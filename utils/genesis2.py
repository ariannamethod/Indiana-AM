import random
import textwrap
from datetime import datetime, timezone
import httpx
import re

from .config import settings  # settings.PPLX_API_KEY должен быть определён

# Самая универсальная рабочая модель на сегодня:
PPLX_MODEL = "sonar-pro"
PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
TIMEOUT = 25

headers = {
    "Authorization": f"Bearer {settings.PPLX_API_KEY}",
    "Content-Type": "application/json",
}


# Символы, которыми должно заканчиваться корректное предложение
SENTENCE_ENDINGS = ('.', '!', '?', ':', ';', '"', ')', ']', '}')


def _build_prompt(draft: str, user_prompt: str, language: str) -> list:
    system_msg = textwrap.dedent(
        f"""
        You are GENESIS-2, the intuition filter for Indiana‐AM ("Indiana Jones" archetype).
        Return ONE short investigative twist (≤500 tokens) that deepens the current reasoning.
        Do **NOT** repeat the draft; just add an angle, question or hidden variable.
        Reply in {language}.
        """
    ).strip()
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"USER PROMPT >>> {user_prompt}"},
        {"role": "assistant", "content": f"DRAFT >>> {draft}"},
        {"role": "user", "content": "Inject the twist now:"},
    ]


async def _call_sonar(messages: list) -> str:
    payload = {
        "model": PPLX_MODEL,
        "messages": messages,
        "temperature": 0.8,  # регулируй, если нужно разнообразие
        "max_tokens": 500,  # Увеличен лимит токенов с 120 до 500
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(PPLX_API_URL, headers=headers, json=payload)
        try:
            resp.raise_for_status()
        except Exception:
            # Дебаг: показать тело ошибки API
            print("[Genesis-2] Sonar HTTP error:", resp.text)
            raise
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content.strip()


async def genesis2_sonar_filter(user_prompt: str, draft_reply: str, language: str) -> str:
    # Не всегда срабатывать — для "живости"
    if random.random() < 0.12 or not settings.PPLX_API_KEY:
        return ""
    try:
        messages = _build_prompt(draft_reply, user_prompt, language)
        twist = await _call_sonar(messages)

        # Проверка на обрезание сообщения посередине предложения
        if twist and twist[-1] not in SENTENCE_ENDINGS:
            twist = twist.rstrip() + "..."

        return twist
    except Exception as e:
        print(f"[Genesis-2] Sonar fail {e} @ {datetime.now(timezone.utc).isoformat()}")
        return ""


async def assemble_final_reply(user_prompt: str, indiana_draft: str, language: str) -> str:
    twist = await genesis2_sonar_filter(user_prompt, indiana_draft, language)
    if twist:
        return f"{indiana_draft}\n\n🜂 Investigative Twist → {twist}"
    return indiana_draft
