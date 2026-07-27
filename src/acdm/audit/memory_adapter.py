from __future__ import annotations

import asyncio

from .models import AuditEvent


class InMemoryAuditLogAdapter:
    """Deterministic adapter intended for unit tests."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._sequences: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def append(self, event: AuditEvent) -> AuditEvent:
        async with self._lock:
            sequence = self._sequences.get(event.conversation_id, 0) + 1
            self._sequences[event.conversation_id] = sequence
            stored = event.model_copy(update={"sequence": sequence})
            self.events.append(stored)
            return stored

    async def list_session_events(
        self, conversation_id: str
    ) -> list[AuditEvent]:
        async with self._lock:
            return [
                event
                for event in self.events
                if event.conversation_id == conversation_id
            ]
