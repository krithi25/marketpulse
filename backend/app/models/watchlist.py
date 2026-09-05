from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        nullable=False,
        default="My Watchlist"
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="watchlists"
    )

    stocks = relationship(
        "Stock",
        back_populates="watchlist",
        cascade="all, delete-orphan"
    )

    holdings = relationship(
        "PortfolioHolding",
        back_populates="watchlist",
        cascade="all, delete-orphan"
    )