from uuid import uuid4

import pytest
from pydantic import ValidationError

from adcm.application.preference_expander import PreferenceExpander
from adcm.application.signal_binder import SignalBinder
from adcm.domain.models import AllowedPath, Preference, Signal, ValueCandidate, ValueOrigin


def test_pre_path_signal_waits_until_concept_is_legal_and_propagates_evidence():
    evidence_id = uuid4()
    signal = Signal(
        concept="field_delimiter",
        value=";",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[evidence_id],
    )
    binder = SignalBinder()
    assert binder.bind(
        [signal], [AllowedPath(path="source.system", concepts=["source_system"])]
    ) == []
    assert signal.status == "unbound"

    candidates = binder.bind(
        [signal],
        [AllowedPath(path="source.delimited.delimiter", concepts=["field_delimiter"])],
    )
    assert len(candidates) == 1
    assert candidates[0].path == "source.delimited.delimiter"
    assert candidates[0].evidence_ids == [evidence_id]
    assert candidates[0].source_signal_id == signal.id


def test_user_explicit_signal_without_evidence_is_invalid_state():
    with pytest.raises(ValidationError):
        Signal(concept="field_delimiter", value=";", origin=ValueOrigin.USER_EXPLICIT)


def test_ambiguous_signal_remains_unbound_and_does_not_create_candidate():
    signal = Signal(
        concept="delimiter",
        value=";",
        evidence_ids=[uuid4()],
    )

    candidates = SignalBinder().bind(
        [signal],
        [
            AllowedPath(path="source.delimited.delimiter", concepts=["delimiter"]),
            AllowedPath(path="target.delimited.delimiter", concepts=["delimiter"]),
        ],
    )

    assert candidates == []
    assert signal.status == "unbound"


def test_bound_signal_returns_to_unbound_when_current_view_is_not_unique():
    signal = Signal(concept="delimiter", value=";", evidence_ids=[uuid4()])
    binder = SignalBinder()

    assert binder.bind(
        [signal],
        [AllowedPath(path="source.delimited.delimiter", concepts=["delimiter"])],
    )
    assert signal.status == "bound"

    assert binder.bind([signal], []) == []
    assert signal.status == "unbound"

    assert binder.bind(
        [signal],
        [
            AllowedPath(path="source.delimited.delimiter", concepts=["delimiter"]),
            AllowedPath(path="target.delimited.delimiter", concepts=["delimiter"]),
        ],
    ) == []
    assert signal.status == "unbound"


def test_binders_do_not_create_candidates_for_schema_wildcard_paths():
    allowed_paths = [AllowedPath(path="tables[*].name", concepts=["table_name"])]
    signal = Signal(concept="table_name", value="orders", evidence_ids=[uuid4()])
    preference = Preference(concept="table_name", value="orders", evidence_ids=[uuid4()])

    assert SignalBinder().bind([signal], allowed_paths) == []
    assert signal.status == "unbound"
    assert PreferenceExpander().expand([preference], allowed_paths) == []


def test_user_preference_candidate_without_evidence_is_invalid_state():
    with pytest.raises(ValidationError):
        ValueCandidate(path="source.format", value="parquet", origin=ValueOrigin.USER_PREFERENCE)
