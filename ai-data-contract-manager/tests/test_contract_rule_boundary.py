"""ADCM side of the Contract Forge business-rule wire contract.

ADCM mirrors Forge's DTOs structurally but never imports them, so these tests validate
raw MCP-shaped payloads instead of building Forge objects.
"""

from adcm.models import ConversationMemory, ForgeState, Requirement
from adcm.orchestrator import ADCMOrchestrator


def memory_for(state: ForgeState) -> ConversationMemory:
    return ConversationMemory(session_id="adcm-1", forge_session_id=state.session_id)


def turn_for(state: ForgeState):
    return ADCMOrchestrator._turn_from_state("adcm-1", state, memory_for(state))


def test_a_new_forge_reason_does_not_break_the_transport_boundary():
    """``reason`` is an open string; a new discovery reason must not fail validation."""
    state = ForgeState.model_validate(
        {
            "session_id": "forge-1",
            "status": "needs_input",
            "pending": [
                {
                    "path": "preparator.operations.unpack.format",
                    "question": "Jaki jest format archiwum?",
                    "status": "missing",
                    "reason": "contract_rule",
                    "rule_id": "preparator.unpack.format_required_when_enabled",
                    "message": "format is required when unpack.enabled is true.",
                    "value_schema": {"type": "string", "enum": ["zip", "gzip"]},
                    "allowed_values": ["zip", "gzip"],
                }
            ],
        }
    )

    requirement = state.pending[0]
    assert requirement.reason == "contract_rule"
    assert requirement.rule_id == "preparator.unpack.format_required_when_enabled"
    assert requirement.status == "missing"

    turn = turn_for(state)
    assert turn.pending_path == "preparator.operations.unpack.format"
    assert turn.message.startswith("Jaki jest format archiwum?")


def test_a_blocking_business_rule_is_explained_even_without_schema_errors():
    state = ForgeState.model_validate(
        {
            "session_id": "forge-1",
            "status": "invalid",
            "validation_errors": [],
            "contract_rule_issues": [
                {
                    "rule_id": "preparator.enabled_requires_operation",
                    "status": "invalid",
                    "path": "preparator.operations",
                    "message": "When preparator.enabled is true, at least one operation must be enabled.",
                },
                {
                    "rule_id": "record_validation.macro.registered",
                    "status": "skipped_non_executable",
                    "path": "macro",
                    "message": "macro must exist in VALIDATION_REGISTRY.",
                },
            ],
        }
    )

    turn = turn_for(state)

    assert turn.status == "invalid"
    assert "preparator.operations: When preparator.enabled is true" in turn.message
    # A rule Forge could not execute is reported but never presented as a failure.
    assert "VALIDATION_REGISTRY" not in turn.message
    assert len(turn.contract_rule_issues) == 2


def test_invalid_and_forbidden_requirements_ask_for_a_correction():
    invalid = Requirement(
        path="source.columns.0.end",
        status="invalid",
        reason="contract_rule",
        question="Podaj koniec zakresu.",
    )
    forbidden = Requirement(
        path="converter.fixedWidth",
        status="forbidden",
        reason="contract_rule",
        message="fixed_width is only allowed for a fixed_width source.",
    )

    assert ADCMOrchestrator._requirement_question(invalid).startswith(
        "Wartość dla source.columns.0.end jest niepoprawna."
    )
    forbidden_question = ADCMOrchestrator._requirement_question(forbidden)
    assert "nie jest dozwolona" in forbidden_question
    # With no question, the rule message carries the explanation.
    assert "fixed_width is only allowed" in forbidden_question


def test_only_missing_requirements_are_resolved_automatically():
    state = ForgeState.model_validate(
        {
            "session_id": "forge-1",
            "status": "needs_input",
            "pending": [
                {"path": "metadata.owner", "question": "Kto jest właścicielem?", "status": "missing"},
                {"path": "source.columns.0.end", "question": "Popraw koniec.", "status": "invalid"},
            ],
        }
    )

    assert [field.path for field in ADCMOrchestrator._resolvable_fields(state)] == ["metadata.owner"]


def test_contract_rule_issues_count_as_progress():
    """Otherwise a turn that only resolved a rule would read as 'no progress'."""
    base = {"session_id": "forge-1", "status": "needs_input", "contract": {"a": 1}}
    before = ForgeState.model_validate(
        {
            **base,
            "contract_rule_issues": [
                {
                    "rule_id": "preparator.enabled_requires_operation",
                    "status": "invalid",
                    "message": "...",
                }
            ],
        }
    )
    after = ForgeState.model_validate(base)

    assert ADCMOrchestrator._state_signature(before) != ADCMOrchestrator._state_signature(after)
