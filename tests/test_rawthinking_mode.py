import sys
from pathlib import Path
from types import SimpleNamespace

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
async def test_rawthinking_chain(monkeypatch):
    main.RAW_THINKING_USERS.add("123")
    m = DummyMessage("What is life?")

    monkeypatch.setattr(main, "ChatActionSender", lambda **kwargs: DummySender())

    async def fake_genesis6_report(*a, **k):
        return {}

    async def fake_run_rawthinking(prompt, lang):
        return ("final answer", "B thoughts", "C thoughts")

    async def fake_memory_save(*a, **k):
        return None

    async def fake_process_with_assistant(*a, **k):
        return "summary"

    async def fake_send_split_message(*a, **k):
        m.answers.append(k.get("text", a[-1]))

    monkeypatch.setattr(main, "genesis6_report", fake_genesis6_report)
    monkeypatch.setattr(main, "run_rawthinking", fake_run_rawthinking)
    monkeypatch.setattr(main, "memory", SimpleNamespace(save=fake_memory_save))
    monkeypatch.setattr(main, "save_note", lambda *a, **k: None)
    monkeypatch.setattr(main, "process_with_assistant", fake_process_with_assistant)
    monkeypatch.setattr(main, "send_split_message", fake_send_split_message)
    monkeypatch.setattr(main, "is_rate_limited", lambda *a, **k: False)

    await main.handle_message(m)

    assert m.answers == [
        "summary\n\nIndiana-B and Indiana-C, what do you think?",
        "Indiana-B → B thoughts",
        "Indiana-C → C thoughts",
        "final answer",
    ]
    main.RAW_THINKING_USERS.clear()
