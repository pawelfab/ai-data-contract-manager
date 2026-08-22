from adcm.domain.session.models import Session

class MemorySessionRepository:
    def __init__(self): self._items: dict[str,Session]={}
    async def create(self, session: Session) -> Session: self._items[session.id]=session; return session
    async def get(self, session_id: str) -> Session|None: return self._items.get(session_id)
    async def save(self, session: Session) -> None: self._items[session.id]=session
