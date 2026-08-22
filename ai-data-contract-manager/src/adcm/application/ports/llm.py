from typing import Any, Protocol
from pydantic import BaseModel, Field
from adcm.application.ports.forge import Requirement
from adcm.domain.evidence.models import EvidenceItem, Message
from adcm.domain.issues.models import AdvisoryIssue


class Candidate(BaseModel):
    path: str
    value: Any
    confidence: float = 1.0
    evidence_id: str


class ResolveRequest(BaseModel):
    requirements: list[Requirement]
    evidence: list[EvidenceItem]
    history: list[Message]
    current_document: dict[str, Any]


class ResolveResult(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)
    warnings: list[AdvisoryIssue] = Field(default_factory=list)


class QuestionRequest(BaseModel):
    requirements: list[Requirement]
    warnings: list[AdvisoryIssue] = Field(default_factory=list)
    history: list[Message]
    current_document: dict[str, Any]


class QuestionResult(BaseModel):
    message: str


class HeuristicsPort(Protocol):
    async def resolve(self, request: ResolveRequest) -> ResolveResult: ...

    async def inspect_consistency(
        self, evidence: list[EvidenceItem], current_document: dict[str, Any]
    ) -> list[AdvisoryIssue]: ...

    async def compose_question(self, request: QuestionRequest) -> str: ...
