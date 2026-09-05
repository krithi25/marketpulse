from sqlalchemy.orm import Session

from app.models.snapshot import MarketSnapshot


def save_snapshot(
    db: Session,
    quote: dict
):
    snapshot = MarketSnapshot(
        symbol=quote["symbol"],
        price=quote["price"],
        change=quote.get("change"),
        change_percent=quote.get("change_percent"),
        high=quote.get("high"),
        low=quote.get("low"),
        open=quote.get("open"),
        previous_close=quote.get("previous_close")
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot
def get_previous_snapshot(
    db: Session,
    symbol: str,
    current_snapshot_id: int
):
    return (
        db.query(MarketSnapshot)
        .filter(
            MarketSnapshot.symbol == symbol.upper(),
            MarketSnapshot.id < current_snapshot_id
        )
        .order_by(
            MarketSnapshot.id.desc()
        )
        .first()
    )