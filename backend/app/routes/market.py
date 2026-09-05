from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

from app.services.market_data import get_stock_quote, search_stock_symbols

from app.services.snapshot import (
    save_snapshot,
    get_previous_snapshot
)

from app.services.change_detector import (
    calculate_change
)


router = APIRouter()


@router.get("/search")
async def search_market_symbols(query: str):
    return {"results": await search_stock_symbols(query)}


@router.get("/{symbol}")
async def get_market_data(
    symbol: str,
    db: Session = Depends(get_db)
):
    quote = await get_stock_quote(symbol)

    snapshot = save_snapshot(
        db,
        quote
    )

    return {
        "symbol": quote["symbol"],
        "price": quote["price"],
        "change": quote["change"],
        "change_percent": quote["change_percent"],
        "high": quote["high"],
        "low": quote["low"],
        "open": quote["open"],
        "previous_close": quote["previous_close"],
        "timestamp": quote["timestamp"],
        "snapshot_id": snapshot.id
    }


@router.get("/{symbol}/changes")
async def get_stock_changes(
    symbol: str,
    db: Session = Depends(get_db)
):
    quote = await get_stock_quote(symbol)

    current_snapshot = save_snapshot(
        db,
        quote
    )

    previous_snapshot = get_previous_snapshot(
        db,
        symbol,
        current_snapshot.id
    )

    if not previous_snapshot:
        return {
            "symbol": symbol.upper(),
            "message": "Not enough history yet",
            "severity": "NORMAL"
        }

    result = calculate_change(
        previous_snapshot.price,
        current_snapshot.price
    )

    return {
        "symbol": symbol.upper(),
        "previous_price": previous_snapshot.price,
        "current_price": current_snapshot.price,
        "absolute_change": result["absolute_change"],
        "percentage_change": result["percentage_change"],
        "severity": result["severity"]
    }