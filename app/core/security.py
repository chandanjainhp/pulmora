"""Password hashing and JWT token helpers.

* Active passwords are hashed with bcrypt (passlib).
* Users imported from the legacy Django database keep their original
  ``pbkdf2_sha256$...`` hash in ``legacy_password_hash``.  On the first
  successful login the hash is verified with the *Django* algorithm and then
  transparently upgraded to bcrypt.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# --- Password hashing -------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_bcrypt(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _verify_django_pbkdf2_sha256(plain_password: str, encoded: str) -> bool:
    """Verify a Django-style ``pbkdf2_sha256$iterations$salt$hash`` string."""
    try:
        algorithm, iterations, salt, b64_digest = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    # Django stores base64 of the raw digest bytes.
    expected = base64.b64encode(digest).decode("ascii")
    return expected == b64_digest


def verify_password(
    plain_password: str,
    hashed_password: Optional[str],
    legacy_hash: Optional[str] = None,
) -> bool:
    """Verify against the bcrypt hash, falling back to a legacy Django hash."""
    if hashed_password:
        try:
            if verify_bcrypt(plain_password, hashed_password):
                return True
        except Exception:
            pass
    if legacy_hash:
        return _verify_django_pbkdf2_sha256(plain_password, legacy_hash)
    return False


# --- JWT tokens -------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def create_access_token(
    subject: str, expires_minutes: Optional[int] = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Return the subject (username) or ``None`` if the token is invalid."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None


# --- Dependencies -----------------------------------------------------------

def _token_from_request(request) -> Optional[str]:
    """Bearer header first, then the HttpOnly auth cookie (browser pages)."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.cookies.get(settings.AUTH_COOKIE_NAME)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _token_from_request(request)
    if not token:
        raise credentials_error
    username = decode_access_token(token)
    if not username:
        raise credentials_error
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_error
    return user
