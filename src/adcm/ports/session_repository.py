from typing import Protocol
from uuid import UUID
from adcm.domain.models import ConversationState


class SessionRepositoryPort(Protocol):
    async def load(self, session_id: UUID) -> ConversationState | None: ...
    async def save(self, state: ConversationState) -> None: ...
