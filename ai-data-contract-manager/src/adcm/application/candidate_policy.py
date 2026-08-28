from adcm.domain.contract import ContractState
from adcm.domain.mutations import CandidateAction, MutationCandidate, MutationCommand, MutationOperation
from adcm.domain.provenance import ValueSource

from .json_pointer import exists


class CandidatePolicy:
    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold

    def decide(self, state: ContractState, candidates: list[MutationCandidate]) -> list[MutationCommand]:
        commands: list[MutationCommand] = []
        for candidate in candidates:
            if candidate.confidence < self.confidence_threshold:
                continue
            if candidate.action == CandidateAction.REMOVE:
                if exists(state.document, candidate.path):
                    commands.append(
                        MutationCommand(
                            operation=MutationOperation.REMOVE,
                            path=candidate.path,
                            source=ValueSource.USER_EXPLICIT,
                            producer_id=candidate.id,
                            reason="explicit user removal",
                        )
                    )
                continue
            operation = MutationOperation.REPLACE if exists(state.document, candidate.path) else MutationOperation.ADD
            commands.append(
                MutationCommand(
                    operation=operation,
                    path=candidate.path,
                    value=candidate.value,
                    source=ValueSource.USER_EXPLICIT,
                    producer_id=candidate.id,
                    reason="explicit user value",
                )
            )
        return commands
