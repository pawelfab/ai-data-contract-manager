from typing import Protocol
from pydantic import BaseModel, Field
from adcm.domain.evidence.models import EvidenceItem

class ContextRequest(BaseModel):
    query: str
    metadata: dict = Field(default_factory=dict)

class ContextProviderPort(Protocol):
    async def collect(self, request: ContextRequest) -> list[EvidenceItem]: ...
