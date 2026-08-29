from typing import Protocol

from adcm.application.observability.models import SessionAuditEvent


class SessionAuditSinkPort(Protocol):
    def emit(self, event: SessionAuditEvent) -> None: ...

