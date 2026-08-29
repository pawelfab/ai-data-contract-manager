import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from adcm.adapters.logging.bigquery_app_log_sink import BigQueryAppLogSink
from adcm.adapters.logging.bigquery_session_audit_sink import BigQuerySessionAuditSink
from adcm.adapters.logging.local_app_log_sink import LocalAppLogSink
from adcm.adapters.logging.local_session_audit_sink import LocalSessionAuditSink
from adcm.adapters.logging.sanitizer import REDACTED, sanitize
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.models import AppLogEvent, SessionAuditEvent
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder


def test_local_sinks_jsonl_and_session_isolation(tmp_path):
    app = LocalAppLogSink(tmp_path)
    app.emit(AppLogEvent(level="INFO", service="adcm", environment="test", component="x", event="started",
                         timestamp=datetime(2026, 8, 29, tzinfo=timezone.utc)))
    session = LocalSessionAuditSink(tmp_path)
    session.emit(SessionAuditEvent(session_id="aaa", turn_no=1, event_type="turn.started"))
    session.emit(SessionAuditEvent(session_id="aaa", turn_no=1, event_type="intent.resolved"))
    session.emit(SessionAuditEvent(session_id="bbb", turn_no=1, event_type="turn.started"))
    assert len((tmp_path / "app/2026-08-29.jsonl").read_text().splitlines()) == 1
    assert len((tmp_path / "sessions/aaa.jsonl").read_text().splitlines()) == 2
    assert len((tmp_path / "sessions/bbb.jsonl").read_text().splitlines()) == 1


def test_sanitizer_nested_and_bearer():
    result = sanitize({"API_KEY": "secret", "nested": {"password": "pw"}, "text": "Bearer abc.def", "message": "api_key=raw-secret", "token_count": 42})
    assert result["API_KEY"] == REDACTED
    assert result["nested"]["password"] == REDACTED
    assert result["text"] == f"Bearer {REDACTED}"
    assert result["message"] == f"api_key={REDACTED}"
    assert result["token_count"] == 42


def test_sanitizer_redacts_multiline_and_multiword_secrets():
    samples = {
        'credentials: {"type":"service_account","private_key":"raw-private-key"}': "raw-private-key",
        "private_key=-----BEGIN PRIVATE KEY-----\nraw-key-material\n-----END PRIVATE KEY-----": "raw-key-material",
        "cookie: session=raw-cookie; other=value": "raw-cookie",
        "password: correct horse battery staple": "correct horse battery staple",
    }
    for message, secret in samples.items():
        assert secret not in sanitize(message)


def test_local_session_sink_sanitizes_raw_user_message(tmp_path):
    sink = LocalSessionAuditSink(tmp_path)
    sink.emit(
        SessionAuditEvent(
            session_id="aaa",
            turn_no=1,
            event_type="user.message.received",
            data={"message": "credentials: {\"private_key\":\"raw-private-key\"}"},
        )
    )
    content = (tmp_path / "sessions" / "aaa.jsonl").read_text(encoding="utf-8")
    assert "raw-private-key" not in content
    assert REDACTED in content


def test_bigquery_session_batches_until_terminal():
    class Client:
        def __init__(self): self.calls = []
        def insert_rows_json(self, table, rows): self.calls.append((table, rows)); return []
    client = Client()
    sink = BigQuerySessionAuditSink("p", "d", client=client)
    sink.emit(SessionAuditEvent(session_id="a", turn_no=1, correlation_id="c", event_type="intent.resolved", data={"x": 1}))
    assert client.calls == []
    sink.emit(SessionAuditEvent(session_id="a", turn_no=1, correlation_id="c", event_type="turn.completed", data={}))
    assert len(client.calls) == 1 and len(client.calls[0][1]) == 2


def test_bigquery_session_keeps_interleaved_turn_buffers_separate():
    class Client:
        def __init__(self): self.calls = []
        def insert_rows_json(self, table, rows): self.calls.append((table, rows)); return []
    client = Client()
    sink = BigQuerySessionAuditSink("p", "d", client=client)
    sink.emit(SessionAuditEvent(session_id="a", turn_no=1, correlation_id="a1", event_type="turn.started"))
    sink.emit(SessionAuditEvent(session_id="b", turn_no=4, correlation_id="b4", event_type="turn.started"))
    sink.emit(SessionAuditEvent(session_id="a", turn_no=1, correlation_id="a1", event_type="turn.completed"))
    assert len(client.calls) == 1
    assert {row["session_id"] for row in client.calls[0][1]} == {"a"}
    sink.emit(SessionAuditEvent(session_id="b", turn_no=4, correlation_id="b4", event_type="turn.failed"))
    assert len(client.calls) == 2
    assert {row["session_id"] for row in client.calls[1][1]} == {"b"}


def test_bigquery_session_is_thread_safe_for_independent_turns():
    class Client:
        def __init__(self): self.calls = []
        def insert_rows_json(self, table, rows): self.calls.append((table, rows)); return []
    client = Client()
    sink = BigQuerySessionAuditSink("p", "d", client=client)

    def emit_turn(number: int) -> None:
        correlation = f"c-{number}"
        sink.emit(SessionAuditEvent(session_id="s", turn_no=number, correlation_id=correlation, event_type="turn.started"))
        sink.emit(SessionAuditEvent(session_id="s", turn_no=number, correlation_id=correlation, event_type="turn.completed"))

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(emit_turn, range(20)))

    assert len(client.calls) == 20
    assert all(len(rows) == 2 for _, rows in client.calls)


def test_bigquery_batch_failure_reports_all_buffered_events():
    class Client:
        def insert_rows_json(self, table, rows): return [{"reason": "unavailable"}]
    class Capture:
        def __init__(self): self.events = []
        def emit(self, event): self.events.append(event)
    app = AppLogRecorder(Capture())
    bound = SessionAuditRecorder(BigQuerySessionAuditSink("p", "d", client=Client()), app).bind("a", 1, "c")
    bound.record("turn.started")
    bound.record("intent.resolved", {"candidates": []})
    bound.record("turn.failed", {"error_type": "Example"})
    failure = app.sink.events[0]
    assert failure.event == "session_audit_sink_failed"
    assert failure.data["failed_event_type"] == "turn.failed"
    assert failure.data["failed_event_count"] == 3


def test_bigquery_exception_reports_all_buffered_events():
    class Client:
        def insert_rows_json(self, table, rows): raise ConnectionError("network unavailable")
    class Capture:
        def __init__(self): self.events = []
        def emit(self, event): self.events.append(event)
    app = AppLogRecorder(Capture())
    bound = SessionAuditRecorder(BigQuerySessionAuditSink("p", "d", client=Client()), app).bind("a", 1, "c")
    bound.record("turn.started")
    bound.record("intent.resolved", {"candidates": []})
    bound.record("turn.failed", {"error_type": "Example"})
    assert app.sink.events[0].data["failed_event_count"] == 3


def test_bigquery_app_sink_maps_rows_and_reports_insert_errors():
    class Client:
        def __init__(self, errors): self.errors, self.calls = errors, []
        def insert_rows_json(self, table, rows): self.calls.append((table, rows)); return self.errors
    client = Client([])
    sink = BigQueryAppLogSink("p", "d", client=client)
    sink.emit(AppLogEvent(level="INFO", service="adcm", environment="test", component="test", event="ok"))
    assert client.calls[0][0] == "p.d.app_logs"

    failing = AppLogRecorder(BigQueryAppLogSink("p", "d", client=Client([{"reason": "failed"}])))
    assert failing.info("still_best_effort").event == "still_best_effort"


def test_local_session_filename_is_safe_and_collision_resistant(tmp_path):
    sink = LocalSessionAuditSink(tmp_path)
    sink.emit(SessionAuditEvent(session_id="../a", turn_no=1, event_type="turn.started"))
    sink.emit(SessionAuditEvent(session_id="..\\a", turn_no=1, event_type="turn.started"))
    paths = list((tmp_path / "sessions").glob("*.jsonl"))
    assert len(paths) == 2
    assert all(path.parent == tmp_path / "sessions" for path in paths)


def test_audit_failure_escalates_to_application_log():
    class Bad:
        def emit(self, event): raise RuntimeError("down")
    class Capture:
        def __init__(self): self.events = []
        def emit(self, event): self.events.append(event)
    app = AppLogRecorder(Capture())
    audit = SessionAuditRecorder(Bad(), app).bind("a", 3, "corr")
    event = audit.record("intent.resolved", {"ok": True})
    assert event.event_type == "intent.resolved"
    assert app.sink.events[0].event == "session_audit_sink_failed"
    assert app.sink.events[0].data["failed_event_type"] == "intent.resolved"


def test_application_fallback_stderr_is_sanitized(capsys):
    class Bad:
        def emit(self, event):
            raise RuntimeError("credentials: {\"private_key\":\"raw-private-key\"}")
    AppLogRecorder(Bad()).info("test")
    stderr = capsys.readouterr().err
    assert "raw-private-key" not in stderr
    assert REDACTED in stderr
