from collections.abc import Callable
from uuid import uuid4

from adcm.domain.errors import SessionNotFoundError
from adcm.domain.session import SessionState
from adcm.ports.session_repository import SessionRepositoryPort


class SessionService:
    """Cykl życia sesji: utworzenie i odczyt istniejącej.

    Format identyfikatora należy do ADCM, nie do klienta — dlatego id powstaje tutaj,
    a nie jest przyjmowane z żądania. Odczyt jest jawnie odmienny od
    `SessionRepositoryPort.get_or_create`: brak sesji jest błędem, nie powodem do jej
    utworzenia.

    Przebieg tury pozostaje w `TurnOrchestrator`; ten serwis go nie dubluje.
    """

    def __init__(
        self,
        *,
        sessions: SessionRepositoryPort,
        id_factory: Callable[[], str] = lambda: uuid4().hex,
    ) -> None:
        self.sessions = sessions
        self.id_factory = id_factory

    async def create(self) -> SessionState:
        session = SessionState(session_id=self.id_factory())
        await self.sessions.save(session)
        return session

    async def get(self, session_id: str) -> SessionState:
        session = await self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session
