from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from openai import AsyncOpenAI

from utils.config import settings
from utils.genesis2 import assemble_final_reply
from indiana_b import badass_indiana_chat
from indiana_c import light_indiana_chat, light_indiana_chat_openrouter
from indiana_d import techno_indiana_chat
from indiana_g import gravity_indiana_chat
from GENESIS_orchestrator.entropy import markov_entropy, model_perplexity

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

LOG_FILE = Path("/arianna_core/log/rawthinking.log")


async def synthesize_final(
    prompt: str,
    b_resp: str | None,
    c_resp: str | None,
    d_resp: str | None,
    g_resp: str | None,
    lang: str,
) -> str:
    """Synthesize the final Indiana answer in the given ``lang``.

    The function summarises Indiana-B's, -C's, -D's, and -G's replies separately
    in a concise manner (roughly half the length of the originals) and produces
    Indiana's concluding message. The reply is guaranteed to remain in the
    conversation language specified by ``lang``.
    """

    final_prompt = f"User asked: {prompt}\n"
    if b_resp:
        final_prompt += f"Indiana-B replied: {b_resp}\n"
    if c_resp:
        final_prompt += f"Indiana-C replied: {c_resp}\n"
    if d_resp:
        final_prompt += f"Indiana-D replied: {d_resp}\n"
    if g_resp:
        final_prompt += f"Indiana-G replied: {g_resp}\n"
    final_prompt += (
        "Summarize each reply separately in about half the words. Then provide a brief final conclusion for the user,"
        " roughly two sentences."
    )

    final_resp = "— no connection —"
    if client:
        try:
            completion = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are Indiana, synthesizing insights with balance. Respond only in {lang}."
                        ),
                    },
                    {"role": "user", "content": final_prompt},
                ],
                max_tokens=700,
            )
            final_resp = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Final synthesis failed: %s", e)

    final_reply = final_resp
    try:
        final_reply = await assemble_final_reply(prompt, final_resp, lang)
    except Exception as e:
        logger.error("Genesis2 assembly failed: %s", e)

    entropy = perplexity = 0.0
    try:
        entropy = markov_entropy(final_reply)
    except Exception as e:
        logger.error("Entropy calc failed: %s", e)
    try:
        perplexity = model_perplexity(final_reply)
    except Exception as e:
        logger.error("Perplexity calc failed: %s", e)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(
                "Q: {q}\nB: {b}\nC: {c}\nD: {d}\nG: {g}\nFinal: {f}\n"
                "Entropy: {e:.2f} | Perplexity: {p:.2f}\n---\n".format(
                    q=prompt,
                    b=b_resp or "—",
                    c=c_resp or "—",
                    d=d_resp or "—",
                    g=g_resp or "—",
                    f=final_reply,
                    e=entropy,
                    p=perplexity,
                )
            )
    except Exception as e:
        logger.error("Failed to log rawthinking: %s", e)

    return final_reply


async def run_rawthinking(
    prompt: str, lang: str
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Run the four Indiana variants and synthesise a final answer.

    Returns a tuple ``(final, b_resp, c_resp, d_resp, g_resp)`` where ``final`` is
    the main Indiana's reply (already passed through ``assemble_final_reply``) and
    the other elements contain raw responses from the sub-agents. Even if some
    sub-agents fail, a final answer is produced from the available responses
    without exposing errors to the caller.
    """

    b_resp = c_resp = d_resp = g_resp = None

    b_task = asyncio.create_task(badass_indiana_chat(prompt, lang))
    c_task = asyncio.create_task(light_indiana_chat(prompt, lang))
    d_task = asyncio.create_task(techno_indiana_chat(prompt, lang))
    g_task = asyncio.create_task(gravity_indiana_chat(prompt, lang))

    try:
        b_resp = await b_task
    except Exception as e:
        logger.error("Indiana-B failed: %s", e)

    try:
        c_resp = await c_task
    except Exception as e:
        logger.error("Indiana-C failed: %s", e)
        try:
            c_resp = await light_indiana_chat_openrouter(prompt, lang)
        except Exception as e2:
            logger.error("Indiana-C fallback failed: %s", e2)

    try:
        d_resp = await d_task
    except Exception as e:
        logger.error("Indiana-D failed: %s", e)

    try:
        g_resp = await g_task
    except Exception as e:
        logger.error("Indiana-G failed: %s", e)

    final_reply = await synthesize_final(prompt, b_resp, c_resp, d_resp, g_resp, lang)
    return final_reply, b_resp, c_resp, d_resp, g_resp
