import sys
import logging
from pathlib import Path
import os

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.vectorstore import LocalVectorStore  # noqa: E402
from utils import dayandnight  # noqa: E402
from utils.config import settings  # noqa: E402


@pytest.mark.asyncio
async def test_store_and_fetch_last_day(monkeypatch):
    os.environ.pop("OPENAI_API_KEY", None)
    settings.OPENAI_API_KEY = None
    store = LocalVectorStore()
    monkeypatch.setattr(dayandnight, "vector_store", store)
    await dayandnight._store_last_day("2024-01-01", "hi")
    last = await dayandnight._fetch_last_day()
    assert last == "2024-01-01"


@pytest.mark.asyncio
async def test_init_vector_memory_logs(monkeypatch, caplog):
    os.environ.pop("OPENAI_API_KEY", None)
    settings.OPENAI_API_KEY = None
    store = LocalVectorStore()
    monkeypatch.setattr(dayandnight, "vector_store", store)

    with caplog.at_level(logging.INFO):
        await dayandnight.init_vector_memory()
    assert "No daily log found in vector memory" in caplog.text

    await dayandnight._store_last_day("2024-01-02", "hi")
    caplog.clear()
    with caplog.at_level(logging.INFO):
        await dayandnight.init_vector_memory()
    assert "Last daily log stored on 2024-01-02" in caplog.text
