import asyncio
from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main import RATE_LIMIT, USER_MESSAGE_TIMES, handle_message, is_rate_limited  # noqa: E402


class DummyMessage:
    def __init__(self):
        self.text = "Hello?"
        self.from_user = SimpleNamespace(id=123, language_code="en")
        self.chat = SimpleNamespace(id=123, type="private")
        self.voice = None
        self.photo = []
        self.answers: list[str] = []

    async def answer(self, text: str):
        self.answers.append(text)


@pytest.mark.asyncio
async def test_rate_limiter_stops_responses(monkeypatch):
    USER_MESSAGE_TIMES._data.clear()
    user_id = str(123)
    for _ in range(RATE_LIMIT):
        assert not is_rate_limited(user_id)

    m = DummyMessage()
    import main
    main.EMERGENCY_MODE = False

    async def fake_send_split_message(*args, **kwargs):  # pragma: no cover
        raise AssertionError("send_split_message should not be called")

    monkeypatch.setattr("main.send_split_message", fake_send_split_message)

    await handle_message(m)

    assert m.answers, "warning should be sent when rate limit exceeded"
    assert "слишком часто" in m.answers[0].lower()
