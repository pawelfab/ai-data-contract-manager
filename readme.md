# ADCM Minimal v0.1

Minimalna, uruchamialna implementacja nowego ADCM zgodna z założeniem:

- **ADCM jest orkiestratorem rozmowy**, normalizatorem wejścia i klientem MCP.
- **Contract Forge MCP jest właścicielem kontraktu** i jedynym komponentem, który mutuje kanoniczny stan kontraktu.
- pierwszy krok rozmowy zawsze wybiera **system źródłowy**;
- potem Forge wykonuje kolejno:
  1. enrichment systemowy,
  2. enrichment wspólny,
  3. `default` z `contract.json`,
  4. zwraca brakujące wymagane pola;
- ADCM próbuje odpowiedzieć na odkryte wymagania informacjami, które user podał wcześniej; jeśli nie ma podstaw, pyta usera;
- literówki i różne formaty wklejonych kolumn są normalizowane deterministycznie, a opcjonalnie semantycznie przez Pydantic AI;
- terminal jest interfejsem demo, ale ten sam orchestrator jest wystawiony przez FastAPI, więc web UI można dołożyć bez zmiany logiki kontraktu.

## Struktura

```text
src/
  adcm/
    orchestrator.py    # schodkowa pętla rozmowy
    heuristics.py      # literówki, scalar parsing, kolumny
    semantic.py        # opcjonalny Pydantic AI resolver
    gateway.py         # MCP / local adapter
    api.py             # FastAPI dla przyszłego UI
    cli.py             # terminal demo
  contract_forge/
    engine.py          # kanoniczny stan sesji i kolejność enrichmentów
    schema.py          # dynamiczna nawigacja po JSON Schema
    rules.py           # enrichment engine
    mcp_server.py      # referencyjny Contract Forge MCP
config/
  contract.json
  ux_rules_original.json
  ux_rules_contract_v1.json
```

## Najszybszy smoke test bez sieci MCP

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
adcm-cli --local-forge
```

Przykładowa ścieżka Rocket:

```text
ADCM: Jaki jest system źródłowy?
> roket
ADCM: Jak ma się nazywać pipeline?
> customer_accounts_daily
ADCM: Zespół lub adres kontaktowy odpowiedzialny za pipeline.
> data-platform@example.com
ADCM: Gdzie znajduje się plik stałopozycyjny?
> gs://raw-zone/accounts/accounts.dat
ADCM: Podaj nazwy, typy i zakresy start/end kolumn fixed-width.
account_id 0 8 STRING NOT NULL
balance 8 20 NUMERIC
<blank line>
```

## Docelowy wariant z MCP Streamable HTTP

Instalacja:

```bash
pip install -e ".[mcp,dev]"
```

Terminal 1 — Contract Forge MCP:

```bash
contract-forge-mcp
```

Domyślnie endpoint to:

```text
http://127.0.0.1:8001/mcp
```

Terminal 2 — ADCM:

```bash
set ADCM_MCP_URL=http://127.0.0.1:8001/mcp
adcm-cli
```

PowerShell:

```powershell
$env:ADCM_MCP_URL = "http://127.0.0.1:8001/mcp"
adcm-cli
```

## Pydantic AI + lokalny gateway OpenAI-compatible

Runtime automatycznie ładuje `.env` z katalogu projektu. Zmienne procesu mają
pierwszeństwo, dzięki czemu ten sam obiekt ustawień działa lokalnie i w Cloud Run.

Instalacja:

```bash
pip install -e ".[openai,dev]"
```

Konfiguracja gatewaya działającego pod `http://127.0.0.1:3030`:

```dotenv
ADCM_LLM_MODE=pydantic
ADCM_LLM_PROVIDER=openai_compatible
ADCM_MODEL=auto
OPENAI_BASE_URL=http://127.0.0.1:3030/v1
OPENAI_API_KEY=local-gateway
```

ADCM używa jawnego `OpenAIChatModel` z profilem zgodności gatewaya. Structured
output jest przesyłany jako JSON mode, ponieważ ten gateway odrzuca
`tool_choice=required` używany domyślnie przez część konfiguracji Pydantic AI.
Wynik nadal przechodzi walidację `ExtractionResult`, a następnie walidację
Contract Forge.

## Pydantic AI + Vertex AI

Tryb LLM jest opcjonalny. Heurystyki działają bez kosztu LLM, a Pydantic AI jest używany tylko wtedy, gdy deterministyczne parsowanie nie wystarcza lub gdy trzeba odzyskać informację podaną wcześniej w rozmowie.

```bash
pip install -e ".[vertex,dev]"
```

PowerShell:

```powershell
$env:ADCM_LLM_MODE = "pydantic"
$env:ADCM_VERTEX_MODEL = "gemini-2.5-flash"
$env:GOOGLE_CLOUD_PROJECT = "your-project"
$env:GOOGLE_CLOUD_LOCATION = "europe-west1"
gcloud auth application-default login
adcm-cli
```

LLM **nie wybiera sam narzędzi MCP i nie mutuje kontraktu**. Zwraca wyłącznie kandydaty dla ścieżek aktualnie wymaganych przez Forge. Forge je waliduje i dopiero wtedy aktualizuje stan.

## API pod przyszły web UI

Uruchom najpierw Contract Forge MCP, potem:

```bash
adcm-api
```

Endpointy:

```text
POST /sessions
POST /sessions/{session_id}/messages
GET  /sessions/{session_id}
GET  /health
```

Web UI powinno być cienkim klientem tych endpointów. Nie powinno znać `contract.json`, enrichmentów ani kolejności pól.

## Priorytet źródeł wartości

```text
user explicit
    > LLM fact extracted from user history
    > system enrichment
    > generic enrichment
    > JSON Schema default
```

W v0 edycja wcześniej wzbogaconej wartości nie jest jeszcze częścią rozmowy. Forge przyjmuje tylko ścieżki, które aktualnie zgłasza jako `pending` — to celowe ograniczenie bezpieczeństwa demo.

## Co jest dynamiczne

Bez zmian w ADCM obsługiwane są m.in.:

- nowe wymagane pola w istniejących obiektach,
- nowe `default`, `enum`, `pattern`, opisy i `x-acdm-question`,
- zmiana listy pól wymaganych,
- istniejące warianty `source.oneOf` wybierane przez discriminator; jeśli system ma dokładnie jeden `sourceType`, Forge wybiera go automatycznie, a przy wielu zwraca wybór userowi,
- defaults w elementach tablic,
- końcowa walidacja pełnym JSON Schema Draft 2020-12.

Zmiany wymagające rozszerzenia Forge:

- nowy typ akcji enrichmentu,
- semantyka nowego `x-contract-rules.kind`, jeśli nie jest wyrażona standardowym JSON Schema,
- zupełnie nowy mechanizm wariantów nieoparty o obecny discriminator,
- reguły odwołujące się do zewnętrznych rejestrów/BigQuery/GitHub.

To jest świadoma granica: elastyczność strukturalna jest dynamiczna, ale logika biznesowa nie jest interpretowana z tekstu `message` ani z nazwy `id`.

## Testy

```bash
pytest -q
```

Obecne testy pokrywają:

- pełny Rocket happy path,
- enrichment SAP,
- literówkę systemu,
- parsowanie CSV/SQL-like i fixed-width columns,
- schodkową pętlę ADCM,
- dynamiczne odkrycie nowego required field po zmianie schema.

## Ograniczenia v0

1. Sesje Forge i ADCM są w pamięci procesu. Dla Cloud Run / wielu replik trzeba wprowadzić zewnętrzny state store.
2. `x-acdm-optional-decision` nie jest jeszcze osobnym etapem rozmowy; v0 interpretuje „brakujące pola” jako **wymagane przez aktywny wariant JSON Schema** i kończy po ich wypełnieniu oraz walidacji.
3. Nie ma workflow edycji gotowego kontraktu.
4. Nie ma auth, audytu i trwałego logowania sesji.
5. Nie ma jeszcze Schema Explorer MCP ani walidacji nazw w BigQuery/GitHub.
6. Stary `ux_rules_new.json` nie pasuje do obecnego `contract.json`; do demo używany jest jawnie zmigrowany `ux_rules_contract_v1.json`.

Szczegóły: `docs/ARCHITECTURE.md`, `docs/RULE_COMPATIBILITY.md`, `docs/IMPLEMENTATION_PLAN.md`.
