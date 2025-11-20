"""Database models for notification channels and alert rules."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationChannel(Base):
    """Notification channel configuration (Teams, Slack, Discord, Telegram)."""

    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # teams, slack, discord, telegram
    endpoint_encrypted: Mapped[str] = mapped_column(String(1024), nullable=False)  # webhook URL or token
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_metadata: Mapped[dict | None] = mapped_column(JSON, default=None)  # additional config like chat_id for Telegram
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    alert_rules: Mapped[list["AlertRule"]] = relationship("AlertRule", back_populates="channel", cascade="all, delete-orphan")


class AlertRule(Base):
    """Alert trigger rules mapping to notification channels."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("notification_channels.id", ondelete="CASCADE"))
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)  # connectivity, intrusion, memory_error, etc.
    threshold: Mapped[int | None] = mapped_column(Integer, default=None)  # e.g., failure count before alerting
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    channel: Mapped[NotificationChannel] = relationship("NotificationChannel", back_populates="alert_rules")
