from typing import Protocol
from adcm.domain.models import AuditEvent


class AuditSinkPort(Protocol):
    async def append(self, event: AuditEvent) -> None: ...
