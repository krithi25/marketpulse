import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

is_vercel = os.getenv("VERCEL") or os.getenv("VERCEL_ENV")
configured_database_url = os.getenv("DATABASE_URL")
if is_vercel and (not configured_database_url or configured_database_url.startswith("sqlite:")):
    DATABASE_URL = "sqlite:////tmp/marketpulse.db"
else:
    DATABASE_URL = configured_database_url or "sqlite:///./marketpulse.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()