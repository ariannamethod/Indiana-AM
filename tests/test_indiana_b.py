import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import indiana_b  # noqa: E402
from indiana_b import badass_indiana_chat  # noqa: E402


@pytest.mark.asyncio
async def test_missing_xai_api_key(monkeypatch, caplog):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr(indiana_b, "XAI_API_KEY", None, raising=False)
    with caplog.at_level("ERROR"):
        result = await badass_indiana_chat("test")
    assert "XAI_API_KEY" in caplog.text
    assert result == "XAI_API_KEY is missing"
