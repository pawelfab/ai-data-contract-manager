from typing import Protocol
from pydantic import BaseModel, Field
from adcm.domain.contract.value import Authority
from adcm.domain.evidence.models import EvidenceItem, Message


class ContextCollectionRequest(BaseModel):
    user_request: str
    history: list[Message] = Field(default_factory=list)
    current_document: dict = Field(default_factory=dict)
    authority: Authority = Authority.USER_REFERENCED
    allowed_sources: list[str] = Field(default_factory=list)


class ContextCollectionResult(BaseModel):
    evidence: list[EvidenceItem] = Field(default_factory=list)
    user_visible_output: str | None = None


class AgentContextPort(Protocol):
    """Optional agent-selected context/tool boundary.

    Future Atlassian, repository, schema-explorer and visualizer MCPs can live behind this
    port. Contract Forge deliberately does not.
    """

    async def collect(self, request: ContextCollectionRequest) -> ContextCollectionResult: ...
