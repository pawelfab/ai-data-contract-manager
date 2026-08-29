from typing import Any

from contract_forge.application.observability.models import AppLogEvent

from .sanitizer import sanitize


class BigQueryAppLogSink:
    """BigQuery adapter. The SDK is imported only when a client is constructed."""

    def __init__(self, project: str, dataset: str, table: str = "app_logs", client: Any = None) -> None:
        self.project, self.client, self.table_ref = project, client, f"{project}.{dataset}.{table}"

    def _client(self) -> Any:
        if self.client is None:
            from google.cloud import bigquery
            self.client = bigquery.Client(project=self.project)
        return self.client

    @staticmethod
    def to_row(event: AppLogEvent) -> dict[str, Any]:
        return sanitize(event.model_dump(mode="json"))

    def emit(self, event: AppLogEvent) -> None:
        errors = self._client().insert_rows_json(self.table_ref, [self.to_row(event)])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors!r}")
