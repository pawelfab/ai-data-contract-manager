from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditEvent(BaseModel):
    """Versioned, storage-independent audit event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence: int | None = None
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    conversation_id: str
    run_id: str | None = None
    event_type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    redaction_applied: bool = False
