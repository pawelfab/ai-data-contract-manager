from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from adcm.domain.contract import ContractState
from adcm.domain.mutations import CandidateAction, MutationCandidate, MutationCommand, MutationOperation
from adcm.domain.provenance import ValueSource

from .json_pointer import exists


class CandidateDisposition(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class CandidateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: MutationCandidate
    disposition: CandidateDisposition
    reason: str
    command_id: str | None = None


class CandidatePolicyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commands: list[MutationCommand] = Field(default_factory=list)
    decisions: list[CandidateDecision] = Field(default_factory=list)


class CandidatePolicy:
    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold

    def decide(self, state: ContractState, candidates: list[MutationCandidate]) -> list[MutationCommand]:
        """Backward-compatible command-only view of :meth:`evaluate`."""
        return self.evaluate(state, candidates).commands

    def evaluate(self, state: ContractState, candidates: list[MutationCandidate]) -> CandidatePolicyResult:
        commands: list[MutationCommand] = []
        decisions: list[CandidateDecision] = []
        for candidate in candidates:
            if candidate.confidence < self.confidence_threshold:
                decisions.append(
                    CandidateDecision(
                        candidate=candidate,
                        disposition=CandidateDisposition.REJECTED,
                        reason=f"confidence below threshold {self.confidence_threshold:.2f}",
                    )
                )
                continue
            if candidate.action == CandidateAction.REMOVE:
                if exists(state.document, candidate.path):
                    command = MutationCommand(
                        operation=MutationOperation.REMOVE,
                        path=candidate.path,
                        source=ValueSource.USER_EXPLICIT,
                        producer_id=candidate.id,
                        reason="explicit user removal",
                    )
                    commands.append(command)
                    decisions.append(
                        CandidateDecision(
                            candidate=candidate,
                            disposition=CandidateDisposition.ACCEPTED,
                            reason="explicit user removal accepted",
                            command_id=command.id,
                        )
                    )
                else:
                    decisions.append(
                        CandidateDecision(
                            candidate=candidate,
                            disposition=CandidateDisposition.REJECTED,
                            reason="remove target does not exist",
                        )
                    )
                continue
            operation = MutationOperation.REPLACE if exists(state.document, candidate.path) else MutationOperation.ADD
            command = MutationCommand(
                operation=operation,
                path=candidate.path,
                value=candidate.value,
                source=ValueSource.USER_EXPLICIT,
                producer_id=candidate.id,
                reason="explicit user value",
            )
            commands.append(command)
            decisions.append(
                CandidateDecision(
                    candidate=candidate,
                    disposition=CandidateDisposition.ACCEPTED,
                    reason="explicit user value accepted",
                    command_id=command.id,
                )
            )
        return CandidatePolicyResult(commands=commands, decisions=decisions)
