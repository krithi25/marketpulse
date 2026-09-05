# MarketPulse 🚀

A smart market watchlist that helps users understand
what meaningfully changed since they last checked.

## Tech Stack

- React
- FastAPI
- Python
- SQLite
- SQLAlchemy

## Core Idea

Instead of simply showing current stock prices,
MarketPulse identifies meaningful changes and explains
why they deserve attention.

## Architecture

React Frontend
      ↓
FastAPI Backend
      ↓
Business Logic
      ↓
Database / Market Data Provider

## Run locally

Set `FINNHUB_API_KEY` in `backend/.env`, then start the backend from `backend`:

```powershell
uvicorn app.main:app --reload
```

Start the frontend from `frontend` with `npm run dev`.

## Docker

Create a `.env` file beside `docker-compose.yml`:

```env
FINNHUB_API_KEY=your_key_here
MARKETPULSE_TOKEN_SECRET=replace_this_in_production
```

Then run:

```powershell
docker compose up --build
```

The frontend is available at `http://localhost:5173` and the API at `http://localhost:8000`.

## Tests

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Market quotes are cached for 30 seconds. Volume, news, and symbol-search responses are cached for 5 minutes to reduce duplicate third-party API requests.