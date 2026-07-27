from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from threading import RLock

from .models import AuditEvent


class JsonlAuditLogAdapter:
    """Append-only JSONL audit log, partitioned by conversation."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._sequences: dict[str, int] = {}

    async def append(self, event: AuditEvent) -> AuditEvent:
        return await asyncio.to_thread(self._append_sync, event)

    async def list_session_events(
        self, conversation_id: str
    ) -> list[AuditEvent]:
        return await asyncio.to_thread(
            self._list_session_events_sync, conversation_id
        )

    def _append_sync(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            sequence = self._sequences.get(event.conversation_id)
            if sequence is None:
                sequence = self._last_sequence(event.conversation_id)
            sequence += 1
            self._sequences[event.conversation_id] = sequence
            stored = event.model_copy(update={"sequence": sequence})
            path = self._event_path(event.conversation_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(stored.model_dump_json())
                stream.write("\n")
                stream.flush()
            return stored

    def _list_session_events_sync(
        self, conversation_id: str
    ) -> list[AuditEvent]:
        path = self._event_path(conversation_id)
        if not path.exists():
            return []
        with self._lock, path.open("r", encoding="utf-8") as stream:
            return [
                AuditEvent.model_validate_json(line)
                for line in stream
                if line.strip()
            ]

    def _last_sequence(self, conversation_id: str) -> int:
        events = self._list_session_events_sync(conversation_id)
        if not events:
            return 0
        return max(event.sequence or 0 for event in events)

    def _event_path(self, conversation_id: str) -> Path:
        safe_id = hashlib.sha256(
            conversation_id.encode("utf-8")
        ).hexdigest()[:24]
        return self.sessions_dir / safe_id / "events.jsonl"
