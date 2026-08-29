import json
import threading
from datetime import timezone
from pathlib import Path

from adcm.adapters.logging.sanitizer import sanitize
from adcm.application.observability.models import AppLogEvent

_lock = threading.Lock()


class LocalAppLogSink:
    def __init__(self, root: str | Path = "logs"):
        self.root = Path(root)

    def emit(self, event: AppLogEvent) -> None:
        stamp = event.timestamp.astimezone(timezone.utc).date().isoformat()
        path = self.root / "app" / f"{stamp}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(sanitize(event.model_dump(mode="json")), ensure_ascii=False)
        with _lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

