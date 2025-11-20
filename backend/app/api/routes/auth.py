"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.security import SessionSigner
from app.models.user import User
from app.schemas.auth import AuthStatus, LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserPasswordUpdate, UserRead, UserUsernameUpdate
from app.services.users import (
    authenticate_user,
    create_user,
    get_user_by_username,
    update_user_password,
    update_user_username,
    users_exist,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "zephyr_session"


@router.get("/status", response_model=AuthStatus)
async def auth_status(session: AsyncSession = Depends(get_db)) -> AuthStatus:
    return AuthStatus(has_users=await users_exist(session))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_db)) -> UserRead:
    existing_any = await users_exist(session)
    if existing_any:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin already created")

    normalized = payload.copy(update={"username": payload.username.lower(), "role": payload.role or "admin"})
    existing = await get_user_by_username(session, normalized.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    try:
        user = await create_user(session, normalized, allow_existing=False)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await session.commit()
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await authenticate_user(session, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    signer = SessionSigner()
    token = signer.dumps({"sub": user.username})
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/password", response_model=UserRead)
async def change_password(
    payload: UserPasswordUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    try:
        updated = await update_user_password(session, current_user, payload.current_password, payload.new_password)
        await session.commit()
        return UserRead.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/username", response_model=UserRead)
async def change_username(
    payload: UserUsernameUpdate,
    response: Response,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    try:
        updated = await update_user_username(session, current_user, payload.new_username)
        await session.commit()
        # Update session cookie with new username
        signer = SessionSigner()
        token = signer.dumps({"sub": updated.username})
        settings = get_settings()
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60,
        )
        return UserRead.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
