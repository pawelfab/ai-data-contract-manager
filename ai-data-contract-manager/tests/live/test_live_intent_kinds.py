"""S4, S6 — pytanie o wiedzę i wypowiedź nierozpoznana nie mutują kontraktu.

BUSINESS_BEHAVIOR: SC-12, SC-13, EC-14, 4.3.

Ograniczenie, o którym trzeba wiedzieć czytając te asercje: `knowledge_query` jest
dziś wyliczane przez politykę intencji, ale nigdzie nie konsumowane - nie ma go na
`TurnOutcome`, a composer zwraca dla tury KNOWLEDGE ten sam tekst status/missing co
dla tury mutacyjnej. Dlatego sprawdzamy wyłącznie inwariant „dokument się nie zmienił",
a nie treść odpowiedzi. Kryterium biznesowe SC-13 jest dziś nieimplementowalne.
"""

import pytest

from helpers import assert_document_unchanged, assert_status, missing_paths

pytestmark = pytest.mark.live


@pytest.fixture
def seeded_session(client):
    """Sesja z niepustym, ustabilizowanym kontraktem - żeby było co zepsuć."""
    session_id = client.new_session()
    baseline = client.turn(session_id, "system sap")
    return session_id, baseline


@pytest.mark.parametrize(
    "question",
    [
        "jakie są dostępne typy źródła?",
        "co jeszcze mogę uzupełnić?",
        "jakie pola są dostępne?",
    ],
)
def test_knowledge_query_does_not_change_the_contract(client, seeded_session, question):
    """SC-12, SC-13: pytanie o wiedzę nie jest decyzją o zmianie wartości."""
    session_id, baseline = seeded_session

    body = client.turn(session_id, question)

    assert_document_unchanged(baseline, body)
    assert body["changes"] == []
    assert body["unresolved"] == []
    # Tura się odbyła, mimo że nic nie zmieniła - jedna wypowiedź, jedna odpowiedź (4.1).
    assert body["turn_no"] == baseline["turn_no"] + 1

    # Stan sesji też nie drgnął.
    state = client.state(session_id)
    assert state["document"] == baseline["document"]
    assert state["turn_no"] == body["turn_no"]


def test_unresolved_message_asks_for_clarification_without_mutating(client, seeded_session):
    """EC-14: nierozpoznana intencja nie staje się decyzją użytkownika."""
    session_id, baseline = seeded_session

    body = client.turn(session_id, "abrakadabra qwerty")

    assert_document_unchanged(baseline, body)
    assert body["changes"] == []

    assert body["message"].startswith("Nie udało mi się jednoznacznie zrozumieć")
    # Odpowiedź na nierozpoznaną wypowiedź nie udaje raportu o stanie kontraktu.
    assert "YAML:" not in body["message"]
    assert "valid=" not in body["message"]

    # Powód nierozpoznania musi dotrzeć do klienta, a nie kończyć w audycie.
    assert body["unresolved"], "unresolved nie może być puste dla nierozpoznanej intencji"
    for item in body["unresolved"]:
        assert isinstance(item["reason"], str) and item["reason"].strip(), item


def test_unresolved_turn_does_not_block_the_next_real_change(client, seeded_session):
    """Nierozpoznana tura jest epizodem, nie stanem sesji."""
    session_id, baseline = seeded_session
    client.turn(session_id, "zupełnie niezrozumiała wypowiedź")

    body = client.turn(session_id, "/metadata/dataFileId = SAP_FILE")

    assert body["document"]["metadata"]["dataFileId"] == "SAP_FILE"
    assert missing_paths(body) == []
    assert_status(body, valid=True, complete=True, clean=True)
