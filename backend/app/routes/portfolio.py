import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PortfolioHolding, Watchlist
from app.security import get_owned_watchlist
from app.services.market_data import get_stock_quote

router = APIRouter()


class HoldingPayload(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)


async def serialize_portfolio(watchlist: Watchlist, db: Session):
    async def calculate_holding(holding: PortfolioHolding):
        try:
            quote = await get_stock_quote(holding.symbol)
            current_price = quote["price"]
            previous_close = quote.get("previous_close") or current_price
            market_value = current_price * holding.quantity
            invested_value = holding.buy_price * holding.quantity
            today_pnl = (current_price - previous_close) * holding.quantity
            overall_pnl = market_value - invested_value
            return {
                "id": holding.id,
                "symbol": holding.symbol,
                "quantity": holding.quantity,
                "buy_price": holding.buy_price,
                "current_price": current_price,
                "market_value": round(market_value, 2),
                "invested_value": round(invested_value, 2),
                "today_pnl": round(today_pnl, 2),
                "overall_pnl": round(overall_pnl, 2),
                "status": "ok",
            }
        except Exception:
            return {
                "id": holding.id,
                "symbol": holding.symbol,
                "quantity": holding.quantity,
                "buy_price": holding.buy_price,
                "status": "error",
                "message": "Live quote unavailable",
            }

    holdings = await asyncio.gather(*(calculate_holding(holding) for holding in watchlist.holdings))
    healthy = [holding for holding in holdings if holding["status"] == "ok"]
    portfolio_value = sum(holding["market_value"] for holding in healthy)
    invested_value = sum(holding["invested_value"] for holding in healthy)
    today_pnl = sum(holding["today_pnl"] for holding in healthy)
    overall_pnl = sum(holding["overall_pnl"] for holding in healthy)
    contributor = min(healthy, key=lambda holding: holding["today_pnl"], default=None)

    return {
        "portfolio_value": round(portfolio_value, 2),
        "invested_value": round(invested_value, 2),
        "today_pnl": round(today_pnl, 2),
        "overall_pnl": round(overall_pnl, 2),
        "today_pnl_percent": round((today_pnl / (portfolio_value - today_pnl)) * 100, 2) if portfolio_value - today_pnl else 0,
        "main_contributor": {
            "symbol": contributor["symbol"],
            "today_pnl": contributor["today_pnl"],
        } if contributor else None,
        "holdings": holdings,
    }


@router.get("/{watchlist_id}")
async def get_portfolio(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    return await serialize_portfolio(watchlist, db)


@router.post("/{watchlist_id}/holdings")
async def add_holding(
    watchlist_id: int,
    payload: HoldingPayload,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    symbol = payload.symbol.upper().strip()
    try:
        await get_stock_quote(symbol)
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"{symbol} is not supported by the live market data provider",
        ) from error
    existing = db.query(PortfolioHolding).filter(
        PortfolioHolding.watchlist_id == watchlist_id,
        PortfolioHolding.symbol == symbol,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} is already in your portfolio")

    holding = PortfolioHolding(
        watchlist_id=watchlist_id,
        symbol=symbol,
        quantity=payload.quantity,
        buy_price=payload.buy_price,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return {"message": f"{symbol} added to portfolio", "holding_id": holding.id}


@router.delete("/{watchlist_id}/holdings/{symbol}")
def remove_holding(
    watchlist_id: int,
    symbol: str,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.watchlist_id == watchlist_id,
        PortfolioHolding.symbol == symbol.upper().strip(),
    ).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(holding)
    db.commit()
    return {"message": "Holding removed"}
