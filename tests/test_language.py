import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.language import detect_language  # noqa: E402


@pytest.mark.asyncio
async def test_detect_language_persistence(tmp_path):
    db = tmp_path / "lang.db"
    user = "u1"
    lang = await detect_language(user, "Hello world", db_path=str(db))
    assert lang == "en"
    lang2 = await detect_language(user, "/language", db_path=str(db))
    assert lang2 == "en"


@pytest.mark.asyncio
async def test_language_change_command(tmp_path):
    db = tmp_path / "lang.db"
    user = "u2"
    lang = await detect_language(user, "/language ru", db_path=str(db))
    assert lang == "ru"
    lang2 = await detect_language(user, "/language", db_path=str(db))
    assert lang2 == "ru"
    # Short message falls back to stored language
    lang3 = await detect_language(user, "ok", db_path=str(db))
    assert lang3 == "ru"
