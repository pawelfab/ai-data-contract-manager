"""Passthrough spies around the real outbound ports.

These wrap — never replace — `ForgeMcpAdapter` and `PydanticAiHeuristicsAdapter`, so the live
test still exercises the production adapters end to end. They exist only to make the internals
of one turn observable: which requirements Forge exposed in each stabilization round, and what
the LLM actually proposed before `ValueResolver` accepted or rejected it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from adcm.application.ports.forge import ForgeEvaluation
from adcm.application.ports.llm import QuestionRequest, ResolveRequest, ResolveResult
from adcm.domain.evidence.models import EvidenceItem
from adcm.domain.issues.models import AdvisoryIssue


@dataclass
class ForgeRound:
    """One `evaluate_contract` round trip over the real MCP transport."""

    document: dict[str, Any]
    evaluation: ForgeEvaluation
    duration_s: float

    @property
    def requirement_paths(self) -> list[str]:
        return [requirement.path for requirement in self.evaluation.requirements]

    @property
    def suggestion_pairs(self) -> list[tuple[str, Any]]:
        return [(item.path, item.value) for item in self.evaluation.suggestions]


@dataclass
class LlmCall:
    kind: str
    duration_s: float
    detail: str


class RecordingForge:
    """Records every Forge round while delegating to the real adapter."""

    def __init__(self, inner):
        self.inner = inner
        self.rounds: list[ForgeRound] = []

    async def evaluate(self, document: dict[str, Any], *, user_id: str | None = None) -> ForgeEvaluation:
        started = time.perf_counter()
        evaluation = await self.inner.evaluate(document, user_id=user_id)
        self.rounds.append(
            ForgeRound(
                document=document,
                evaluation=evaluation,
                duration_s=time.perf_counter() - started,
            )
        )
        return evaluation

    def take(self) -> list[ForgeRound]:
        """Return the rounds recorded since the last call and reset the buffer."""

        rounds, self.rounds = self.rounds, []
        return rounds


class RecordingHeuristics:
    """Records every LLM call while delegating to the real PydanticAI adapter."""

    def __init__(self, inner):
        self.inner = inner
        self.calls: list[LlmCall] = []

    async def resolve(self, request: ResolveRequest) -> ResolveResult:
        started = time.perf_counter()
        result = await self.inner.resolve(request)
        asked = ", ".join(r.path for r in request.requirements) or "-"
        proposed = ", ".join(f"{c.path}={c.value!r}" for c in result.candidates) or "-"
        self._record("resolve", started, f"asked[{asked}] proposed[{proposed}]")
        return result

    async def inspect_consistency(
        self, evidence: list[EvidenceItem], current_document: dict[str, Any]
    ) -> list[AdvisoryIssue]:
        started = time.perf_counter()
        issues = await self.inner.inspect_consistency(evidence, current_document)
        self._record("inspect_consistency", started, f"{len(issues)} issue(s)")
        return issues

    async def compose_question(self, request: QuestionRequest) -> str:
        started = time.perf_counter()
        question = await self.inner.compose_question(request)
        self._record("compose_question", started, f"{len(question)} chars")
        return question

    def _record(self, kind: str, started: float, detail: str) -> None:
        self.calls.append(LlmCall(kind=kind, duration_s=time.perf_counter() - started, detail=detail))

    def take(self) -> list[LlmCall]:
        calls, self.calls = self.calls, []
        return calls


@dataclass
class TurnRecord:
    """Everything observed for a single user message."""

    index: int
    user: str
    result: Any = None
    forge_rounds: list[ForgeRound] = field(default_factory=list)
    llm_calls: list[LlmCall] = field(default_factory=list)
    duration_s: float = 0.0
    hard_failures: list[str] = field(default_factory=list)
    soft_failures: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def final_requirement_paths(self) -> list[str]:
        """Requirements exposed by the last Forge round — these drive the next question."""

        return self.forge_rounds[-1].requirement_paths if self.forge_rounds else []
