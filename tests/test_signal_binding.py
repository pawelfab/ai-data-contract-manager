from adcm.application.signal_binder import SignalBinder
from adcm.domain.models import AllowedPath, Signal


def test_pre_path_signal_waits_until_concept_is_legal():
    signal = Signal(concept="field_delimiter", value=";")
    binder = SignalBinder()
    assert binder.bind([signal], [AllowedPath(path="source.system", concepts=["source_system"])]) == []
    assert signal.status == "unbound"
    candidates = binder.bind(
        [signal],
        [AllowedPath(path="source.delimited.delimiter", concepts=["field_delimiter"])],
    )
    assert len(candidates) == 1
    assert candidates[0].path == "source.delimited.delimiter"
