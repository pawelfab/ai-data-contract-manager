from enum import StrEnum

from pydantic import BaseModel, Field

from adcm.application.ports.llm import Candidate


class CandidateDecisionStatus(StrEnum):
    ACCEPTED = "accepted"
    SHADOWED = "shadowed"
    REJECTED = "rejected"
    NEEDS_USER_DECISION = "needs_user_decision"


class CandidateDecision(BaseModel):
    candidate: Candidate
    status: CandidateDecisionStatus
    reason: str | None = None


class CandidateOutcome(BaseModel):
    decisions: list[CandidateDecision] = Field(default_factory=list)
    changed: bool = False
