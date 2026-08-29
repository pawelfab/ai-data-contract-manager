import json

from contract_forge.adapters.logging.bigquery_app_log_sink import BigQueryAppLogSink
from contract_forge.adapters.logging.local_app_log_sink import LocalAppLogSink
from contract_forge.adapters.logging.sanitizer import REDACTED, sanitize
from contract_forge.application.observability.app_log_recorder import AppLogRecorder
from contract_forge.application.observability.models import AppLogEvent
from contract_forge import server


def test_local_jsonl_and_sanitization(tmp_path):
    sink = LocalAppLogSink(tmp_path)
    sink.emit(AppLogEvent(level="INFO", event="test", data={"Authorization": "secret", "nested": {"token": "abc"}}))
    line = next((tmp_path / "app").glob("*.jsonl")).read_text(encoding="utf-8").splitlines()[0]
    payload = json.loads(line)
    assert payload["data"] == {"Authorization": "***REDACTED***", "nested": {"token": "***REDACTED***"}}


def test_sanitizer_redacts_text_tokens():
    assert "secret" not in sanitize("Authorization: Bearer secret")


def test_sanitizer_redacts_raw_multiline_secrets():
    message = 'credentials: {"type":"service_account","private_key":"raw-private-key"}'
    assert "raw-private-key" not in sanitize(message)
    assert REDACTED in sanitize(message)


def test_bigquery_mapping_and_injected_client():
    class Client:
        def __init__(self): self.calls = []
        def insert_rows_json(self, table, rows): self.calls.append((table, rows)); return []
    client = Client()
    sink = BigQueryAppLogSink("p", "d", client=client)
    event = AppLogEvent(level="ERROR", event="failed", correlation_id="c")
    sink.emit(event)
    assert client.calls[0][0] == "p.d.app_logs"
    assert client.calls[0][1][0]["event"] == "failed"


def test_recorder_ignores_sink_failure():
    class Broken:
        def emit(self, event): raise RuntimeError("down")
    event = AppLogRecorder(Broken()).error("sink_test")
    assert event.event == "sink_test"


def test_recorder_fallback_stderr_is_sanitized(capsys):
    class Broken:
        def emit(self, event):
            raise RuntimeError("password: correct horse battery staple")
    AppLogRecorder(Broken()).error("sink_test")
    stderr = capsys.readouterr().err
    assert "correct horse battery staple" not in stderr
    assert REDACTED in stderr


def test_correlation_id_is_technical_metadata_only(monkeypatch):
    class CaptureRecorder:
        def __init__(self): self.correlations = []
        def emit(self, level, event, **kwargs):
            self.correlations.append(kwargs.get("correlation_id"))

    recorder = CaptureRecorder()
    monkeypatch.setattr(server, "app_log", recorder)

    first = server.contract_analyze({}, correlation_id="AAA")
    second = server.contract_analyze({}, correlation_id="BBB")
    first_description = server.contract_describe(correlation_id="AAA")
    second_description = server.contract_describe(correlation_id="BBB")

    assert first == second
    assert first_description == second_description
    assert "AAA" in recorder.correlations
    assert "BBB" in recorder.correlations
