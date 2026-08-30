"""S5, S4', S6' — rozpoznawanie intencji przez prawdziwy resolver LLM.

BUSINESS_BEHAVIOR: 4.3, SC-13, EC-14.

Te testy są NON-BLOCKING: marker `llm` jest odfiltrowany przez domyślne `addopts`,
więc nie wchodzą do żadnej bramki. Uruchamia się je jawnie:

    ... -m pytest ai-data-contract-manager\\tests\\live -q -m llm

Świadomie NIE ma tu `xfail(strict=False)`. Wynik ma być prawdziwy: jeżeli model
przestaje poprawnie klasyfikować intencję, test ma to pokazać, a nie zamaskować.

MIXED jest osiągalny wyłącznie tutaj. `HeuristicIntentResolver` zwraca tylko
MUTATION / KNOWLEDGE / UNRESOLVED, więc scenariusz „jawna zmiana + pytanie w jednej
wypowiedzi" nie ma deterministycznego odpowiednika. Nie dopisujemy gałęzi MIXED do
heurystyki po to, żeby test przeszedł.
"""

import pytest

from helpers import assert_document_unchanged, flatten_pointers

pytestmark = pytest.mark.llm


@pytest.fixture
def seeded_session(llm_client):
    session_id = llm_client.new_session()
    baseline = llm_client.turn(session_id, "ustaw /metadata/sourceSystemGcpId na sap")
    assert baseline["document"].get("metadata", {}).get("sourceSystemGcpId") == "sap", (
        "seed nie zadziałał, dalsze asercje nie miałyby sensu\n"
        f"document={baseline['document']}\nunresolved={baseline['unresolved']}"
    )
    return session_id, baseline


def test_mixed_intent_applies_only_the_explicit_change(llm_client, seeded_session):
    """4.3: w jednej wypowiedzi jawna zmiana wykonuje się, pytanie nie zmienia niczego."""
    session_id, baseline = seeded_session

    body = llm_client.turn(
        session_id,
        "ustaw /metadata/dataFileId na SAP_FILE i powiedz przy okazji, jakie są dostępne typy źródła",
    )

    assert body["document"]["metadata"]["dataFileId"] == "SAP_FILE"

    # Pytanie nie może dołożyć ani jednej mutacji poza tą, o którą jawnie poproszono.
    assert [item["path"] for item in body["changes"]] == ["/metadata/dataFileId"]

    expected = flatten_pointers(baseline["document"]) | {"/metadata/dataFileId": "SAP_FILE"}
    assert flatten_pointers(body["document"]) == expected


def test_knowledge_query_does_not_mutate(llm_client, seeded_session):
    """SC-13: pytanie o listę dopuszczalnych wartości nie jest decyzją o zmianie."""
    session_id, baseline = seeded_session

    body = llm_client.turn(session_id, "jakie są dostępne typy źródła?")

    assert_document_unchanged(baseline, body)
    assert body["changes"] == []


def test_knowledge_query_suggesting_a_value_is_not_accepted_as_a_decision(llm_client, seeded_session):
    """4.3: sugestia wartości zawarta w pytaniu nie może zostać przyjęta jako mutacja."""
    session_id, baseline = seeded_session

    body = llm_client.turn(session_id, "czy typ źródła to powinien być jdbc?")

    assert_document_unchanged(baseline, body)
    assert body["changes"] == []


def test_ambiguous_message_is_unresolved_and_changes_nothing(llm_client, seeded_session):
    """EC-14: przy nierozpoznanej intencji system prosi o doprecyzowanie."""
    session_id, baseline = seeded_session

    body = llm_client.turn(session_id, "no to tamto jak zwykle, wiesz o co chodzi")

    assert_document_unchanged(baseline, body)
    assert body["changes"] == []
    assert body["message"].startswith("Nie udało mi się jednoznacznie zrozumieć")
    assert body["unresolved"], "unresolved musi nieść powód nierozpoznania"
    for item in body["unresolved"]:
        assert isinstance(item["reason"], str) and item["reason"].strip(), item
