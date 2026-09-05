from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Watchlist
from app.services.dashboard import build_dashboard
from app.security import get_owned_watchlist

router = APIRouter()


@router.get("/{watchlist_id}")
async def get_dashboard(
    watchlist_id: int,
    db: Session = Depends(get_db),
    watchlist: Watchlist = Depends(get_owned_watchlist),
):
    return await build_dashboard(watchlist, db)
