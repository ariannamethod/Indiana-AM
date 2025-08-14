import asyncio
import time
from collections import OrderedDict


class LRUCache:
    """Simple LRU cache with max length and TTL support."""

    def __init__(self, maxlen: int = 1024, ttl: float | None = None):
        self.maxlen = maxlen
        self.ttl = ttl
        self._data: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str, default=None):
        async with self._lock:
            if self.ttl is not None:
                cutoff = time.time() - self.ttl
                keys = [k for k, (_, ts) in self._data.items() if ts < cutoff]
                for k in keys:
                    del self._data[k]
            item = self._data.get(key)
            if item is None:
                return default
            value, _ = item
            self._data.move_to_end(key)
            self._data[key] = (value, time.time())
            return value

    async def set(self, key: str, value: str):
        async with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (value, time.time())
            if len(self._data) > self.maxlen:
                self._data.popitem(last=False)

    async def delete(self, key: str) -> None:
        """Remove ``key`` from the cache if present."""
        async with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        """Remove all items from the cache."""
        self._data.clear()

    async def cleanup(self, max_age: float) -> None:
        async with self._lock:
            cutoff = time.time() - max_age
            keys = [k for k, (_, ts) in self._data.items() if ts < cutoff]
            for k in keys:
                del self._data[k]
