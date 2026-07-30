# AI Data Contract Manager

Projekt składa się z dwóch lokalnych aplikacji:

- `acdm` — webowy agent Pydantic AI, który interpretuje rozmowę i prowadzi
  użytkownika przez tworzenie kontraktu;
- `mcp-contract-forge` — deterministyczny serwer MCP, który odczytuje JSON
  Schema, zwraca wymagania aktywnego wariantu, waliduje draft i generuje YAML.

Najważniejsza zasada architektoniczna:

> LLM interpretuje wypowiedź użytkownika. MCP definiuje i waliduje kontrakt.
> Pydantic przechowuje typowany stan. YAML powstaje wyłącznie w MCP.

## Wymagania

- Python 3.11 lub nowszy;
- PowerShell — poniższe przykłady są przygotowane dla Windows;
- klucz i URL API dostawcy modelu zgodnego z konfiguracją Pydantic AI.

## Instalacja

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Do odtworzenia dokładnie przetestowanego zestawu zależności na Windows
i Pythonie 3.11:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
```

Uzupełnij co najmniej `OPENAI_API_KEY` w `.env`. Jeśli używasz własnego
endpointu zgodnego z OpenAI, ustaw również `OPENAI_BASE_URL`.

## Uruchomienie

```powershell
.\.venv\Scripts\python.exe -m acdm.main
```

Domyślnie `ACDM_CONTRACT_TRANSPORT=stdio`. ACDM uruchamia wtedy
`mcp-contract-forge` przez bieżący interpreter:

```text
python -m mcp_contract_forge.server
```

Jeden proces i jedna zainicjalizowana sesja MCP są współdzielone przez
wywołania aplikacji aż do jej zamknięcia.

Do szybkiego developmentu bez osobnego procesu MCP można ustawić:

```dotenv
ACDM_CONTRACT_TRANSPORT=inprocess
```

Interfejs jest dostępny domyślnie pod `http://127.0.0.1:7932`.

## Testy

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Testy nie wymagają prawdziwego modelu LLM. Zachowanie agenta jest sprawdzane
przez `FunctionModel`, a logika kontraktu przez adapter in-process i prawdziwy
transport MCP stdio.

## Źródła prawdy

- kanoniczny JSON Schema:
  `contracts/data-contract.schema.json`;
- poprawne przykłady:
  `examples/csv-bronze.contract.json` oraz
  `examples/fixed-width-all-layers.contract.json`;
- `examples/legacy-contract.partial.json` jest wyłącznie historycznym,
  niekompletnym przykładem i nie jest czytany przez aplikację.

## Dokumentacja

- [Architektura](docs/architecture.md)
- [Przepływ agenta i stan sesji](docs/agent-workflow.md)
- [Kontrakt MCP](docs/mcp-contract-forge.md)
- [Konfiguracja](docs/configuration.md)
- [Testowanie](docs/testing.md)
- [Logowanie audytowe](docs/audit-logging.md)
- [Scenariusz MVP](docs/mvp-usage.md)
- [Roadmapa ACDM](docs/acdm-plan.md)
- [Roadmapa Contract Forge](docs/mcp-contract-forge-plan.md)

## Aktualne ograniczenia

- `Agent.to_web()` jest developerskim interfejsem lokalnym;
- `InMemorySessionStore` traci aktywny `ContractState` po restarcie procesu;
- historia widoczna w menu przeglądarki jest zarządzana przez Web Chat UI;
- log audytowy JSONL nie jest repozytorium stanu i nie odtwarza sesji;
- aplikacja nie ma jeszcze uwierzytelniania, własnego UI ani Schema Advisora.
