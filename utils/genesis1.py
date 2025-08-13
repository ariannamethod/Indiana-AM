import os
import random
import textwrap
import datetime
import httpx
import asyncio
import logging
from .config import settings  # TELEGRAM_TOKEN, PPLX_API_KEY, PINECONE_API_KEY и т.д.
try:
    from .vector_engine import get_vector_engine  # type: ignore
except ImportError:  # pragma: no cover
    from .vector_engine import IndianaVectorEngine

    def get_vector_engine():  # pragma: no cover
        return IndianaVectorEngine()

PPLX_MODEL = "sonar-pro"
PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
TIMEOUT = 30

logger = logging.getLogger(__name__)

# ====== хаотический выбор ======
def _chaotic_pick(strings: list[str]) -> str:
    """
    Имитация 'теории хаоса': берем случайный элемент, иногда заменяем частью другого.
    """
    if not strings:
        return ""
    base = random.choice(strings)
    if random.random() < 0.3:  # немного шума
        frag = random.choice(strings)
        cut = random.randint(0, max(1, len(frag)//2))
        return base + " " + frag[:cut]
    return base

# ====== поиск в Perplexity ======
async def _call_perplexity(query: str, size: int) -> str:
    messages = [
        {"role": "system", "content": textwrap.dedent(f"""
            You are GENESIS-1, Indiana-AM's impressionistic discovery filter.
            Given a found fragment and optional related material,
            create an *impressionistic digest* of ~{size} words.
            Use high temperature associative, poetic brush strokes.
            Return only the digest text (in the user's language if clear).
        """).strip()},
        {"role": "user", "content": query}
    ]
    payload = {"model": PPLX_MODEL, "messages": messages, "temperature": 0.98, "max_tokens": size*5}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                resp = await client.post(PPLX_API_URL, headers={
                    "Authorization": f"Bearer {settings.PPLX_API_KEY}",
                    "Content-Type": "application/json"
                }, json=payload)
                resp.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return resp.json()["choices"][0]["message"]["content"].strip()

# ====== основной вызов ======
async def run_genesis1(digest_size: int = 150) -> str | None:
    """Запустить Genesis-1 и вернуть полученный дайджест.

    Parameters
    ----------
    digest_size:
        Ориентировочный размер выжимки в словах.
    Returns
    -------
    str | None
        Сгенерированный дайджест или ``None``, если ничего не найдено.
    """
    # 1. Собираем случайные куски из репо (например artefacts/)
    repo_dir = "./artefacts"
    collected = []
    for root, _, files in os.walk(repo_dir):
        for fn in files:
            try:
                with open(os.path.join(root, fn), encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    collected.extend(lines)
            except Exception:
                continue

    if not collected:
        return None

    fragment = _chaotic_pick(collected)

    # 2. Поиск в Pinecone (если доступен)
    fragment_related = ""
    try:
        ve = get_vector_engine()
        results = ve.search(fragment, limit=2)
        fragment_related = "\n".join([f"[MEMORY] {txt}" for txt, _ in results])
    except Exception:
        pass

    # 3. Вызов Perplexity
    query = f"Fragment: {fragment}\n\n{fragment_related}"
    digest = await _call_perplexity(query, digest_size)

    # 4. Запись в память
    try:
        await ve.add_memory("genesis1", digest)
    except Exception:
        pass

    # 5. Вывод
    logger.info(f"[Genesis-1 Fact]\n{digest}\n")

    return digest
