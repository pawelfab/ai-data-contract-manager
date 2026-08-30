"""Klient HTTP i asercje suity live.

Wszystko tutaj operuje wyłącznie na publicznym kontrakcie REST v1: `document`,
`contract_status`, `missing`, `diagnostics`, `unresolved`, `changes`, `message`.
Świadomie nie ma dostępu do provenance ani mutation logu — te nie są kontraktem
publicznym (`docs/CORE_INVARIANTS.md` #18), więc test, który ich potrzebuje,
sprawdza nie to, co trzeba.
"""

from typing import Any

import httpx2

TURNS_PATH = "/v1/sessions/{session_id}/turns"


class AdcmClient:
    """Cienka nakładka na REST API v1. Bez wiedzy o strukturze kontraktu."""

    def __init__(self, base_url: str, *, timeout: float = 60.0) -> None:
        self._http = httpx2.Client(base_url=base_url, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def new_session(self) -> str:
        response = self._http.post("/v1/sessions")
        _expect(response, 201, "POST /v1/sessions")
        return response.json()["session_id"]

    def turn(self, session_id: str, message: str) -> dict:
        response = self._http.post(TURNS_PATH.format(session_id=session_id), json={"message": message})
        _expect(response, 200, f"POST turn {message!r}")
        return response.json()

    def state(self, session_id: str) -> dict:
        response = self._http.get(f"/v1/sessions/{session_id}")
        _expect(response, 200, f"GET /v1/sessions/{session_id}")
        return response.json()


def _expect(response, status: int, what: str) -> None:
    if response.status_code != status:
        raise AssertionError(f"{what}: oczekiwano {status}, dostano {response.status_code}\nbody: {response.text}")


def flatten_pointers(document: dict) -> dict[str, Any]:
    """Dokument jako mapa JSON Pointer -> wartość, tylko dla liści.

    Puste kontenery są zachowane jako liście, bo aktywacja sekcji opcjonalnej
    pustym obiektem jest w tym systemie znaczącym stanem (BUSINESS_BEHAVIOR EC-12).
    """
    result: dict[str, Any] = {}

    def walk(node: Any, pointer: str) -> None:
        if isinstance(node, dict) and node:
            for key, value in node.items():
                walk(value, f"{pointer}/{_escape(key)}")
        elif isinstance(node, list) and node:
            for index, value in enumerate(node):
                walk(value, f"{pointer}/{index}")
        else:
            result[pointer] = node

    walk(document, "")
    return result


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def missing_paths(body: dict) -> list[str]:
    return [item["path"] for item in body["missing"]]


def changes_by_operation(body: dict, operation: str) -> list[dict]:
    return [item for item in body["changes"] if item["operation"] == operation]


def change_at(body: dict, path: str) -> dict | None:
    return next((item for item in body["changes"] if item["path"] == path), None)


def assert_status(body: dict, *, valid: bool, complete: bool, clean: bool) -> None:
    expected = {"valid": valid, "complete": complete, "clean": clean}
    assert body["contract_status"] == expected, (
        f"status={body['contract_status']}, oczekiwano {expected}\n"
        f"missing={missing_paths(body)}\ndiagnostics={body['diagnostics']}"
    )


def assert_document_unchanged(before: dict, after: dict) -> None:
    """Tura nie zmieniła stanu kontraktu ani jego oceny."""
    assert after["document"] == before["document"], (
        "dokument zmienił się, a nie powinien\n"
        f"było:  {flatten_pointers(before['document'])}\n"
        f"jest:  {flatten_pointers(after['document'])}"
    )
    assert missing_paths(after) == missing_paths(before), "zmieniła się lista missing"
    assert after["contract_status"] == before["contract_status"], "zmienił się contract_status"


def assert_no_stale_value(document: dict, needle: str) -> None:
    """Żaden klucz ani string w dokumencie nie nosi już śladu po `needle`.

    To jest asercja „brak stale values" z SC-04: po zmianie systemu źródłowego nic
    wyprowadzonego z poprzedniego systemu nie może zostać w dokumencie.
    """
    lowered = needle.lower()
    offenders: list[str] = []
    for pointer, value in flatten_pointers(document).items():
        if lowered in pointer.lower():
            offenders.append(f"{pointer} (ścieżka)")
        if isinstance(value, str) and lowered in value.lower():
            offenders.append(f"{pointer} = {value!r}")
    assert not offenders, f"stale values po {needle!r}: " + ", ".join(offenders)


def assert_absent(document: dict, *pointers: str) -> None:
    present = flatten_pointers(document)
    still_there = [pointer for pointer in pointers if any(key == pointer or key.startswith(f"{pointer}/") for key in present)]
    assert not still_there, f"te ścieżki miały zniknąć, a są: {still_there}\ndokument: {present}"


def assert_present(document: dict, expected: dict[str, Any]) -> None:
    actual = flatten_pointers(document)
    wrong = {
        pointer: (actual.get(pointer, "<brak>"), value)
        for pointer, value in expected.items()
        if actual.get(pointer, "<brak>") != value
    }
    assert not wrong, "niezgodne wartości {pointer: (jest, oczekiwano)}: " + repr(wrong)
