from __future__ import annotations

from typing import Protocol

from .models import AuditEvent


class AuditLogPort(Protocol):
    """Storage port implemented by JSONL now and a database in the future."""

    async def append(self, event: AuditEvent) -> AuditEvent: ...

    async def list_session_events(
        self, conversation_id: str
    ) -> list[AuditEvent]: ...


class NullAuditLogAdapter:
    async def append(self, event: AuditEvent) -> AuditEvent:
        return event

    async def list_session_events(
        self, conversation_id: str
    ) -> list[AuditEvent]:
        return []
