from typing import Any

from adcm.adapters.logging.sanitizer import sanitize
from adcm.application.observability.models import AppLogEvent


class BigQueryAppLogSink:
    def __init__(self, project: str, dataset: str, table: str = "app_logs", client: Any = None):
        self.project = project
        self.table = f"{project}.{dataset}.{table}"
        self.client = client

    def _client(self):
        if self.client is None:
            from google.cloud import bigquery
            self.client = bigquery.Client(project=self.project)
        return self.client

    def emit(self, event: AppLogEvent) -> None:
        row = sanitize(event.model_dump(mode="json"))
        errors = self._client().insert_rows_json(self.table, [row])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors!r}")
