import asyncio
from copy import deepcopy

from adcm.domain.session import SessionState


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str) -> SessionState:
        async with self._lock:
            if session_id not in self._items:
                self._items[session_id] = SessionState(session_id=session_id)
            return deepcopy(self._items[session_id])

    async def save(self, session: SessionState) -> None:
        async with self._lock:
            self._items[session.session_id] = deepcopy(session)
