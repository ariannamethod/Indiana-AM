import sys
from pathlib import Path
from types import SimpleNamespace
import random
from datetime import datetime, timezone

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


class DummyMessage:
    def __init__(self, text="/help"):
        self.text = text
        self.from_user = SimpleNamespace(id=123, language_code="en")
        self.chat = SimpleNamespace(id=123, type="private")
        self.voice = None
        self.photo = []
        self.answers: list[str] = []

    async def answer(self, text: str):
        self.answers.append(text)


class DummySender:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_coder_help_returns_core_commands(monkeypatch):
    main.CODER_USERS.clear()
    m = DummyMessage("/help")
    main.CODER_USERS.set(str(m.from_user.id), datetime.now(timezone.utc).isoformat())

    monkeypatch.setattr(main, "ChatActionSender", lambda **kwargs: DummySender())

    async def fake_genesis6_report(*a, **k):
        return {}

    async def fake_genesis2_sonar_filter(*a, **k):
        return "twist"

    async def fake_send_split_message(*a, **k):
        m.answers.append(k.get("text", a[-1]))

    monkeypatch.setattr(main, "genesis6_report", fake_genesis6_report)
    monkeypatch.setattr(main, "genesis2_sonar_filter", fake_genesis2_sonar_filter)

    async def fake_memory_save(*a, **k):
        return None

    monkeypatch.setattr(main, "memory", SimpleNamespace(save=fake_memory_save))
    monkeypatch.setattr(main, "save_note", lambda *a, **k: None)
    monkeypatch.setattr(main, "format_core_commands", lambda: "core help")
    monkeypatch.setattr(main, "is_rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(main, "send_split_message", fake_send_split_message)
    monkeypatch.setattr(random, "random", lambda: 1.0)

    await main.handle_message(m)

    assert m.answers == ["core help\n\n🜂 Investigative Twist → twist"]
    main.CODER_USERS.clear()


@pytest.mark.asyncio
async def test_coder_ignored_during_rawthinking():
    main.CODER_USERS.clear()
    main.RAW_THINKING_USERS.set("123", datetime.now(timezone.utc).isoformat())
    m = DummyMessage("/coder")
    await main.enable_coder(m)
    assert m.answers == []
    assert main.CODER_USERS.get("123") is None
    main.RAW_THINKING_USERS.clear()
