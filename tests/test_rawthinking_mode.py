import os
import sys
from pathlib import Path
from types import SimpleNamespace
import asyncio
from datetime import datetime, timezone

import pytest

os.environ["PINECONE_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = "test"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:ABC"

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
    await main.RAW_THINKING_USERS.set("123", datetime.now(timezone.utc).isoformat())
    main.EMERGENCY_MODE = False
    m = DummyMessage("What is life?")
    
    async def fake_genesis6_report(*a, **k):
        return {}

    async def fake_badass(*a, **k):
        return "B thoughts"

    async def fake_light(*a, **k):
        return "C thoughts"

    async def fake_techno(*a, **k):
        return "D thoughts"

    async def fake_gravity(*a, **k):
        return "G thoughts"

    call_counter = {"count": 0}

    async def fake_assemble(prompt, draft, lang):
        call_counter["count"] += 1
        return "final answer"

    async def fake_synth(prompt, b, c, d, g, lang):
        return await fake_assemble(prompt, "draft", lang)

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
    monkeypatch.setattr(main, "techno_indiana_chat", fake_techno)
    monkeypatch.setattr(main, "gravity_indiana_chat", fake_gravity)
    monkeypatch.setattr(main, "assemble_final_reply", fake_assemble)
    monkeypatch.setattr(main, "synthesize_final", fake_synth)
    monkeypatch.setattr(main, "memory", SimpleNamespace(save=fake_memory_save))
    monkeypatch.setattr(main, "save_note", lambda *a, **k: None)
    monkeypatch.setattr(main, "process_with_assistant", fake_process_with_assistant)
    monkeypatch.setattr(main, "send_split_message", fake_send_split_message)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    class DummyChatActionSender:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "ChatActionSender", DummyChatActionSender)
    monkeypatch.setattr(main.random, "choice", lambda seq: seq[0])

    await main.handle_message(m)

    assert m.answers == [
        "summary\n\nWhat do you think?",
        "Indiana-B\nB thoughts",
        "Indiana-C\nC thoughts",
        "Indiana-D\nD thoughts",
        "Indiana-G\nG thoughts",
        "final answer",
    ]
    assert call_counter["count"] == 1
    main.RAW_THINKING_USERS.clear()
