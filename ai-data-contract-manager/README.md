## Instalcja
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .

## Uruchomienie
cd ai-data-contract-manager
.\.venv\Scripts\Activate.ps1

$env:PYTHONPATH="src"
$env:ADCM_FORGE_URL="http://localhost:8000/mcp"
$env:ADCM_RULES_PATH="resources/ux_rules.json"
$env:ADCM_INTENT_MODE="heuristic" --dla heurystyki samej aplikacji bez llm
$env:ADCM_INTENT_MODE="pydantic-ai" --dla heurystyki llm
$env:ADCM_MODEL = "openai-chat:auto"
$env:OPENAI_BASE_URL = "http://localhost:3030/v1"

$env:ADCM_DEBUG_API="true" --opcjonalnie, włącza GET /v1/debug/sessions/{id}

uvicorn --factory adcm.adapters.api.composition:build_app --host 0.0.0.0 --port 8080 --reload

Import modułu nie tworzy niczego — aplikację buduje fabryka `build_app()`
(composition root), stąd flaga `--factory`.

## Testy

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

`pyproject.toml` rejestruje dwa markery i domyślnie je odfiltrowuje
(`addopts = -m "not live and not llm"`), więc powyższa komenda uruchamia wyłącznie
testy in-process:

- `live` — `tests/live/`, czarnoskrzynkowa suita end-to-end. Fixtury same startują
  realny Contract Forge i realny ADCM (przez `uvicorn --factory`, na wolnych portach)
  i asercjonują wyłącznie na publicznym kontrakcie REST v1.
- `llm` — podzbiór wymagający prawdziwego resolvera intencji; **non-blocking**,
  bez `OPENAI_BASE_URL`/`ADCM_MODEL` daje `skip`.

```bash
.venv/Scripts/python.exe -m pytest tests/live -q -m live
.venv/Scripts/python.exe -m pytest tests/live -q -m llm
```

Szczegóły i uzasadnienie podziału: sekcja „Testy live" w `README.md` w katalogu głównym.

## REST API v1

Publiczny kontrakt (OpenAPI: `/docs`, `/openapi.json`):

```text
GET  /health
POST /v1/sessions                       -> 201 {session_id, turn_no, status}
GET  /v1/sessions/{session_id}          -> 200 | 404
POST /v1/sessions/{session_id}/turns    -> 200 | 404 | 422 | 503
POST /v1/sessions/{session_id}/turn     -> deprecated alias dla /turns
```

Identyfikator sesji generuje ADCM — klient go nie wybiera. Przykład:

```bash
SESSION=$(curl -sX POST http://localhost:8080/v1/sessions | jq -r .session_id)
curl -X POST http://localhost:8080/v1/sessions/$SESSION/turns \
  -H 'Content-Type: application/json' -d '{"message":"sourceSystemGcpId sap"}'
curl http://localhost:8080/v1/sessions/$SESSION
```

Odpowiedź tury zawiera wyłącznie to, co potrzebne klientowi: `message`, `document`,
`contract_status`, `missing`, `diagnostics`, `unresolved`, `changes`, `correlation_id`.
Pełny `ForgeAnalysis`, przebieg stabilizacji, `provenance` i `mutation_log` pozostają
wewnętrzne — dostępne w Session Audit oraz przez `GET /v1/debug/sessions/{id}`
przy `ADCM_DEBUG_API=true`.

Błędy mają jeden kształt:

```json
{"error": {"code": "session_not_found", "message": "Session not found", "correlation_id": "..."}}
```

Kody: `session_not_found` (404), `validation_error` (422),
`contract_forge_unavailable` (503), `internal_error` (500).

## Obserwowalność

ADCM zapisuje application log oraz session audit. Domyślnie backend to JSONL:

```text
ADCM_LOG_BACKEND=local
ADCM_LOG_DIR=logs
ADCM_ENVIRONMENT=local
ADCM_AUDIT_LEVEL=normal
```

Application log trafia do `logs/app/YYYY-MM-DD.jsonl`, a audit sesji do
`logs/sessions/<bezpieczny-session-id>.jsonl`.

`ADCM_AUDIT_LEVEL` steruje szczegółowością session audit. W trybie `normal`
`forge.analysis.completed` jest compact summary (liczniki zamiast powtarzanej
w każdej rundzie listy `writable[]`), a `turn.completed` nie duplikuje historii
`proposal_decisions[]` — szczegóły pozostają w osobnych eventach
`forge.proposal.received`, `rule.proposal.generated` i `proposal.decision`.
Tryb `debug` przywraca pełny `ForgeAnalysis`. Dla BigQuery ustaw `ADCM_LOG_BACKEND=bigquery`,
`ADCM_BQ_PROJECT`, `ADCM_BQ_DATASET` oraz opcjonalnie
`ADCM_BQ_APP_LOG_TABLE` (domyślnie `app_logs`) i
`ADCM_BQ_SESSION_AUDIT_TABLE` (domyślnie `session_audit`). Zależność jest
opcjonalna: `pip install -r requirements-bigquery.txt` (lub extra
`pip install -e .[bigquery]`).
Przy budowie obrazu GCP wskaż `--build-arg REQUIREMENTS_FILE=requirements-bigquery.txt`.
