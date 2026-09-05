from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from app.database import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    symbol = Column(
        String,
        nullable=False,
        index=True
    )

    price = Column(
        Float,
        nullable=False
    )

    change = Column(
        Float,
        nullable=True
    )

    change_percent = Column(
        Float,
        nullable=True
    )

    high = Column(
        Float,
        nullable=True
    )

    low = Column(
        Float,
        nullable=True
    )

    open = Column(
        Float,
        nullable=True
    )

    previous_close = Column(
        Float,
        nullable=True
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )