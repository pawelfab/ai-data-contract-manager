"""S3 — jawna decyzja użytkownika wygrywa z regułą aplikacji i pozostaje autorytatywna.

BUSINESS_BEHAVIOR: EC-06, EC-07, SC-06, J-02.

Publiczny kontrakt nie wystawia provenance, więc autorytetu nie da się sprawdzić
wprost. Dowodem jest zachowanie w czasie: wartość użytkownika musi przetrwać kolejne
tury, w których reguła znów proponuje swoją wersję - i musi pociągnąć za sobą
wartości od niej pochodne.
"""

import pytest

from helpers import assert_present, assert_status, change_at, missing_paths

pytestmark = pytest.mark.live


def test_explicit_user_value_beats_app_rule_and_survives_later_turns(client):
    session_id = client.new_session()

    seeded = client.turn(session_id, "system sap")
    # Punkt wyjścia: /metadata/id pochodzi z reguły global.source_system.metadata_id.
    assert_present(seeded["document"], {"/metadata/id": "sap"})

    overridden = client.turn(session_id, "/metadata/id = SAP_CUSTOM")
    assert_present(overridden["document"], {"/metadata/id": "SAP_CUSTOM"})
    # Wartość pochodna idzie za decyzją użytkownika, a nie za regułą, która ją zrodziła.
    assert_present(overridden["document"], {"/converter/outputFilename": "SAP_CUSTOM_{{data_danych}}.csv"})
    assert change_at(overridden, "/converter/outputFilename")["old_value"] == "sap_{{data_danych}}.csv"

    # EC-06: kolejna tura znów uruchamia stabilizację i regułę - i znów musi przegrać.
    later = client.turn(session_id, "/metadata/dataFileId = SAP_FILE")
    assert_present(
        later["document"],
        {
            "/metadata/id": "SAP_CUSTOM",
            "/converter/outputFilename": "SAP_CUSTOM_{{data_danych}}.csv",
            "/metadata/sourceSystemGcpId": "sap",
        },
    )
    # Tura zmieniła wyłącznie to, o co poprosił użytkownik.
    assert [item["path"] for item in later["changes"]] == ["/metadata/dataFileId"]
    assert_status(later, valid=True, complete=True, clean=True)


def test_last_user_decision_wins_after_repeated_changes(client):
    """EC-07: użytkownik może zmieniać tę samą wartość wielokrotnie."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "/metadata/id = FIRST")
    client.turn(session_id, "/metadata/id = SECOND")

    body = client.turn(session_id, "/metadata/id = THIRD")

    assert_present(
        body["document"],
        {"/metadata/id": "THIRD", "/converter/outputFilename": "THIRD_{{data_danych}}.csv"},
    )
    assert change_at(body, "/metadata/id")["old_value"] == "SECOND"


def test_user_value_is_not_resurrected_by_the_rule_after_removal(client):
    """Usunięcie wartości użytkownika oddaje pole regule, zamiast blokować je na zawsze."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "/metadata/id = SAP_CUSTOM")

    body = client.turn(session_id, "remove /metadata/id")

    # Reguła znów jest właścicielem pola, więc wartość wraca do konwencji systemu.
    assert_present(body["document"], {"/metadata/id": "sap"})
    assert_present(body["document"], {"/converter/outputFilename": "sap_{{data_danych}}.csv"})
    assert missing_paths(body) == ["/metadata/dataFileId"]
