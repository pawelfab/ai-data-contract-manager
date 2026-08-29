from typing import Protocol

from adcm.application.observability.models import AppLogEvent


class AppLogSinkPort(Protocol):
    def emit(self, event: AppLogEvent) -> None: ...

