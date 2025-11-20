"""Notification channel endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_secret_manager
from app.core.security import SecretManager
from app.models.user import User
from app.schemas.notification import (
    AlertRuleCreate,
    AlertRuleRead,
    NotificationChannelCreate,
    NotificationChannelRead,
    NotificationChannelUpdate,
)
from app.services import notification_channels as channel_service
from app.services.notifications import (
    DiscordProvider,
    NotificationMessage,
    NotificationError,
    SlackProvider,
    TelegramProvider,
    TeamsProvider,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/channels", response_model=list[NotificationChannelRead])
async def list_channels(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[NotificationChannelRead]:
    channels = await channel_service.list_channels(session)
    return [NotificationChannelRead.model_validate(item) for item in channels]


@router.post("/channels", response_model=NotificationChannelRead, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: NotificationChannelCreate,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> NotificationChannelRead:
    channel = await channel_service.create_channel(session, payload, secret_manager)
    await session.commit()
    return NotificationChannelRead.model_validate(channel)


@router.get("/channels/{channel_id}", response_model=NotificationChannelRead)
async def get_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> NotificationChannelRead:
    channel = await channel_service.get_channel(session, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return NotificationChannelRead.model_validate(channel)


@router.put("/channels/{channel_id}", response_model=NotificationChannelRead)
async def update_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> NotificationChannelRead:
    channel = await channel_service.get_channel(session, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    updated = await channel_service.update_channel(session, channel, payload, secret_manager)
    await session.commit()
    return NotificationChannelRead.model_validate(updated)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    channel = await channel_service.get_channel(session, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    await channel_service.delete_channel(session, channel)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/channels/{channel_id}/rules", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    channel_id: int,
    payload: AlertRuleCreate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertRuleRead:
    channel = await channel_service.get_channel(session, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    rule = await channel_service.create_alert_rule(
        session, AlertRuleCreate(**payload.model_dump(), channel_id=channel_id)
    )
    await session.commit()
    return AlertRuleRead.model_validate(rule)


@router.post("/channels/{channel_id}/test", status_code=status.HTTP_200_OK)
async def test_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    channel = await channel_service.get_channel(session, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    if not channel.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Channel is disabled")

    # Create provider based on channel type
    if channel.type == "slack":
        provider = SlackProvider(channel.endpoint_encrypted, secret_manager)
    elif channel.type == "teams":
        provider = TeamsProvider(channel.endpoint_encrypted, secret_manager)
    elif channel.type == "discord":
        provider = DiscordProvider(channel.endpoint_encrypted, secret_manager)
    elif channel.type == "telegram":
        chat_id = channel.channel_metadata.get("chat_id", "") if channel.channel_metadata else ""
        if not chat_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram chat ID not configured")
        provider = TelegramProvider(channel.endpoint_encrypted, chat_id, secret_manager)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported channel type: {channel.type}")

    # Send test message
    test_message = NotificationMessage(
        subject="Test Notification",
        body=f"This is a test notification from Zephyr IPMI. If you receive this, your {channel.type.upper()} integration is working correctly!",
    )

    try:
        await provider.send(test_message)
        return {"status": "success", "message": f"Test notification sent successfully to {channel.name}"}
    except NotificationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
