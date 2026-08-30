"""S7, S8 — domknięcie kontraktu, późniejsza edycja pola oraz pole obce.

BUSINESS_BEHAVIOR: SC-15, SC-18, SC-19, SC-20, D-02, D-06, J-04.

S8 jest świadomie kruchy: `foreign` nie należy do publicznego kontraktu REST, więc
jedynym śladem usunięcia pola obcego dostępnym klientowi jest tekst `message`. Zmiana
brzmienia komunikatu w composerze wywali ten test - i tak ma być, bo D-02 czyni ten
komunikat obietnicą wobec użytkownika, a nie szczegółem implementacji.
"""

import pytest

from helpers import assert_present, assert_status, change_at, changes_by_operation, missing_paths

pytestmark = pytest.mark.live

FOREIGN_REMOVAL_NOTICE = "usunięto pola obce: /source/separator"


def test_contract_reaches_complete_and_yields_yaml(client):
    """SC-19 -> SC-18: od poprawnego-niekompletnego do gotowego artefaktu."""
    session_id = client.new_session()

    seeded = client.turn(session_id, "system sap")
    assert_status(seeded, valid=True, complete=False, clean=True)
    assert missing_paths(seeded) == ["/metadata/dataFileId"]
    assert "YAML:" not in seeded["message"]

    completed = client.turn(session_id, "/metadata/dataFileId = SAP_FILE")

    assert_status(completed, valid=True, complete=True, clean=True)
    assert missing_paths(completed) == []
    # SC-18: dopiero kontrakt kompletny i poprawny daje finalny artefakt biznesowy.
    assert "YAML:" in completed["message"]
    assert "dataFileId: SAP_FILE" in completed["message"]


def test_completed_contract_accepts_a_later_edit_of_the_same_field(client):
    """Kompletność nie zamraża kontraktu - pole nadal wolno poprawić."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "/metadata/dataFileId = SAP_FILE")

    edited = client.turn(session_id, "/metadata/dataFileId = SAP_FILE_V2")

    assert_present(edited["document"], {"/metadata/dataFileId": "SAP_FILE_V2"})
    assert_status(edited, valid=True, complete=True, clean=True)
    change = change_at(edited, "/metadata/dataFileId")
    assert change["operation"] == "replace"
    assert change["old_value"] == "SAP_FILE"
    assert change["new_value"] == "SAP_FILE_V2"


def test_removing_a_required_value_makes_the_contract_incomplete_again(client):
    """`complete` jest przeliczane co turę, a nie zapamiętywane."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "/metadata/dataFileId = SAP_FILE")

    body = client.turn(session_id, "remove /metadata/dataFileId")

    assert_status(body, valid=True, complete=False, clean=True)
    assert missing_paths(body) == ["/metadata/dataFileId"]
    assert "YAML:" not in body["message"]
    assert changes_by_operation(body, "remove"), "usunięcie musi być widoczne w changes"


def test_foreign_field_is_accepted_then_removed_and_reported(client):
    """SC-15 + D-06: system nie blokuje wpisu prewencyjnie, tylko wydaje werdykt."""
    session_id = client.new_session()
    client.turn(session_id, "system sap")
    client.turn(session_id, "/metadata/dataFileId = SAP_FILE")

    body = client.turn(session_id, "/source/separator = ;")

    # Pole nie zostaje w kontrakcie - `separator` nie należy do aktywnego kształtu.
    assert "separator" not in body["document"]["source"], body["document"]["source"]
    # D-02: użytkownik ZAWSZE dostaje komunikat o usunięciu.
    assert FOREIGN_REMOVAL_NOTICE in body["message"]

    # D-06: wpis najpierw trafia do dokumentu, dopiero potem zapada werdykt.
    # Obie operacje są jawne w `changes` - nic nie dzieje się po cichu.
    assert change_at(body, "/source/separator") is not None
    assert {"/source/separator"} <= {item["path"] for item in changes_by_operation(body, "remove")}

    # J-04: pozycja obca nie unieważnia kontraktu, bo została posprzątana w tej samej turze.
    assert_status(body, valid=True, complete=True, clean=True)
