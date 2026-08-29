import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from contract_forge.application.observability.models import AppLogEvent

from .sanitizer import sanitize

_locks: dict[Path, threading.Lock] = {}
_locks_guard = threading.Lock()


class LocalAppLogSink:
    def __init__(self, log_dir: str | Path = "logs") -> None:
        self.root = Path(log_dir) / "app"

    def emit(self, event: AppLogEvent) -> None:
        path = self.root / f"{event.timestamp.astimezone(timezone.utc):%Y-%m-%d}.jsonl"
        with _locks_guard:
            lock = _locks.setdefault(path, threading.Lock())
        payload = sanitize(event.model_dump(mode="json"))
        self.root.mkdir(parents=True, exist_ok=True)
        with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
