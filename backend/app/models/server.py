"""Database models for managed IPMI servers and fan profiles."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ServerTarget(Base):
    """Managed server with IPMI access credentials and monitoring config."""

    __tablename__ = "server_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor: Mapped[str] = mapped_column(String(32), nullable=False)
    bmc_host: Mapped[str] = mapped_column(String(255), nullable=False)
    bmc_port: Mapped[int] = mapped_column(Integer, default=623)
    username_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_encrypted: Mapped[str | None] = mapped_column(String(1024))
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    fan_defaults: Mapped[dict | None] = mapped_column(JSON, default=None)
    notification_channel_ids: Mapped[list[int] | None] = mapped_column(JSON, default=None)  # List of notification channel IDs
    alert_config: Mapped[dict | None] = mapped_column(JSON, default=None)  # Alert settings: {"memory_errors": true, "power_failure": true, ...}
    offline_alert_threshold_minutes: Mapped[int] = mapped_column(Integer, default=15)  # Alert if offline for this many minutes
    last_successful_poll: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)  # Timestamp of last successful poll
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    fan_overrides: Mapped[list[FanOverride]] = relationship("FanOverride", back_populates="server", cascade="all, delete-orphan")
    active_alerts: Mapped[list["ActiveAlert"]] = relationship("ActiveAlert", back_populates="server", cascade="all, delete-orphan")


class FanOverride(Base):
    """Per-fan override configuration."""

    __tablename__ = "fan_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("server_targets.id", ondelete="CASCADE"))
    fan_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    min_rpm: Mapped[int | None]
    max_rpm: Mapped[int | None]
    lower_temp_c: Mapped[int | None]
    upper_temp_c: Mapped[int | None]
    profile: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    server: Mapped[ServerTarget] = relationship("ServerTarget", back_populates="fan_overrides")
