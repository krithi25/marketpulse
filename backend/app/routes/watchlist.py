import asyncio
from datetime import datetime

from app.models.visit import WatchlistVisit
from app.models.snapshot import MarketSnapshot

from sqlalchemy.orm import Session
from app.models.visit import WatchlistVisit
from app.database import get_db
from app.services.market_data import get_stock_quote, get_volume_stats, get_company_news
from app.services.snapshot import save_snapshot, get_previous_snapshot
from app.services.change_detector import (
    calculate_change,
    calculate_significance,
    generate_explanation,
    analyze_news,
)
from fastapi import APIRouter, Depends, HTTPException


from app.database import get_db
from app.models import User, Watchlist, Stock
from app.security import get_owned_watchlist


router = APIRouter()


@router.post("/setup")
def setup_user(db: Session = Depends(get_db)):
    """
    Create a demo user and watchlist.
    """

    user = db.query(User).filter(
        User.email == "demo@marketpulse.com"
    ).first()

    if not user:
        user = User(
            email="demo@marketpulse.com"
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    watchlist = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).first()

    if not watchlist:
        watchlist = Watchlist(
            name="My Watchlist",
            user_id=user.id
        )

        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)

    return {
        "user_id": user.id,
        "watchlist_id": watchlist.id,
        "message": "Setup successful"
    }


@router.get("/{watchlist_id}")
def get_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    return {
        "id": watchlist.id,
        "name": watchlist.name,
        "stocks": [
            {
                "id": stock.id,
                "symbol": stock.symbol
            }
            for stock in watchlist.stocks
        ]
    }


@router.post("/{watchlist_id}/stocks")
async def add_stock(
    watchlist_id: int,
    symbol: str,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    symbol = symbol.upper().strip()

    try:
        await get_stock_quote(symbol)
    except HTTPException as error:
        raise HTTPException(
            status_code=422,
            detail=f"{symbol} is not currently supported by the market data provider"
        ) from error

    existing_stock = db.query(Stock).filter(
        Stock.watchlist_id == watchlist_id,
        Stock.symbol == symbol
    ).first()

    if existing_stock:
        raise HTTPException(
            status_code=409,
            detail=f"{symbol} is already in the watchlist"
        )

    stock = Stock(
        symbol=symbol,
        watchlist_id=watchlist_id
    )

    db.add(stock)
    db.commit()
    db.refresh(stock)

    return {
        "message": f"{symbol} added successfully",
        "stock": {
            "id": stock.id,
            "symbol": stock.symbol
        }
    }


@router.delete("/{watchlist_id}/stocks/{symbol}")
def remove_stock(
    watchlist_id: int,
    symbol: str,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    symbol = symbol.upper().strip()

    stock = db.query(Stock).filter(
        Stock.watchlist_id == watchlist_id,
        Stock.symbol == symbol
    ).first()

    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"{symbol} is not in the watchlist"
        )

    db.delete(stock)
    db.commit()

    return {
        "message": f"{symbol} removed successfully"
    }

@router.get("/{watchlist_id}/intelligence")
async def get_watchlist_intelligence(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    try:
        market_quote = await get_stock_quote("SPY")
        market_change = market_quote.get("change_percent")
    except Exception:
        market_change = None

    async def process_stock(stock):
        symbol = stock.symbol
        try:
            quote = await get_stock_quote(symbol)
            volume = await get_volume_stats(symbol)
            news = analyze_news(await get_company_news(symbol))
            current_snapshot = save_snapshot(db, quote)
            previous_snapshot = get_previous_snapshot(db, symbol, current_snapshot.id)

            snapshot_change = calculate_change(previous_snapshot.price, current_snapshot.price) if previous_snapshot else None
            percentage_change = quote.get("change_percent")
            if percentage_change is None:
                percentage_change = snapshot_change["percentage_change"] if snapshot_change else 0

            significance = calculate_significance(
                percentage_change,
                volume["current_volume"],
                volume["average_volume"],
                market_change,
                news["score"],
            )
            reasons = generate_explanation(
                percentage_change,
                significance["score"],
                volume["current_volume"],
                volume["average_volume"],
                market_change,
                news,
            )

            return {
                "symbol": symbol,
                "price": current_snapshot.price,
                "change_percent": percentage_change,
                "score": significance["score"],
                "severity": significance["severity"],
                "signals": significance["signals"],
                "current_volume": volume["current_volume"],
                "average_volume": volume["average_volume"],
                "volume_ratio": volume["volume_ratio"],
                "market_change": market_change,
                "news_score": news["score"],
                "news_sentiment": news["sentiment"],
                "news_impact": news["impact"],
                "news": news["articles"],
                "reasons": reasons if previous_snapshot else ["First market snapshot"],
                "status": "ok",
            }
        except Exception as error:
            print(f"Error processing {symbol}: {error}")
            return {"symbol": symbol, "status": "error", "message": "Unable to fetch market data"}

    results = await asyncio.gather(*(process_stock(stock) for stock in watchlist.stocks))
    return {"watchlist_id": watchlist_id, "watchlist_name": watchlist.name, "stocks": results}

@router.post("/{watchlist_id}/visit")
def record_watchlist_visit(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    visit = WatchlistVisit(
        watchlist_id=watchlist_id
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    return {
        "watchlist_id": watchlist_id,
        "visited_at": visit.visited_at
    }

@router.get("/{watchlist_id}/since-last-visit")
def get_changes_since_last_visit(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    # Find the previous visit
    last_visit = (
        db.query(WatchlistVisit)
        .filter(
            WatchlistVisit.watchlist_id == watchlist_id
        )
        .order_by(WatchlistVisit.visited_at.desc())
        .first()
    )

    if not last_visit:
        return {
            "watchlist_id": watchlist_id,
            "message": "No previous visit found",
            "changes": []
        }

    changes = []

    for stock in watchlist.stocks:

        # Snapshot immediately before the last visit
        previous_snapshot = (
            db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.symbol == stock.symbol,
                MarketSnapshot.timestamp <= last_visit.visited_at
            )
            .order_by(MarketSnapshot.timestamp.desc())
            .first()
        )

        # Latest snapshot
        latest_snapshot = (
            db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.symbol == stock.symbol
            )
            .order_by(MarketSnapshot.timestamp.desc())
            .first()
        )

        if not previous_snapshot or not latest_snapshot:
            continue

        # Calculate change
        change = calculate_change(
            previous_snapshot.price,
            latest_snapshot.price
        )

        reasons = generate_explanation(
            change["percentage_change"],
            change["score"]
        )

        changes.append({
            "symbol": stock.symbol,
            "previous_price": previous_snapshot.price,
            "current_price": latest_snapshot.price,
            "change_percent": change["percentage_change"],
            "score": change["score"],
            "severity": change["severity"],
            "reasons": reasons
        })

    return {
        "watchlist_id": watchlist_id,
        "last_checked": last_visit.visited_at,
        "changes": changes
    }