import re
from typing import Optional

import aiosqlite
from langdetect import detect, DetectorFactory, LangDetectException

from .lru_cache import LRUCache

DetectorFactory.seed = 0

LANG_CACHE_MAXLEN = 1000
LANG_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days
USER_LANGS = LRUCache(maxlen=LANG_CACHE_MAXLEN)
DB_PATH = "lighthouse_memory.db"  # reuse main memory db


async def _connect(db_path: str = DB_PATH) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            language TEXT
        )
        """
    )
    await db.commit()
    return db


async def _read_language(user_id: str, db_path: str = DB_PATH) -> Optional[str]:
    db = await _connect(db_path)
    async with db.execute(
        "SELECT language FROM user_settings WHERE user_id=?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    await db.close()
    return row[0] if row else None


async def _write_language(user_id: str, lang: str, db_path: str = DB_PATH) -> None:
    db = await _connect(db_path)
    await db.execute(
        """
        INSERT INTO user_settings (user_id, language)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET language=excluded.language
        """,
        (user_id, lang),
    )
    await db.commit()
    await db.close()


async def detect_language(
    user_id: str, text: str, language_code: str | None = None, db_path: str = DB_PATH
) -> str:
    """Detect user's language with persistent storage and command override.

    The function tries to detect the language from ``text``. If the text begins
    with ``/language``, it interprets it as a command. ``/language`` alone
    returns the currently stored language, while ``/language <code>`` updates the
    preference. Detected or chosen languages are stored in a persistent
    ``user_settings`` table and cached for faster access.
    """

    if text and text.strip().lower().startswith("/language"):
        parts = text.split(maxsplit=1)
        if len(parts) == 1 or not parts[1].strip():
            cached = await USER_LANGS.get(user_id)
            if cached is None:
                cached = await _read_language(user_id, db_path)
            return cached or language_code or "en"
        new_lang = parts[1].strip().split()[0]
        await USER_LANGS.set(user_id, new_lang)
        await _write_language(user_id, new_lang, db_path)
        return new_lang

    cached = await USER_LANGS.get(user_id)
    saved = None
    if cached is None:
        saved = await _read_language(user_id, db_path)

    lang = None
    clean = re.sub(r"\W", "", text or "")
    if len(clean) >= 3:
        try:
            lang = detect(text)
        except LangDetectException:
            lang = None
    if language_code:
        language_code = language_code.split("-")[0]
    lang = lang or language_code or cached or saved or "en"
    await USER_LANGS.set(user_id, lang)
    await _write_language(user_id, lang, db_path)
    return lang


async def cleanup_user_langs() -> None:
    """Periodically drop inactive user language records from cache."""
    await USER_LANGS.cleanup(LANG_CACHE_TTL)
