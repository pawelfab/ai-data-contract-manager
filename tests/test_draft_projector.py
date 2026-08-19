from uuid import uuid4

import pytest
from pydantic import ValidationError

from adcm.application.draft_projector import DraftProjector
from adcm.domain.models import (
    AllowedPath,
    ContractDraft,
    ConversationState,
    CurrentSchemaView,
    EvaluationStatus,
    FinalValidationStatus,
    RenderMode,
    ResolvedValue,
    ValidationFindingStatus,
    ValueCandidate,
    ValueOrigin,
    WorkflowOutcomeStatus,
)


def rv(path, value):
    return ResolvedValue(
        path=path,
        value=value,
        selected_candidate_id=uuid4(),
        origin=ValueOrigin.USER_EXPLICIT,
    )


def test_projection_rejects_unauthorized_paths_and_builds_nested_document():
    resolved = {
        "source.system": rv("source.system", "SAP"),
        "llm.invented.path": rv("llm.invented.path", "bad"),
    }
    view = CurrentSchemaView(
        schema_revision="v1",
        allowed_paths=[AllowedPath(path="source.system")],
    )
    draft = DraftProjector().project(resolved, view, revision=1)
    assert draft.values == {"source": {"system": "SAP"}}


def test_reprojection_removes_paths_no_longer_legal():
    resolved = {
        "source.format": rv("source.format", "parquet"),
        "source.delimited.delimiter": rv("source.delimited.delimiter", ";"),
    }
    parquet_view = CurrentSchemaView(
        schema_revision="v2",
        allowed_paths=[AllowedPath(path="source.format")],
    )
    draft = DraftProjector().project(resolved, parquet_view, revision=2)
    assert draft.values == {"source": {"format": "parquet"}}


def test_projection_authorizes_concrete_array_indices_against_schema_wildcards():
    path = "silver.tables[0].columns[2].name"
    view = CurrentSchemaView(
        schema_revision="v1",
        allowed_paths=[AllowedPath(path="silver.tables[*].columns[*].name")],
    )

    draft = DraftProjector().project({path: rv(path, "amount")}, view, revision=1)

    assert draft.values == {
        "silver": {
            "tables": [
                {
                    "columns": [
                        {},
                        {},
                        {"name": "amount"},
                    ]
                }
            ]
        }
    }


def test_projection_omits_schema_wildcards_and_malformed_instance_paths():
    wildcard_path = "tables[*].name"
    malformed_index_path = "tables[00].name"
    view = CurrentSchemaView(
        schema_revision="v1",
        allowed_paths=[AllowedPath(path=wildcard_path)],
    )

    draft = DraftProjector().project(
        {
            wildcard_path: rv(wildcard_path, "bad"),
            malformed_index_path: rv(malformed_index_path, "bad"),
        },
        view,
        revision=1,
    )

    assert not view.is_path_allowed(wildcard_path)
    assert not view.is_path_allowed(malformed_index_path)
    assert draft.values == {}


def test_root_array_instance_path_is_not_authorized_for_dict_backed_drafts():
    root_array_path = "[0].name"
    view = CurrentSchemaView(
        schema_revision="v1",
        allowed_paths=[AllowedPath(path="[*].name")],
    )

    draft = DraftProjector().project(
        {root_array_path: rv(root_array_path, "bad")},
        view,
        revision=1,
    )

    assert not view.is_path_allowed(root_array_path)
    assert draft.values == {}


def test_canonical_hash_depends_only_on_canonical_nested_content():
    first = ContractDraft(values={"source": {"format": "parquet", "system": "SAP"}}, revision=1)
    second = ContractDraft(values={"source": {"system": "SAP", "format": "parquet"}}, revision=99)

    assert first.canonical_hash() == second.canonical_hash()


def test_conversation_state_rejects_resolution_without_selected_candidate():
    resolution = rv("source.system", "SAP")

    with pytest.raises(ValidationError, match="unknown selected candidate"):
        ConversationState(resolved_values={"source.system": resolution})


def test_conversation_state_accepts_resolution_linked_to_candidate_at_the_same_path():
    candidate = ValueCandidate(
        path="source.system",
        value="SAP",
        origin=ValueOrigin.MCP_DEFAULT,
        status="selected",
    )
    resolution = ResolvedValue(
        path="source.system",
        value="SAP",
        selected_candidate_id=candidate.id,
        origin=candidate.origin,
    )

    state = ConversationState(
        value_candidates=[candidate],
        resolved_values={"source.system": resolution},
    )

    assert state.resolved_values["source.system"].selected_candidate_id == candidate.id


def test_conversation_state_rejects_inconsistent_selected_candidate_provenance():
    evidence_ids = [uuid4()]
    candidate = ValueCandidate(
        path="source.system",
        value="SAP",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=evidence_ids,
        status="selected",
    )
    resolution = ResolvedValue(
        path="source.system",
        value="SAP",
        selected_candidate_id=candidate.id,
        origin=candidate.origin,
        evidence_ids=evidence_ids,
    )
    invalid_states = [
        (candidate, resolution.model_copy(update={"value": "Oracle"})),
        (candidate, resolution.model_copy(update={"origin": ValueOrigin.MCP_DEFAULT})),
        (candidate, resolution.model_copy(update={"evidence_ids": [uuid4()]})),
        (candidate.model_copy(update={"status": "candidate"}), resolution),
    ]

    for selected_candidate, invalid_resolution in invalid_states:
        with pytest.raises(ValidationError):
            ConversationState(
                value_candidates=[selected_candidate],
                resolved_values={"source.system": invalid_resolution},
            )


@pytest.mark.parametrize(
    ("candidate_value", "resolved_value"),
    [(1, True), (True, 1), (0, False), (False, 0), (1, 1.0)],
)
def test_conversation_state_compares_resolved_values_as_canonical_json(
    candidate_value,
    resolved_value,
):
    candidate = ValueCandidate(
        path="value",
        value=candidate_value,
        origin=ValueOrigin.MCP_DEFAULT,
        status="selected",
    )
    resolution = ResolvedValue(
        path="value",
        value=resolved_value,
        selected_candidate_id=candidate.id,
        origin=candidate.origin,
    )

    with pytest.raises(ValidationError, match="canonically match"):
        ConversationState(
            value_candidates=[candidate],
            resolved_values={"value": resolution},
        )


def test_conversation_state_accepts_canonically_equal_nested_values():
    candidate = ValueCandidate(
        path="value",
        value={"b": [2, 3], "a": 1},
        origin=ValueOrigin.MCP_DEFAULT,
        status="selected",
    )
    resolution = ResolvedValue(
        path="value",
        value={"a": 1, "b": [2, 3]},
        selected_candidate_id=candidate.id,
        origin=candidate.origin,
    )

    state = ConversationState(
        value_candidates=[candidate],
        resolved_values={"value": resolution},
    )

    assert state.resolved_values["value"].value == {"a": 1, "b": [2, 3]}


def test_conversation_state_rejects_duplicate_candidate_ids():
    duplicate_id = uuid4()
    candidates = [
        ValueCandidate(
            id=duplicate_id,
            path="source.system",
            value="SAP",
            origin=ValueOrigin.MCP_DEFAULT,
            status="selected",
        ),
        ValueCandidate(
            id=duplicate_id,
            path="source.system",
            value="Oracle",
            origin=ValueOrigin.MCP_ENRICHMENT,
            status="selected",
        ),
    ]

    with pytest.raises(ValidationError, match="candidate IDs must be unique"):
        ConversationState(value_candidates=candidates)


def test_conversation_state_rejects_multiple_selected_candidates_for_one_path():
    candidates = [
        ValueCandidate(
            path="source.system",
            value="SAP",
            origin=ValueOrigin.MCP_DEFAULT,
            status="selected",
        ),
        ValueCandidate(
            path="source.system",
            value="Oracle",
            origin=ValueOrigin.MCP_ENRICHMENT,
            status="selected",
        ),
    ]

    with pytest.raises(ValidationError, match="Only one selected candidate"):
        ConversationState(value_candidates=candidates)


def test_status_enums_expose_only_canonical_vocabulary():
    assert set(EvaluationStatus) == {
        EvaluationStatus.INCOMPLETE,
        EvaluationStatus.COMPLETE,
        EvaluationStatus.INVALID,
    }
    assert set(ValidationFindingStatus) == {
        ValidationFindingStatus.VALID,
        ValidationFindingStatus.INVALID,
        ValidationFindingStatus.DEFERRED,
    }
    assert set(FinalValidationStatus) == {
        FinalValidationStatus.VALID,
        FinalValidationStatus.INVALID,
        FinalValidationStatus.DEFERRED_EXTERNAL,
    }
    assert set(WorkflowOutcomeStatus) == {
        WorkflowOutcomeStatus.WAITING_FOR_USER,
        WorkflowOutcomeStatus.BLOCKED_EXTERNAL,
        WorkflowOutcomeStatus.COMPLETE,
        WorkflowOutcomeStatus.INVALID,
        WorkflowOutcomeStatus.FAILED,
    }
    assert set(RenderMode) == {RenderMode.DRAFT, RenderMode.FINAL}
