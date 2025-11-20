"""Reusable dependencies for FastAPI routes."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import SecretManager, SessionSigner
from app.db.session import get_session
from app.models.user import User
from app.services.users import get_user_by_username


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session


async def get_secret_manager() -> SecretManager:
    return SecretManager()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()
    token = request.cookies.get("zephyr_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    signer = SessionSigner()
    try:
        payload = signer.loads(token, max_age=settings.access_token_expire_minutes * 60)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
