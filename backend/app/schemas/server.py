"""Pydantic schemas for managed server configuration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class FanOverrideBase(BaseModel):
    fan_identifier: str = Field(..., min_length=1, max_length=64)
    min_rpm: int | None = Field(default=None, ge=0)
    max_rpm: int | None = Field(default=None, ge=0)
    lower_temp_c: int | None = Field(default=None, ge=0, le=120)
    upper_temp_c: int | None = Field(default=None, ge=0, le=120)
    profile: dict[str, Any] | None = None


class FanOverrideCreate(FanOverrideBase):
    pass


class FanOverrideRead(FanOverrideBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServerBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    vendor: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$")
    bmc_host: str = Field(..., min_length=1, max_length=255)
    bmc_port: int = Field(default=623, ge=1, le=65535)
    poll_interval_seconds: int = Field(default=300, ge=30, le=86400)
    fan_defaults: dict[str, Any] | None = None
    notification_channel_ids: list[int] | None = Field(default=None)  # List of notification channel IDs to use for this server
    alert_config: dict[str, bool] | None = Field(
        default=None,
        description="Alert settings: enable/disable specific alert types (connectivity, memory_errors, power_failure, intrusion, voltage_issues, system_events, temperature_critical)"
    )
    offline_alert_threshold_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="Alert if server hasn't responded for this many minutes (default: 15)"
    )


class ServerCreate(ServerBase):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None
    fan_overrides: list[FanOverrideCreate] | None = None


class ServerUpdate(ServerBase):
    username: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None
    fan_overrides: list[FanOverrideCreate] | None = None


class ServerRead(ServerBase):
    id: int
    created_at: datetime
    metadata: dict[str, Any] | None = None
    fan_overrides: list[FanOverrideRead] = []

    model_config = ConfigDict(from_attributes=True)
