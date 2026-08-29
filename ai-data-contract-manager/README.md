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

uvicorn adcm.adapters.api.app:app --host 0.0.0.0 --port 8080 --reload

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
