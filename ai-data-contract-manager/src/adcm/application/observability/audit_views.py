"""Mapping core models to compact session audit payloads.

Session audit is a view over domain facts, not a copy of the domain models. Full
descriptors that repeat unchanged across fixed-point rounds (notably
``ForgeAnalysis.writable``) are reduced to counters here, and details that already
own a dedicated event (``forge.proposal.received``, ``rule.proposal.generated``,
``proposal.decision``) are not restated.
"""

from typing import Any

from adcm.domain.forge import ForgeAnalysis, MissingRequirement
from adcm.domain.turn import TurnOutcome

AUDIT_LEVEL_NORMAL = "normal"
AUDIT_LEVEL_DEBUG = "debug"
AUDIT_LEVELS = (AUDIT_LEVEL_NORMAL, AUDIT_LEVEL_DEBUG)


def forge_analysis_completed_view(
    analysis: ForgeAnalysis,
    *,
    round_no: int,
    contract_revision: int,
    duration_ms: float,
    phase: str | None = None,
    level: str = AUDIT_LEVEL_NORMAL,
) -> dict[str, Any]:
    """Payload for ``forge.analysis.completed``.

    Normal level keeps the round context, the status and counters; ``writable`` and
    ``proposals`` are omitted because they either repeat unchanged every round or are
    already emitted as individual proposal events. Debug level keeps the whole
    analysis.
    """
    data: dict[str, Any] = {
        "round": round_no,
        "contract_revision": contract_revision,
    }
    if phase is not None:
        data["phase"] = phase

    if level == AUDIT_LEVEL_DEBUG:
        data = {**analysis.model_dump(mode="json"), **data}
    else:
        data.update(
            {
                "definition_version": analysis.definition_version,
                "status": analysis.status.model_dump(mode="json"),
                "writable_count": len(analysis.writable),
                "missing": [item.path for item in analysis.missing],
                "foreign_count": len(analysis.foreign),
                "proposal_count": len(analysis.proposals),
                "diagnostic_count": len(analysis.diagnostics),
            }
        )
        # Empty diagnostics are already covered by diagnostic_count.
        if analysis.diagnostics:
            data["diagnostics"] = [item.model_dump(mode="json") for item in analysis.diagnostics]

    data["duration_ms"] = duration_ms
    return data


def turn_completed_view(
    outcome: TurnOutcome,
    *,
    contract_revision: int,
    level: str = AUDIT_LEVEL_NORMAL,
) -> dict[str, Any]:
    """Payload for ``turn.completed``: the final snapshot of the turn.

    The full document, forge status, missing requirements, diagnostics, external
    checks and response are kept — they occur once per turn and allow reading the
    final state without replaying the event stream. The stabilization report is
    reduced to its outcome, because every proposal decision already has its own
    ``proposal.decision`` event.
    """
    return {
        "contract_revision": contract_revision,
        "final_document": outcome.document,
        "forge_status": outcome.forge.status.model_dump(mode="json"),
        "missing": [_missing_view(item, level) for item in outcome.forge.missing],
        "diagnostics": [item.model_dump(mode="json") for item in outcome.forge.diagnostics],
        "external_checks": outcome.external_checks.model_dump(mode="json"),
        "stabilization": {
            "rounds": outcome.stabilization.rounds,
            "converged": outcome.stabilization.converged,
        },
        "response": outcome.message,
    }


def _missing_view(item: MissingRequirement, level: str) -> dict[str, Any]:
    if level == AUDIT_LEVEL_DEBUG:
        return item.model_dump(mode="json")
    # `message` is derivable from path and code, `allowed_values` is usually null.
    view: dict[str, Any] = {
        "path": item.path,
        "code": item.code,
        "expected_type": item.expected_type,
    }
    if item.allowed_values:
        view["allowed_values"] = item.allowed_values
    return view
