"""Pydantic schemas for notification channels and alert rules."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class AlertRuleBase(BaseModel):
    trigger_type: str = Field(..., min_length=1, max_length=64)
    threshold: int | None = Field(default=None, ge=1)
    enabled: bool = Field(default=True)


class AlertRuleCreate(AlertRuleBase):
    channel_id: int


class AlertRuleRead(AlertRuleBase):
    id: int
    channel_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., pattern=r"^(teams|slack|discord|telegram)$")
    enabled: bool = Field(default=True)
    metadata: dict[str, Any] | None = Field(default=None, alias="channel_metadata")


class NotificationChannelCreate(NotificationChannelBase):
    endpoint: str = Field(..., min_length=1)  # webhook URL or token, will be encrypted
    chat_id: str | None = Field(default=None)  # for Telegram


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    endpoint: str | None = Field(default=None, min_length=1)
    chat_id: str | None = None
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class NotificationChannelRead(NotificationChannelBase):
    id: int
    created_at: datetime
    alert_rules: list[AlertRuleRead] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
