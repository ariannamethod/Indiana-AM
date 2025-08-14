import asyncio
import pytest

from utils.lru_cache import LRUCache


@pytest.mark.asyncio
async def test_lru_cache_concurrent_access():
    cache = LRUCache(maxlen=200)

    async def worker(i: int) -> str:
        key = f"k{i}"
        val = f"v{i}"
        await cache.set(key, val)
        return await cache.get(key)

    results = await asyncio.gather(*(worker(i) for i in range(100)))
    assert results == [f"v{i}" for i in range(100)]

    # cleanup concurrently
    await cache.cleanup(0)
    remaining = [await cache.get(f"k{i}") for i in range(100)]
    assert all(r is None for r in remaining)
