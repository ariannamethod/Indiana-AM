import asyncio
import logging
import time
from collections import deque
from typing import Deque, Dict, Set

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from .lru_cache import LRUCache


class RateLimitMiddleware(BaseMiddleware):
    """Simple per-user rate limiter.

    Keeps a rolling window of message timestamps for each user and ensures
    that no more than ``limit`` messages are processed within ``window``
    seconds. When the limit is exceeded, the message is ignored or delayed
    depending on ``delay``.
    """

    def __init__(
        self,
        limit: int,
        window: float,
        delay: float = 0.0,
        max_users: int = 1024,
        *,
        period: float = 86400,
        bypass_ids: Set[str] | None = None,
    ) -> None:
        self.limit = limit
        self.window = window
        self.delay = delay
        self.bypass_ids = bypass_ids or set()
        self._users: LRUCache = LRUCache(maxlen=max_users, ttl=period)
        self.logger = logging.getLogger(__name__)

    async def __call__(self, handler, event: TelegramObject, data: Dict):  # type: ignore[override]
        if isinstance(event, Message) and event.from_user:
            user_id = str(event.from_user.id)
            if user_id in self.bypass_ids:
                return await handler(event, data)
            now = time.time()
            timestamps: Deque[float] = await self._users.get(user_id, deque())

            # drop outdated timestamps
            while timestamps and now - timestamps[0] > self.window:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                self.logger.warning("Rate limit exceeded for user %s", user_id)
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
                    return await handler(event, data)
                return None

            timestamps.append(now)
            await self._users.set(user_id, timestamps)
        return await handler(event, data)
