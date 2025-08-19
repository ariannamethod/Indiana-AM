from datetime import datetime
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from aiogram.types import Chat, Message, User  # noqa: E402

from utils.rate_limiter import RateLimitMiddleware  # noqa: E402


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excess_messages():
    middleware = RateLimitMiddleware(limit=2, window=60, delay=0)
    user = User(id=1, is_bot=False, first_name="Test")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text="hello")

    calls = 0

    async def handler(event, data):
        nonlocal calls
        calls += 1

    await middleware(handler, message, {})
    await middleware(handler, message, {})
    await middleware(handler, message, {})

    assert calls == 2


@pytest.mark.asyncio
async def test_rate_limiter_logs_exceed(caplog):
    middleware = RateLimitMiddleware(limit=1, window=60, delay=0)
    user = User(id=1, is_bot=False, first_name="Test")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text="hello")

    async def handler(event, data):
        return None

    with caplog.at_level(logging.WARNING):
        await middleware(handler, message, {})
        await middleware(handler, message, {})

    assert any(
        r.message == "Rate limit exceeded: user=1, limit=1/60s"
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_daily_limit_and_bypass():
    middleware = RateLimitMiddleware(limit=1, window=86400, bypass_ids={"2"})
    user1 = User(id=1, is_bot=False, first_name="User1")
    chat1 = Chat(id=1, type="private")
    message1 = Message(message_id=1, date=datetime.now(), chat=chat1, from_user=user1, text="hi")

    calls = 0

    async def handler(event, data):
        nonlocal calls
        calls += 1

    await middleware(handler, message1, {})
    await middleware(handler, message1, {})
    assert calls == 1

    user2 = User(id=2, is_bot=False, first_name="User2")
    chat2 = Chat(id=2, type="private")
    message2 = Message(message_id=1, date=datetime.now(), chat=chat2, from_user=user2, text="hi")

    await middleware(handler, message2, {})
    await middleware(handler, message2, {})

    assert calls == 3
