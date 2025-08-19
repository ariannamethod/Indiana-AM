import importlib

import pytest

import utils.config as config


def test_missing_telegram_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        importlib.reload(config)


def test_missing_openai_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        importlib.reload(config)


def test_contributor_chat_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("CONTRIBUTOR_CHAT01", "100")
    monkeypatch.setenv("CONTRIBUTOR_CHAT02", "200")
    importlib.reload(config)
    assert config.settings.CONTRIBUTOR_CHAT_IDS == ["100", "200"]
