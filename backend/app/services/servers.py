"""Service layer for server configuration persistence."""
from __future__ import annotations

import json
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import SecretManager
from app.models.server import FanOverride, ServerTarget
from app.schemas.server import FanOverrideCreate, ServerCreate, ServerUpdate


def _decrypt_metadata(server: ServerTarget, secret_manager: SecretManager) -> dict[str, Any] | None:
    """Decrypt and parse server metadata."""
    if not server.metadata_encrypted:
        return None
    try:
        decrypted = secret_manager.decrypt(server.metadata_encrypted)
        return json.loads(decrypted) if decrypted else None
    except (ValueError, json.JSONDecodeError):
        return None


async def list_servers(session: AsyncSession) -> list[ServerTarget]:
    result = await session.execute(
        select(ServerTarget)
        .options(selectinload(ServerTarget.fan_overrides))
        .order_by(ServerTarget.name)
    )
    return result.scalars().unique().all()


async def get_server(session: AsyncSession, server_id: int) -> ServerTarget | None:
    result = await session.execute(
        select(ServerTarget)
        .options(selectinload(ServerTarget.fan_overrides))
        .where(ServerTarget.id == server_id)
    )
    return result.scalar_one_or_none()


async def create_server(session: AsyncSession, data: ServerCreate, secret_manager: SecretManager) -> ServerTarget:
    username_encrypted = secret_manager.encrypt(data.username)
    password_encrypted = secret_manager.encrypt(data.password)
    metadata_encrypted = (
        secret_manager.encrypt(json.dumps(data.metadata)) if data.metadata else None
    )

    server = ServerTarget(
        name=data.name,
        vendor=data.vendor.lower(),
        bmc_host=data.bmc_host,
        bmc_port=data.bmc_port,
        username_encrypted=username_encrypted,
        password_encrypted=password_encrypted,
        metadata_encrypted=metadata_encrypted,
        poll_interval_seconds=data.poll_interval_seconds,
        fan_defaults=data.fan_defaults,
        notification_channel_ids=data.notification_channel_ids,
        alert_config=data.alert_config,
        offline_alert_threshold_minutes=data.offline_alert_threshold_minutes,
    )

    if data.fan_overrides:
        server.fan_overrides = [
            FanOverride(
                fan_identifier=override.fan_identifier,
                min_rpm=override.min_rpm,
                max_rpm=override.max_rpm,
                lower_temp_c=override.lower_temp_c,
                upper_temp_c=override.upper_temp_c,
                profile=override.profile,
            )
            for override in _normalize_overrides(data.fan_overrides)
        ]

    session.add(server)
    await session.flush()
    await session.refresh(server, ["fan_overrides"])
    return server


async def update_server(
    session: AsyncSession, server_id: int, data: ServerUpdate, secret_manager: SecretManager
) -> ServerTarget:
    server = await get_server(session, server_id)
    if not server:
        raise ValueError(f"Server {server_id} not found")

    if data.name is not None:
        server.name = data.name
    if data.vendor is not None:
        server.vendor = data.vendor.lower()
    if data.bmc_host is not None:
        server.bmc_host = data.bmc_host
    if data.bmc_port is not None:
        server.bmc_port = data.bmc_port
    if data.poll_interval_seconds is not None:
        server.poll_interval_seconds = data.poll_interval_seconds
    if data.username is not None:
        server.username_encrypted = secret_manager.encrypt(data.username)
    if data.password is not None:
        server.password_encrypted = secret_manager.encrypt(data.password)
    # Always update metadata - handle empty dict, None, or valid dict
    if hasattr(data, 'metadata'):
        if data.metadata is None:
            server.metadata_encrypted = None
        elif isinstance(data.metadata, dict):
            # Check if dict is effectively empty (no meaningful values)
            if len(data.metadata) == 0 or all(not v or (isinstance(v, str) and not v.strip()) for v in data.metadata.values()):
                server.metadata_encrypted = None
            else:
                server.metadata_encrypted = secret_manager.encrypt(json.dumps(data.metadata))
        else:
            # Non-dict metadata - encrypt it
            server.metadata_encrypted = secret_manager.encrypt(json.dumps(data.metadata))
    if data.fan_defaults is not None:
        server.fan_defaults = data.fan_defaults
    if data.notification_channel_ids is not None:
        server.notification_channel_ids = data.notification_channel_ids
    if data.alert_config is not None:
        # Store old alert config to detect disabled alert types
        old_alert_config = server.alert_config or {}
        new_alert_config = data.alert_config or {}
        
        # Update alert config
        server.alert_config = data.alert_config
        
        # Clear alerts for any alert types that were disabled
        # Import here to avoid circular dependencies
        from app.services.scheduler import _clear_alert_if_active
        
        for alert_type, was_enabled in old_alert_config.items():
            # Check if this alert type was enabled before but is now disabled
            is_now_enabled = new_alert_config.get(alert_type, False)
            if was_enabled and not is_now_enabled:
                # Alert type was disabled - clear any active alerts
                await _clear_alert_if_active(session, server, alert_type, "manual")
    
    if data.offline_alert_threshold_minutes is not None:
        server.offline_alert_threshold_minutes = data.offline_alert_threshold_minutes
    if data.fan_overrides is not None:
        # Clear existing overrides
        for override in server.fan_overrides:
            await session.delete(override)
        server.fan_overrides = []
        # Add new overrides
        if data.fan_overrides:
            server.fan_overrides = [
                FanOverride(
                    fan_identifier=override.fan_identifier,
                    min_rpm=override.min_rpm,
                    max_rpm=override.max_rpm,
                    lower_temp_c=override.lower_temp_c,
                    upper_temp_c=override.upper_temp_c,
                    profile=override.profile,
                )
                for override in _normalize_overrides(data.fan_overrides)
            ]

    await session.flush()
    await session.refresh(server, ["fan_overrides"])
    return server


async def delete_server(session: AsyncSession, server_id: int) -> None:
    server = await get_server(session, server_id)
    if not server:
        raise ValueError(f"Server {server_id} not found")
    await session.delete(server)
    await session.flush()


def _normalize_overrides(overrides: Iterable[FanOverrideCreate]) -> list[FanOverrideCreate]:
    normalized: list[FanOverrideCreate] = []
    for override in overrides:
        payload = override.copy(update={})
        normalized.append(payload)
    return normalized
