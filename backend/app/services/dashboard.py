import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Stock, Watchlist
from app.models.dashboard import DashboardSnapshot
from app.models.snapshot import MarketSnapshot
from app.services.change_detector import calculate_change, calculate_significance, generate_explanation, analyze_news
from app.services.market_data import get_stock_quote, get_volume_stats, get_company_news
from app.services.snapshot import get_previous_snapshot, save_snapshot


async def build_dashboard(watchlist: Watchlist, db: Session) -> dict:
    try:
        market_quote = await get_stock_quote("SPY")
        market_change = market_quote.get("change_percent")
    except Exception:
        market_change = None

    async def load_stock(stock: Stock) -> dict:
        try:
            quote = await get_stock_quote(stock.symbol)
            volume = await get_volume_stats(stock.symbol)
            news = analyze_news(await get_company_news(stock.symbol))

            current = save_snapshot(db, quote)
            previous = get_previous_snapshot(db, stock.symbol, current.id)
            snapshot_change = calculate_change(previous.price, current.price) if previous else None
            percentage = quote.get("change_percent")
            if percentage is None:
                percentage = snapshot_change["percentage_change"] if snapshot_change else 0

            significance = calculate_significance(
                percentage,
                volume["current_volume"],
                volume["average_volume"],
                market_change,
                news["score"],
            )
            reasons = generate_explanation(
                percentage,
                significance["score"],
                volume["current_volume"],
                volume["average_volume"],
                market_change,
                news,
            )

            history = (
                db.query(MarketSnapshot)
                .filter(MarketSnapshot.symbol == stock.symbol)
                .order_by(MarketSnapshot.timestamp.desc())
                .limit(14)
                .all()
            )

            return {
                "symbol": stock.symbol,
                "price": current.price,
                "change_percent": percentage,
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
                "reasons": reasons if previous else ["First market snapshot"],
                "status": "ok",
                "history": [
                    {"price": item.price, "timestamp": item.timestamp.isoformat()}
                    for item in reversed(history)
                ],
            }
        except Exception:
            return {
                "symbol": stock.symbol,
                "status": "error",
                "message": "Unable to fetch market data",
                "history": [],
            }

    stocks = await asyncio.gather(*(load_stock(stock) for stock in watchlist.stocks))
    healthy_stocks = [stock for stock in stocks if stock["status"] == "ok"]
    changes = [stock.get("change_percent", 0) for stock in healthy_stocks]
    gainers = sum(change > 0 for change in changes)
    decliners = sum(change < 0 for change in changes)
    attention = sum(stock.get("severity") != "NORMAL" for stock in healthy_stocks)
    average_change = sum(changes) / len(changes) if changes else 0

    dashboard_snapshot = DashboardSnapshot(
        watchlist_id=watchlist.id,
        tracked_count=len(healthy_stocks),
        average_change=round(average_change, 2),
        gainers=gainers,
        decliners=decliners,
        attention_count=attention,
    )
    db.add(dashboard_snapshot)
    db.commit()
    db.refresh(dashboard_snapshot)

    history_start = datetime.utcnow() - timedelta(days=30)
    trend_rows = (
        db.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.watchlist_id == watchlist.id,
            DashboardSnapshot.captured_at >= history_start,
        )
        .order_by(DashboardSnapshot.captured_at.asc())
        .limit(30)
        .all()
    )

    severity_distribution = {
        "HIGH": sum(stock.get("severity") == "HIGH" for stock in healthy_stocks),
        "MEDIUM": sum(stock.get("severity") == "MEDIUM" for stock in healthy_stocks),
        "NORMAL": sum(stock.get("severity") == "NORMAL" for stock in healthy_stocks),
    }

    return {
        "watchlist_id": watchlist.id,
        "watchlist_name": watchlist.name,
        "captured_at": dashboard_snapshot.captured_at.isoformat(),
        "overview": {
            "tracked_count": len(healthy_stocks),
            "average_change": round(average_change, 2),
            "gainers": gainers,
            "decliners": decliners,
            "attention_count": attention,
        },
        "distribution": severity_distribution,
        "trend": [
            {
                "captured_at": item.captured_at.isoformat(),
                "average_change": item.average_change,
            }
            for item in trend_rows
        ],
        "stocks": sorted(
            stocks,
            key=lambda stock: abs(stock.get("change_percent", 0)),
            reverse=True,
        ),
    }
