from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(
        String,
        nullable=False
    )

    watchlist_id = Column(
        Integer,
        ForeignKey("watchlists.id"),
        nullable=False
    )

    added_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    watchlist = relationship(
        "Watchlist",
        back_populates="stocks"
    )

    __table_args__ = (
        UniqueConstraint(
            "watchlist_id",
            "symbol",
            name="unique_watchlist_stock"
        ),
    )