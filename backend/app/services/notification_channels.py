"""Service layer for notification channel persistence."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import SecretManager
from app.models.notification import AlertRule, NotificationChannel
from app.schemas.notification import AlertRuleCreate, NotificationChannelCreate, NotificationChannelUpdate


async def list_channels(session: AsyncSession) -> list[NotificationChannel]:
    result = await session.execute(
        select(NotificationChannel)
        .options(selectinload(NotificationChannel.alert_rules))
        .order_by(NotificationChannel.created_at.desc())
    )
    return result.scalars().unique().all()


async def get_channel(session: AsyncSession, channel_id: int) -> NotificationChannel | None:
    result = await session.execute(
        select(NotificationChannel)
        .options(selectinload(NotificationChannel.alert_rules))
        .where(NotificationChannel.id == channel_id)
    )
    return result.scalar_one_or_none()


async def create_channel(
    session: AsyncSession, data: NotificationChannelCreate, secret_manager: SecretManager
) -> NotificationChannel:
    endpoint_encrypted = secret_manager.encrypt(data.endpoint)
    channel_metadata = data.metadata or {}
    if data.type == "telegram" and data.chat_id:
        channel_metadata["chat_id"] = data.chat_id

    channel = NotificationChannel(
        name=data.name,
        type=data.type.lower(),
        endpoint_encrypted=endpoint_encrypted,
        enabled=data.enabled,
        channel_metadata=channel_metadata if channel_metadata else None,
    )
    session.add(channel)
    await session.flush()
    await session.refresh(channel, ["alert_rules"])
    return channel


async def update_channel(
    session: AsyncSession,
    channel: NotificationChannel,
    data: NotificationChannelUpdate,
    secret_manager: SecretManager,
) -> NotificationChannel:
    if data.name is not None:
        channel.name = data.name
    if data.endpoint is not None:
        channel.endpoint_encrypted = secret_manager.encrypt(data.endpoint)
    if data.enabled is not None:
        channel.enabled = data.enabled
    if data.chat_id is not None:
        if channel.channel_metadata is None:
            channel.channel_metadata = {}
        channel.channel_metadata["chat_id"] = data.chat_id
    if data.metadata is not None:
        channel.channel_metadata = data.metadata

    await session.flush()
    await session.refresh(channel, ["alert_rules"])
    return channel


async def delete_channel(session: AsyncSession, channel: NotificationChannel) -> None:
    await session.delete(channel)
    await session.flush()


async def create_alert_rule(session: AsyncSession, data: AlertRuleCreate) -> AlertRule:
    rule = AlertRule(
        channel_id=data.channel_id,
        trigger_type=data.trigger_type,
        threshold=data.threshold,
        enabled=data.enabled,
    )
    session.add(rule)
    await session.flush()
    return rule
