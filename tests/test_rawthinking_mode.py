import sys
from pathlib import Path
from types import SimpleNamespace
import asyncio

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


@pytest.mark.asyncio
async def test_rawthinking_chain(monkeypatch):
    main.RAW_THINKING_USERS.add("123")
    m = DummyMessage("What is life?")
    
    async def fake_genesis6_report(*a, **k):
        return {}

    async def fake_badass(*a, **k):
        return "B thoughts"

    async def fake_light(*a, **k):
        return "C thoughts"

    async def fake_synth(prompt, b, c, lang):
        return "final answer"

    async def fake_memory_save(*a, **k):
        return None

    async def fake_process_with_assistant(*a, **k):
        return "summary"

    async def fake_send_split_message(*a, **k):
        m.answers.append(k.get("text", a[-1]))

    async def fake_sleep(*a, **k):
        return None

    monkeypatch.setattr(main, "genesis6_report", fake_genesis6_report)
    monkeypatch.setattr(main, "badass_indiana_chat", fake_badass)
    monkeypatch.setattr(main, "light_indiana_chat", fake_light)
    monkeypatch.setattr(main, "synthesize_final", fake_synth)
    monkeypatch.setattr(main, "memory", SimpleNamespace(save=fake_memory_save))
    monkeypatch.setattr(main, "save_note", lambda *a, **k: None)
    monkeypatch.setattr(main, "process_with_assistant", fake_process_with_assistant)
    monkeypatch.setattr(main, "send_split_message", fake_send_split_message)
    monkeypatch.setattr(main, "is_rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await main.handle_message(m)

    assert m.answers == [
        "typing...",
        "summary\n\nIndiana-B and Indiana-C, what do you think?",
        "Indiana-B typing...",
        "Indiana-B\nB thoughts",
        "Indiana-C typing...",
        "Indiana-C\nC thoughts",
        "typing...",
        "final answer",
    ]
    main.RAW_THINKING_USERS.clear()
