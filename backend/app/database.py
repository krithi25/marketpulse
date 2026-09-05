import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

default_database_url = "sqlite:////tmp/marketpulse.db" if os.getenv("VERCEL") else "sqlite:///./marketpulse.db"
DATABASE_URL = os.getenv("DATABASE_URL", default_database_url)

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