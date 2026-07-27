# Testowanie

## Uruchomienie

Pełny zestaw:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

`requirements.lock` zapisuje wersje użyte przez obecny zestaw testów dla
Windows i Pythona 3.11. `pyproject.toml` pozostaje deklaracją obsługiwanych
zakresów, a lock jest snapshotem odtwarzalnego środowiska.

Wybrane obszary:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_schema_service.py
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_stdio.py
.\.venv\Scripts\python.exe -m pytest tests/test_agent_app.py
.\.venv\Scripts\python.exe -m pytest tests/test_audit.py
```

## Zakres

| Plik | Sprawdzany obszar |
|---|---|
| `test_schema_service.py` | katalog wariantów, walidacja i YAML |
| `test_mcp_stdio.py` | prawdziwy stdio, timeout i współdzielenie sesji |
| `test_agent_app.py` | Web UI i deterministyczne wywołania narzędzi |
| `test_state_ops.py` | scope, fingerprinty i patche |
| `test_audit.py` | JSONL, redakcja, thinking i decision trace |
| `test_settings.py` | `.env` i walidacja konfiguracji |

Test regresyjny wariantów potwierdza, że błąd kolumny CSV nie zwraca wymagań
`start` ani `end` z fixed-width i zachowuje właściwy opis elementu tablicy.

## Strategie

- logika schematu używa prawdziwych przykładów JSON;
- narzędzia agenta korzystają z `FunctionModel`, więc testy nie wywołują LLM;
- adapter in-process izoluje zachowanie aplikacyjne;
- osobny test uruchamia prawdziwy serwer MCP stdio;
- mock lifecycle potwierdza, że dwa wywołania używają jednej inicjalizacji.

## Kryterium przed zmianą architektury

Refaktor bez zmiany zachowania jest zaakceptowany, gdy przechodzi pełny zestaw
testów i nie zmienia publicznych nazw narzędzi, kształtu ich argumentów ani
formatu odpowiedzi MCP.
