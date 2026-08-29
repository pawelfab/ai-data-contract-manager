from typing import Protocol

from contract_forge.application.observability.models import AppLogEvent


class AppLogSinkPort(Protocol):
    def emit(self, event: AppLogEvent) -> None: ...
