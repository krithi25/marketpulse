from sqlalchemy import Column, Integer, ForeignKey, DateTime
from datetime import datetime

from app.database import Base


class WatchlistVisit(Base):
    __tablename__ = "watchlist_visits"

    id = Column(Integer, primary_key=True, index=True)

    watchlist_id = Column(
        Integer,
        ForeignKey("watchlists.id"),
        nullable=False
    )

    visited_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )