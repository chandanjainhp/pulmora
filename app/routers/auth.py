"""Authentication endpoints: register, login (JWT), me."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(
        password, user.hashed_password, user.legacy_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Transparent upgrade: legacy Django pbkdf2 hash -> bcrypt on first login.
    if user.legacy_password_hash is not None:
        user.hashed_password = hash_password(password)
        user.legacy_password_hash = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    # Same messages as the original signup view.
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password not matching..",
        )
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username Taken"
        )
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
        )
    user = User(
        username=payload.username,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username Taken"
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Login and receive a JWT")
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """OAuth2 password flow: send ``username``/``password`` as form fields."""
    user = _authenticate(db, form.username, form.password)
    return Token(access_token=create_access_token(subject=user.username))


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
