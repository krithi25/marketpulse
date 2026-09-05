from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer

from app.database import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(
        Integer,
        ForeignKey("watchlists.id"),
        nullable=False,
        index=True,
    )
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    tracked_count = Column(Integer, nullable=False, default=0)
    average_change = Column(Float, nullable=False, default=0)
    gainers = Column(Integer, nullable=False, default=0)
    decliners = Column(Integer, nullable=False, default=0)
    attention_count = Column(Integer, nullable=False, default=0)
