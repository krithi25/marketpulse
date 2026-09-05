import asyncio
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any


class AsyncTTLCache:
    def __init__(self, max_size: int = 512):
        self.max_size = max_size
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, ttl: int, loader: Callable[[], Awaitable[Any]]):
        now = time.monotonic()
        async with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] > now:
                return entry[1]
            if entry:
                self._entries.pop(key, None)

        value = await loader()
        async with self._lock:
            if len(self._entries) >= self.max_size:
                oldest_key = min(self._entries, key=lambda item: self._entries[item][0])
                self._entries.pop(oldest_key, None)
            self._entries[key] = (time.monotonic() + ttl, value)
        return value

    async def clear(self):
        async with self._lock:
            self._entries.clear()


market_cache = AsyncTTLCache()


def cached_async(prefix: str, ttl: int):
    def decorator(function):
        @wraps(function)
        async def wrapped(*args, **kwargs):
            parts = [prefix, *(str(arg).upper().strip() for arg in args), *(f"{key}={value}" for key, value in sorted(kwargs.items()))]
            key = ":".join(parts)
            return await market_cache.get_or_set(key, ttl, lambda: function(*args, **kwargs))
        return wrapped
    return decorator
