from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Watchlist
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter()


class AuthPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


def auth_response(user: User, watchlist: Watchlist, message: str):
    return {
        "message": message,
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email},
        "watchlist": {"id": watchlist.id, "name": watchlist.name},
    }


@router.post("/register")
def register(payload: AuthPayload, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    watchlist = Watchlist(name="My Watchlist", user_id=user.id)
    db.add(watchlist)
    db.commit()
    db.refresh(user)
    db.refresh(watchlist)
    return auth_response(user, watchlist, "Account created")


@router.post("/login")
def login(payload: AuthPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.id.asc()).first()
    if not watchlist:
        watchlist = Watchlist(name="My Watchlist", user_id=user.id)
        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)
    return auth_response(user, watchlist, "Signed in")


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).order_by(Watchlist.id.asc()).first()
    return {
        "user": {"id": current_user.id, "email": current_user.email},
        "watchlist": {"id": watchlist.id, "name": watchlist.name} if watchlist else None,
    }
