"""User service functions for CRUD and authentication."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import PasswordHasher
from app.models.user import User
from app.schemas.user import UserCreate


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    normalized = username.lower()
    result = await session.execute(select(User).where(User.username == normalized))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_in: UserCreate, allow_existing: bool = True) -> User:
    if not allow_existing:
        existing_any = await users_exist(session)
        if existing_any:
            raise ValueError("Initial admin already exists")
    password_hash = PasswordHasher.hash(user_in.password)
    user = User(username=user_in.username, password_hash=password_hash, role=user_in.role or "user")
    session.add(user)
    await session.flush()
    return user


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(session, username)
    if not user:
        return None
    if not PasswordHasher.verify(password, user.password_hash):
        return None
    return user


async def users_exist(session: AsyncSession) -> bool:
    result = await session.execute(select(User.id))
    return result.first() is not None


async def update_user_password(session: AsyncSession, user: User, current_password: str, new_password: str) -> User:
    if not PasswordHasher.verify(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    user.password_hash = PasswordHasher.hash(new_password)
    await session.flush()
    return user


async def update_user_username(session: AsyncSession, user: User, new_username: str) -> User:
    normalized = new_username.lower()
    existing = await get_user_by_username(session, normalized)
    if existing and existing.id != user.id:
        raise ValueError("Username already taken")
    user.username = normalized
    await session.flush()
    return user
