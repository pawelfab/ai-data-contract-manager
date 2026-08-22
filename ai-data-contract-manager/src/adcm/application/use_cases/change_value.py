from typing import Any
from adcm.application.ports.session_repository import SessionRepositoryPort
from adcm.application.use_cases.stabilize_contract import StabilizeContract

class ChangeValue:
    def __init__(self, repo: SessionRepositoryPort, stabilizer: StabilizeContract): self.repo=repo; self.stabilizer=stabilizer
    async def execute(self, session_id: str, path: str, value: Any):
        session=await self.repo.get(session_id)
        if not session: raise KeyError(session_id)
        session.contract.set_user(path,value)
        session.contract.clear_derived()
        result=await self.stabilizer.execute(session)
        await self.repo.save(session)
        return result
