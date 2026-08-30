"""S1, S2 — enrichment po systemie źródłowym i jego przeliczenie po zmianie systemu.

BUSINESS_BEHAVIOR: SC-02, SC-04, SC-19, EC-07, J-02, D-01.

To jest miejsce, w którym testy in-process nic nie mówią: `FakeForge` zawsze zwraca
valid/complete, więc reguły ADCM i propozycje Forge nigdy nie spotykały się w jednej
rundzie uzgadniania na realnej analizie kontraktu.
"""

import pytest

from helpers import (
    assert_absent,
    assert_no_stale_value,
    assert_present,
    assert_status,
    changes_by_operation,
    change_at,
    missing_paths,
)

pytestmark = pytest.mark.live


# Pełny łańcuch wyprowadzeń dla `sap`: wartość usera, reguły aplikacji,
# enrichment Forge i default Forge naraz.
SAP_DOCUMENT = {
    "/metadata/sourceSystemGcpId": "sap",  # USER_EXPLICIT
    "/metadata/id": "sap",  # APP_RULE  global.source_system.metadata_id
    "/metadata/version": "1.0.0",  # FORGE_DEFAULT
    "/source/sourceType": "csv",  # APP_RULE  sap.source_type
    "/source/systemZrodlowy": "sap",  # APP_RULE  global.source_system.source_metadata
    "/source/encoding": "UTF-8",  # FORGE_ENRICHMENT  csv.default_encoding
    "/converter/outputFilename": "sap_{{data_danych}}.csv",  # APP_RULE  sap.converter_filename
}


def test_source_system_triggers_full_enrichment_chain(client):
    """SC-02: podanie systemu uzupełnia metadane i włącza sekcje typowe dla systemu."""
    session_id = client.new_session()

    body = client.turn(session_id, "system sap")

    assert_present(body["document"], SAP_DOCUMENT)
    # SC-19: poprawny, ale niekompletny - obie flagi muszą być obserwowalne osobno.
    assert_status(body, valid=True, complete=False, clean=True)
    assert missing_paths(body) == ["/metadata/dataFileId"]
    assert body["diagnostics"] == []
    assert body["unresolved"] == []

    # Jedna wypowiedź użytkownika, ale wyprowadzeń jest wiele - i wszystkie są jawne.
    changed_paths = {item["path"] for item in body["changes"]}
    assert SAP_DOCUMENT.keys() <= changed_paths
    assert change_at(body, "/metadata/sourceSystemGcpId")["new_value"] == "sap"

    # Stan sesji po turze musi zgadzać się z odpowiedzią tury.
    state = client.state(session_id)
    assert state["document"] == body["document"]
    assert state["contract_status"] == body["contract_status"]
    assert state["turn_no"] == body["turn_no"] == 1


def test_changing_source_system_recomputes_and_leaves_no_stale_values(client):
    """SC-04: po zmianie systemu nic po poprzednim systemie nie zostaje."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")

    body = client.turn(session_id, "system rocket")

    assert_present(
        body["document"],
        {
            "/metadata/sourceSystemGcpId": "rocket",
            "/metadata/id": "rocket",
            "/metadata/version": "1.0.0",
        },
    )
    # To jest sedno SC-04: żaden ślad po `sap` w żadnym kluczu ani wartości.
    assert_no_stale_value(body["document"], "sap")

    # Reguły `scope=system:sap` przestały być aktywne, więc ich wytwory są wycofane.
    # `/source` znika w całości, bo po wycofaniu nie ma już w nim żadnego liścia.
    assert_absent(body["document"], "/source", "/converter")

    removed = {item["path"] for item in changes_by_operation(body, "remove")}
    assert {"/source/sourceType", "/source/encoding", "/converter"} <= removed

    # Wycofanie wyprowadzeń odsłania braki, które wcześniej były zaspokojone regułą.
    assert set(missing_paths(body)) == {
        "/source/sourceType",
        "/source/systemZrodlowy",
        "/metadata/dataFileId",
    }
    assert_status(body, valid=True, complete=False, clean=True)


def test_switching_system_back_restores_the_previous_conventions(client):
    """EC-07: obowiązuje ostatnia decyzja użytkownika, także gdy wraca do poprzedniej."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "system rocket")

    body = client.turn(session_id, "system sap")

    # Reguły są deterministyczne i bezstanowe: ten sam wybór daje ten sam wynik.
    assert_present(body["document"], SAP_DOCUMENT)
    assert_no_stale_value(body["document"], "rocket")
    assert missing_paths(body) == ["/metadata/dataFileId"]
