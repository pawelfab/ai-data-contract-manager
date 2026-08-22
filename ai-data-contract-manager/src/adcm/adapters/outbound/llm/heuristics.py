"""Deterministic local fallback for development/tests.

Production wiring uses PydanticAiHeuristicsAdapter. This adapter intentionally understands only
explicit JSON-Pointer assignments and never pretends to perform semantic reasoning.
"""
import re
from adcm.application.ports.llm import (
    Candidate,
    HeuristicsPort,
    QuestionRequest,
    ResolveRequest,
    ResolveResult,
)


class ConservativeLocalHeuristics(HeuristicsPort):
    async def resolve(self, request: ResolveRequest) -> ResolveResult:
        candidates: list[Candidate] = []
        wanted = {r.path for r in request.requirements}
        for ev in request.evidence:
            for path in wanted:
                match = re.search(re.escape(path) + r"\s*=\s*([^\n;]+)", ev.content)
                if match:
                    candidates.append(
                        Candidate(
                            path=path,
                            value=match.group(1).strip(),
                            confidence=1.0,
                            evidence_id=ev.id,
                        )
                    )
        return ResolveResult(candidates=candidates)

    async def inspect_consistency(self, evidence, current_document):
        return []

    async def compose_question(self, request: QuestionRequest) -> str:
        labels = [r.title or r.path for r in request.requirements]
        decisions = [w.message for w in request.warnings if w.requires_user_decision]
        parts: list[str] = []
        if labels:
            parts.append("Potrzebuję jeszcze: " + ", ".join(labels))
        if decisions:
            parts.append("Do decyzji: " + " ".join(decisions))
        return " ".join(parts) or "Kontrakt nie wymaga dodatkowych informacji."
