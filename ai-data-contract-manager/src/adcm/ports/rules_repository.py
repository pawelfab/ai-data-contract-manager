from typing import Protocol

from adcm.domain.rules import RulesDocument


class RulesRepositoryPort(Protocol):
    async def load(self, session_id: str | None = None) -> RulesDocument: ...
