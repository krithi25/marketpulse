import asyncio

from app.services import market_data
from app.services.cache import market_cache


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"c": 123.45, "d": 1.2, "dp": 0.98, "h": 125, "l": 120, "o": 121, "pc": 122.25, "t": 1}


class FakeClient:
    calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        FakeClient.calls += 1
        return FakeResponse()


def test_quote_cache_avoids_duplicate_provider_calls(monkeypatch):
    async def run():
        await market_cache.clear()
        FakeClient.calls = 0
        monkeypatch.setattr(market_data.httpx, "AsyncClient", lambda *args, **kwargs: FakeClient())
        first = await market_data.get_stock_quote("AAPL")
        second = await market_data.get_stock_quote("AAPL")
        assert first == second
        assert FakeClient.calls == 1

    asyncio.run(run())
