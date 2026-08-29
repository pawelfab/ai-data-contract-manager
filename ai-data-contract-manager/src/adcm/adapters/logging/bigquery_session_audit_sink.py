from collections import defaultdict
from threading import Lock
from typing import Any

from adcm.adapters.logging.sanitizer import sanitize
from adcm.application.observability.models import SessionAuditEvent


class BatchInsertError(RuntimeError):
    def __init__(self, errors: Any, count: int):
        super().__init__(f"BigQuery insert failed: {errors}")
        self.failed_event_count = count


class BigQuerySessionAuditSink:
    def __init__(self, project: str, dataset: str, table: str = "session_audit", client: Any = None):
        self.project = project
        self.table = f"{project}.{dataset}.{table}"
        self.client = client
        self._buffers: dict[tuple[str, int, str | None], list[dict[str, Any]]] = defaultdict(list)
        self._lock = Lock()

    def _client(self):
        if self.client is None:
            from google.cloud import bigquery
            self.client = bigquery.Client(project=self.project)
        return self.client

    def emit(self, event: SessionAuditEvent) -> None:
        key = (event.session_id, event.turn_no, event.correlation_id)
        with self._lock:
            self._buffers[key].append(sanitize(event.model_dump(mode="json")))
            rows = self._buffers.pop(key) if event.event_type in {"turn.completed", "turn.failed"} else None
        if rows is not None:
            try:
                errors = self._client().insert_rows_json(self.table, rows)
            except Exception as exc:
                raise BatchInsertError(type(exc).__name__, len(rows)) from exc
            if errors:
                raise BatchInsertError(errors, len(rows))
