from uuid import uuid4

import pytest
from pydantic import ValidationError

from adcm.application.signal_binder import SignalBinder
from adcm.domain.models import AllowedPath, Signal, ValueOrigin


def test_pre_path_signal_waits_until_concept_is_legal_and_propagates_evidence():
    evidence_id = uuid4()
    signal = Signal(
        concept="field_delimiter",
        value=";",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[evidence_id],
    )
    binder = SignalBinder()
    assert binder.bind([signal], [AllowedPath(path="source.system", concepts=["source_system"])]) == []
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
