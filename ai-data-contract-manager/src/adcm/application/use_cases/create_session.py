from adcm.application.ports.session_repository import SessionRepositoryPort
from adcm.domain.session.models import Session


class CreateSession:
    def __init__(self, repo: SessionRepositoryPort):
        self.repo = repo

    async def execute(self, user_id: str | None = None) -> Session:
        return await self.repo.create(Session(user_id=user_id))
