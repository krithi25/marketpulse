import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from app.services.cache import cached_async

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_URL = "https://finnhub.io/api/v1/quote"
FINNHUB_SEARCH_URL = "https://finnhub.io/api/v1/search"
CANDLE_URL = "https://finnhub.io/api/v1/stock/candle"
NEWS_URL = "https://finnhub.io/api/v1/company-news"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def _require_api_key():
    if not FINNHUB_API_KEY:
        raise HTTPException(status_code=500, detail="Market data API key is not configured")


@cached_async("quote", ttl=30)
async def get_stock_quote(symbol: str):
    _require_api_key()
    symbol = symbol.upper().strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(FINNHUB_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY})
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Market data provider timed out")
    except httpx.HTTPStatusError as error:
        if error.response.status_code in {403, 429}:
            fallback = await get_quote_from_yahoo(symbol)
            if fallback:
                return fallback
        raise HTTPException(status_code=502, detail="Market data provider is unavailable")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Market data provider is unavailable")

    price = data.get("c")
    if price is None or price <= 0:
        raise HTTPException(status_code=404, detail=f"No valid market data found for {symbol}")

    return {
        "symbol": symbol,
        "price": price,
        "change": data.get("d"),
        "change_percent": data.get("dp"),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "previous_close": data.get("pc"),
        "timestamp": data.get("t")
    }


async def get_quote_from_yahoo(symbol: str):
    """Use Yahoo's delayed quote metadata when the primary quote is unavailable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{YAHOO_CHART_URL}/{symbol}",
                params={"range": "2d", "interval": "1d"},
                headers={"User-Agent": "MarketPulse/1.0"},
            )
        response.raise_for_status()
        metadata = (response.json().get("chart", {}).get("result") or [])[0].get("meta", {})
        price = metadata.get("regularMarketPrice")
        previous_close = metadata.get("previousClose") or metadata.get("chartPreviousClose")
        if not price or not previous_close:
            return None
        change = price - previous_close
        return {
            "symbol": symbol,
            "price": price,
            "change": round(change, 4),
            "change_percent": round((change / previous_close) * 100, 4),
            "high": metadata.get("regularMarketDayHigh"),
            "low": metadata.get("regularMarketDayLow"),
            "open": None,
            "previous_close": previous_close,
            "timestamp": metadata.get("regularMarketTime"),
        }
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, IndexError, KeyError, TypeError):
        return None


@cached_async("volume", ttl=300)
async def get_volume_stats(symbol: str):
    _require_api_key()
    symbol = symbol.upper().strip()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=35)
    params = {
        "symbol": symbol,
        "resolution": "D",
        "from": int(start_date.timestamp()),
        "to": int(end_date.timestamp()),
        "token": FINNHUB_API_KEY
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(CANDLE_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Historical market data timed out")
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 403:
            return await get_volume_stats_from_yahoo(symbol)
        raise HTTPException(status_code=502, detail="Historical market data unavailable")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Historical market data unavailable")

    volumes = [volume for volume in data.get("v", []) if volume and volume > 0]
    if data.get("s") != "ok" or len(volumes) < 2:
        return {"current_volume": None, "average_volume": None, "volume_ratio": None}

    current_volume = volumes[-1]
    historical_volumes = volumes[-21:-1]
    if not historical_volumes:
        return {"current_volume": current_volume, "average_volume": None, "volume_ratio": None}

    average_volume = sum(historical_volumes) / len(historical_volumes)
    return {
        "current_volume": round(current_volume, 2),
        "average_volume": round(average_volume, 2),
        "volume_ratio": round(current_volume / average_volume, 2)
    }


async def get_volume_stats_from_yahoo(symbol: str):
    """Use Yahoo's delayed chart feed when Finnhub candles are not enabled."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=35)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{YAHOO_CHART_URL}/{symbol}",
                params={
                    "period1": int(start_date.timestamp()),
                    "period2": int(end_date.timestamp()),
                    "interval": "1d",
                    "events": "history",
                },
                headers={"User-Agent": "MarketPulse/1.0"},
            )
        response.raise_for_status()
        result = response.json().get("chart", {}).get("result") or []
        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        volumes = [volume for volume in quote.get("volume", []) if volume and volume > 0]
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, IndexError, KeyError):
        return {"current_volume": None, "average_volume": None, "volume_ratio": None}

    if len(volumes) < 2:
        return {"current_volume": None, "average_volume": None, "volume_ratio": None}

    current_volume = volumes[-1]
    historical_volumes = volumes[-21:-1]
    if not historical_volumes:
        return {"current_volume": current_volume, "average_volume": None, "volume_ratio": None}

    average_volume = sum(historical_volumes) / len(historical_volumes)
    return {
        "current_volume": round(current_volume, 2),
        "average_volume": round(average_volume, 2),
        "volume_ratio": round(current_volume / average_volume, 2),
    }


@cached_async("search", ttl=300)
async def search_stock_symbols(query: str):
    _require_api_key()
    query = query.strip()
    if len(query) < 2:
        return []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(FINNHUB_SEARCH_URL, params={"q": query, "token": FINNHUB_API_KEY})
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Market data provider timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Market data provider is unavailable")

    return [
        {"symbol": item.get("symbol"), "description": item.get("description"), "type": item.get("type")}
        for item in data.get("result", [])
        if item.get("symbol") and item.get("description")
    ][:8]


@cached_async("news", ttl=300)
async def get_company_news(symbol: str, days: int = 7):
    """Return recent company headlines; unavailable news stays non-fatal."""
    _require_api_key()
    symbol = symbol.upper().strip()
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                NEWS_URL,
                params={
                    "symbol": symbol,
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                    "token": FINNHUB_API_KEY,
                },
            )
        response.raise_for_status()
        articles = response.json()
    except (httpx.TimeoutException, httpx.HTTPError, ValueError):
        return []

    return [
        {
            "headline": article.get("headline"),
            "summary": article.get("summary"),
            "source": article.get("source"),
            "url": article.get("url"),
            "published_at": article.get("datetime"),
        }
        for article in articles[:5]
        if article.get("headline")
    ]
