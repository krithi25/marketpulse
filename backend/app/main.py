import os

from fastapi import FastAPI

from app.database import Base, engine
from app.models import User, Watchlist, Stock

from app.routes import auth, dashboard, portfolio, watchlist, market
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Keep existing SQLite databases usable after adding authentication.
with engine.begin() as connection:
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)")}
    if "password_hash" not in columns:
        connection.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR")


app = FastAPI(
    title="MarketPulse API",
    description="Smart market watchlist API",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_origin_regex=r"https://marketpulse-web(?:-[a-z0-9-]+)?\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)


app.include_router(
    watchlist.router,
    prefix="/api/watchlist",
    tags=["Watchlist"]
)


app.include_router(
    market.router,
    prefix="/api/market",
    tags=["Market Data"]
)


app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


app.include_router(
    portfolio.router,
    prefix="/api/portfolio",
    tags=["Portfolio"]
)


@app.get("/")
def root():
    return {
        "message": "MarketPulse API is running 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }