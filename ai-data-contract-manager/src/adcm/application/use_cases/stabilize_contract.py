from pydantic import BaseModel, Field

from adcm.application.ports.forge import ContractForgePort, ForgeEvaluation
from adcm.application.ports.llm import HeuristicsPort, ResolveRequest
from adcm.application.services.value_resolver import ValueResolver
from adcm.domain.issues.models import AdvisoryIssue
from adcm.domain.session.models import Session


class StabilizationResult(BaseModel):
    evaluation: ForgeEvaluation
    warnings: list[AdvisoryIssue] = Field(default_factory=list)
    rounds: int


class StabilizeContract:
    """Mandatory deterministic Forge loop; LLM only proposes evidence-backed candidates."""

    def __init__(self, forge: ContractForgePort, heuristics: HeuristicsPort, max_rounds: int = 20):
        self.forge = forge
        self.heuristics = heuristics
        self.max_rounds = max_rounds
        self.values = ValueResolver()

    async def execute(
        self,
        session: Session,
        *,
        focus_evidence_ids: set[str] | None = None,
    ) -> StabilizationResult:
        evaluation = ForgeEvaluation()

        for round_no in range(1, self.max_rounds + 1):
            round_warnings: list[AdvisoryIssue] = []
            document = session.contract.effective_document()
            evaluation = await self.forge.evaluate(document, user_id=session.user_id)

            changed = self.values.apply_suggestions(session.contract, evaluation.suggestions)
            current = session.contract.effective_document()
            unresolved = [r for r in evaluation.requirements if _missing(current, r.path)]

            # First round also interprets explicit edits to already-filled fields. Later rounds
            # resolve only newly exposed missing requirements.
            if unresolved or round_no == 1:
                resolution_evidence = session.evidence
                if round_no == 1 and focus_evidence_ids is not None:
                    resolution_evidence = [
                        item for item in session.evidence if item.id in focus_evidence_ids
                    ]
                resolved = await self.heuristics.resolve(
                    ResolveRequest(
                        requirements=unresolved,
                        evidence=resolution_evidence,
                        history=session.messages,
                        current_document=current,
                    )
                )
                round_warnings.extend(resolved.warnings)
                outcome = self.values.apply_candidates(
                    session.contract,
                    resolved.candidates,
                    session.evidence,
                    unresolved,
                )
                changed |= outcome.changed

            if not changed:
                round_warnings.extend(
                    await self.heuristics.inspect_consistency(
                        session.evidence,
                        session.contract.effective_document(),
                    )
                )
                return StabilizationResult(
                    evaluation=evaluation,
                    warnings=_unique(round_warnings),
                    rounds=round_no,
                )

        raise RuntimeError("stabilization did not converge")


def _missing(document: dict, pointer: str) -> bool:
    from adcm.domain.contract.path import get_pointer

    return get_pointer(document, pointer, None) is None


def _unique(items: list[AdvisoryIssue]) -> list[AdvisoryIssue]:
    seen = set()
    out = []
    for item in items:
        key = (item.message, tuple(item.paths), item.requires_user_decision)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
