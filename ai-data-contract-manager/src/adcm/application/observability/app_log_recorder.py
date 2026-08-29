import logging
import sys
from typing import Any

from adcm.application.observability.models import AppLogEvent
from adcm.application.observability.sanitizer import sanitize
from adcm.ports.app_log_sink import AppLogSinkPort

_logger = logging.getLogger(__name__)


class AppLogRecorder:
    def __init__(self, sink: AppLogSinkPort, *, service: str = "adcm", environment: str = "local"):
        self.sink, self.service, self.environment = sink, service, environment

    def emit(self, level: str, event: str, *, component: str = "application", message: str | None = None,
             correlation_id: str | None = None, session_id: str | None = None, turn_no: int | None = None,
             duration_ms: float | None = None, data: dict[str, Any] | None = None) -> AppLogEvent:
        model = AppLogEvent(level=level.upper(), service=self.service, environment=self.environment,
                            component=component, event=event, message=message, correlation_id=correlation_id,
                            session_id=session_id, turn_no=turn_no, duration_ms=duration_ms, data=data or {})
        try:
            self.sink.emit(model)
        except Exception as exc:  # observability must never break business flow
            safe_error = sanitize(str(exc))
            _logger.error("application log sink failed: %s", safe_error)
            print(f"application log sink failed: {safe_error}", file=sys.stderr)
        return model

    def info(self, event: str, **kwargs: Any) -> AppLogEvent:
        return self.emit("INFO", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> AppLogEvent:
        return self.emit("ERROR", event, **kwargs)
