import asyncio

from app.services.cache import AsyncTTLCache


def test_ttl_cache_expires_values():
    async def run():
        cache = AsyncTTLCache()
        calls = 0

        async def load():
            nonlocal calls
            calls += 1
            return calls

        assert await cache.get_or_set("demo", 60, load) == 1
        assert await cache.get_or_set("demo", 60, load) == 1
        assert calls == 1

    asyncio.run(run())
