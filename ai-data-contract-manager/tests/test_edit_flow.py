"""Editing a finished contract.

`complete` describes the contract, not the session: the user can keep talking and change
any field. ADCM never learns the contract structure — Forge tells it what is editable.
"""

from copy import deepcopy

import pytest

from adcm.models import ResolvableField
from adcm.orchestrator import ADCMOrchestrator
from adcm.semantic import CandidateValue, ExtractionResult, SemanticResolver
from support import FakeForgeGateway


class RecordingSemanticResolver(SemanticResolver):
    """Records every call; answers only edit-mode ones, so the stair-step phase
    cannot consume the scripted result."""

    def __init__(self, edit_result: ExtractionResult | None = None):
        self.edit_result = edit_result
        self.calls: list[dict] = []

    async def extract_from_history(self, session_id, messages, targets, user_facts):
        modes = {target.mode for target in targets}
        self.calls.append({"targets": [target.path for target in targets], "modes": modes})
        if modes == {"edit"} and self.edit_result is not None:
            return self.edit_result
        return ExtractionResult()


async def complete_contract(semantic=None) -> tuple[ADCMOrchestrator, str]:
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()
    for answer in (
        "roket",
        "customer_accounts_daily",
        "data-platform@example.com",
        "gs://raw-zone/accounts/accounts.dat",
        "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
    ):
        turn = await service.message(turn.session_id, answer)
    assert turn.status == "complete", turn.message
    return service, turn.session_id


@pytest.mark.asyncio
async def test_the_session_does_not_end_when_the_contract_is_complete():
    service, session_id = await complete_contract()

    turn = await service.message(session_id, "gs://raw-zone/accounts/inny.dat")

    assert turn.status == "complete"
    assert turn.contract["source"]["uri"] == "gs://raw-zone/accounts/inny.dat"
    assert "zmienić dowolne pole" in turn.message


@pytest.mark.asyncio
async def test_a_user_origin_field_that_is_not_overridable_can_still_be_changed():
    """`overridable` hides user-supplied explicit fields; `editable` does not."""
    service, session_id = await complete_contract()
    state = await service.state(session_id)
    assert "metadata.owner" not in {field.path for field in state.overridable}

    turn = await service.message(session_id, "właściciel: finops@example.com")

    assert turn.contract["metadata"]["owner"] == "finops@example.com"
    assert turn.status == "complete"


@pytest.mark.asyncio
async def test_deterministic_edit_does_not_spend_an_llm_call():
    semantic = RecordingSemanticResolver()
    service, session_id = await complete_contract(semantic)
    before = len(semantic.calls)

    await service.message(session_id, "gs://raw-zone/accounts/inny.dat")

    assert len(semantic.calls) == before


@pytest.mark.asyncio
async def test_the_llm_is_the_fallback_and_sees_editable_targets():
    semantic = RecordingSemanticResolver(
        ExtractionResult(
            values=[
                CandidateValue(
                    path="metadata.owner",
                    value="finops",
                    confidence=0.95,
                    evidence="opiekę przejmuje inny zespół",
                )
            ]
        )
    )
    service, session_id = await complete_contract(semantic)
    before = len(semantic.calls)

    turn = await service.message(session_id, "opiekę przejmuje inny zespół")

    assert len(semantic.calls) == before + 1
    assert semantic.calls[-1]["modes"] == {"edit"}
    assert "metadata.owner" in semantic.calls[-1]["targets"]
    assert turn.contract["metadata"]["owner"] == "finops"


@pytest.mark.asyncio
async def test_adding_a_column_replaces_the_whole_array():
    service, session_id = await complete_contract()
    state = await service.state(session_id)
    before = deepcopy(state.contract["source"]["columns"])
    assert [column["name"] for column in before] == ["account_id", "balance"]

    turn = await service.message(session_id, "created_at 20 30 TIMESTAMP")

    columns = turn.contract["source"]["columns"]
    assert [column["name"] for column in columns] == ["account_id", "balance", "created_at"]
    # Existing records survive: the array is replaced as a whole, not patched per index.
    assert columns[:2] == before


@pytest.mark.asyncio
async def test_asking_for_a_value_the_contract_already_has_is_not_a_failure():
    service, session_id = await complete_contract()

    turn = await service.message(session_id, "gs://raw-zone/accounts/accounts.dat")

    assert turn.status == "complete"
    assert turn.candidate_issues == []
    assert "no_progress" not in turn.message


@pytest.mark.asyncio
async def test_an_unrecognized_message_leaves_the_contract_untouched():
    service, session_id = await complete_contract()
    before = deepcopy((await service.state(session_id)).contract)

    turn = await service.message(session_id, "dzięki, wygląda dobrze")

    assert turn.contract == before
    assert turn.status == "complete"


def test_resolvable_field_carries_provenance_from_both_sources():
    from adcm.models import EditableField, Origin, Requirement

    from_requirement = ResolvableField.from_requirement(
        Requirement(path="metadata.owner", question="Kto?", input_mode="semantic"),
        "missing",
    )
    from_editable = ResolvableField.from_editable(
        EditableField(
            path="orchestration.schedule",
            current_value="0 0 * * *",
            current_origin=Origin.SYSTEM_ENRICHMENT,
        )
    )

    assert from_requirement.mode == "missing"
    assert from_requirement.question == "Kto?"
    assert from_editable.mode == "edit"
    assert from_editable.current_value == "0 0 * * *"
    assert from_editable.current_origin == Origin.SYSTEM_ENRICHMENT
