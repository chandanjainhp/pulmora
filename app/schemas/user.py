"""Pydantic schemas for authentication and users."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """POST /auth/register payload (mirrors the original signup form)."""

    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    username: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Optional JSON body for /auth/login (form-encoded is also supported)."""

    username: str
    password: str
