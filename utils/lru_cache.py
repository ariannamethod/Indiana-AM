import time
from collections import OrderedDict


class LRUCache:
    """Simple LRU cache with max length and TTL support."""

    def __init__(self, maxlen: int = 1024, ttl: float | None = None):
        self.maxlen = maxlen
        self.ttl = ttl
        self._data: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, key: str, default=None):
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

    def set(self, key: str, value: str):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, time.time())
        if len(self._data) > self.maxlen:
            self._data.popitem(last=False)

    def cleanup(self, max_age: float) -> None:
        cutoff = time.time() - max_age
        keys = [k for k, (_, ts) in self._data.items() if ts < cutoff]
        for k in keys:
            del self._data[k]
