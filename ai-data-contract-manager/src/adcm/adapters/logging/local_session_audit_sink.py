import base64
import json
import re
import threading
from pathlib import Path

from adcm.adapters.logging.sanitizer import sanitize
from adcm.application.observability.models import SessionAuditEvent

_lock = threading.Lock()


class LocalSessionAuditSink:
    def __init__(self, root: str | Path = "logs"):
        self.root = Path(root)

    def emit(self, event: SessionAuditEvent) -> None:
        if re.fullmatch(r"[A-Za-z0-9_-]+", event.session_id):
            safe = event.session_id
        else:
            encoded = base64.urlsafe_b64encode(event.session_id.encode("utf-8")).decode("ascii").rstrip("=")
            safe = f"encoded-{encoded}" or "session"
        path = self.root / "sessions" / f"{safe}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(sanitize(event.model_dump(mode="json")), ensure_ascii=False)
        with _lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
