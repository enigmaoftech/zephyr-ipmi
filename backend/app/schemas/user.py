"""Pydantic schemas for user operations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    role: str | None = Field(default="user", pattern=r"^[a-zA-Z0-9_\-]+$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_\-]+$")


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserUsernameUpdate(BaseModel):
    new_username: str = Field(..., min_length=3, max_length=64)
