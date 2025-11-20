"""Database models for active alerts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActiveAlert(Base):
    """Track currently active alerts for servers."""

    __tablename__ = "active_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("server_targets.id", ondelete="CASCADE"))
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., "voltage_issues", "memory_errors"
    message: Mapped[str] = mapped_column(String(2048), nullable=False)  # Alert message/details
    first_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    cleared_by: Mapped[str | None] = mapped_column(String(64), default=None)  # "auto" or "manual" or None

    server: Mapped["ServerTarget"] = relationship("ServerTarget", back_populates="active_alerts")

    __table_args__ = (
        UniqueConstraint("server_id", "alert_type", name="uq_server_alert_type"),
    )

