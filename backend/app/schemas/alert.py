"""Pydantic schemas for active alerts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActiveAlertRead(BaseModel):
    id: int
    server_id: int
    alert_type: str
    message: str
    first_triggered_at: datetime
    last_updated_at: datetime
    cleared_at: datetime | None
    cleared_by: str | None

    model_config = ConfigDict(from_attributes=True)

