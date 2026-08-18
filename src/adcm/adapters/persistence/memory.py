from copy import deepcopy
from uuid import UUID
from adcm.domain.models import ConversationState


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, ConversationState] = {}

    async def load(self, session_id: UUID) -> ConversationState | None:
        item = self._items.get(session_id)
        return deepcopy(item) if item else None

    async def save(self, state: ConversationState) -> None:
        self._items[state.session_id] = deepcopy(state)
