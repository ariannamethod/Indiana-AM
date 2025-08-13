from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from langdetect import detect
from openai import AsyncOpenAI

from utils.config import settings
from utils.genesis2 import genesis2_sonar_filter
from indiana_b import badass_indiana_chat
from indiana_c import light_indiana_chat, light_indiana_chat_openrouter

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

LOG_FILE = Path("/arianna_core/log/rawthinking.log")


async def run_rawthinking(prompt: str) -> list[str]:
    """Run Indiana-B, Indiana-C, and synthesize a final answer.

    Returns list of [B response, C response, final filtered response].
    """
    b_resp = c_resp = final_resp = "— no connection —"

    b_task = asyncio.create_task(badass_indiana_chat(prompt))
    c_task = asyncio.create_task(light_indiana_chat(prompt))

    try:
        b_resp = await b_task
    except Exception as e:
        logger.error("Indiana-B failed: %s", e)
        b_resp = "— no connection —"

    try:
        c_resp = await c_task
    except Exception as e:
        logger.error("Indiana-C failed: %s", e)
        try:
            c_resp = await light_indiana_chat_openrouter(prompt)
        except Exception as e2:
            logger.error("Indiana-C fallback failed: %s", e2)
            c_resp = "— no connection —"

    final_prompt = (
        f"User asked: {prompt}\n"
        f"Indiana-B replied: {b_resp}\n"
        f"Indiana-C replied: {c_resp}\n"
        "Provide a concise, thoughtful synthesis addressing the user's request."
    )

    if client:
        try:
            completion = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Indiana, synthesizing insights with balance.",
                    },
                    {"role": "user", "content": final_prompt},
                ],
                max_tokens=1000,
            )
            final_resp = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Final synthesis failed: %s", e)
            final_resp = "— no connection —"
    else:
        final_resp = "— no connection —"

    try:
        lang = detect(prompt)
    except Exception:
        lang = "en"

    try:
        final_resp = await genesis2_sonar_filter(prompt, final_resp, lang)
    except Exception as e:
        logger.error("Genesis2 filter failed: %s", e)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(
                f"Q: {prompt}\nB: {b_resp}\nC: {c_resp}\nFinal: {final_resp}\n---\n"
            )
    except Exception as e:
        logger.error("Failed to log rawthinking: %s", e)

    return [b_resp, c_resp, final_resp]
