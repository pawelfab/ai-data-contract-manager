import logging
import sys
from typing import Any

from contract_forge.ports.app_log_sink import AppLogSinkPort

from .models import AppLogEvent
from .sanitizer import sanitize

_fallback_logger = logging.getLogger("contract_forge.observability")


class AppLogRecorder:
    """Best-effort application logger; observability never breaks Forge."""

    def __init__(self, sink: AppLogSinkPort | None = None, *, service: str = "contract_forge",
                 environment: str = "local") -> None:
        self.sink, self.service, self.environment = sink, service, environment

    def emit(self, level: str, event: str, *, component: str = "application", message: str | None = None,
             correlation_id: str | None = None, duration_ms: float | None = None,
             data: dict[str, Any] | None = None) -> AppLogEvent:
        model = AppLogEvent(event=event, level=level.upper(), service=self.service,
                            environment=self.environment, component=component, message=message,
                            correlation_id=correlation_id, duration_ms=duration_ms,
                            data=data or {})
        if self.sink is None:
            return model
        try:
            self.sink.emit(model)
        except Exception as exc:  # logging must not affect the business path
            text = f"application log sink failed: {sanitize(str(exc))}"
            try:
                _fallback_logger.error(text)
            except Exception:
                pass
            print(text, file=sys.stderr)
        return model

    def info(self, event: str, **kwargs: Any) -> AppLogEvent:
        return self.emit("INFO", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> AppLogEvent:
        return self.emit("ERROR", event, **kwargs)
