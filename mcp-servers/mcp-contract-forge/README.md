## Instalacja
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .

## Uruchomienie
cd mcp-servers/mcp-contract-forge
.\.venv\Scripts\Activate.ps1

set PYTHONPATH=src
set FORGE_CONTRACT_PATH=resources\contract.json

uvicorn contract_forge.server:app --host 0.0.0.0 --port 8000 --reload

## Obserwowalność

Forge zapisuje application log. Domyślnie backend to JSONL:

```text
FORGE_LOG_BACKEND=local
FORGE_LOG_DIR=logs
FORGE_ENVIRONMENT=local
```

Log znajduje się w `logs/app/YYYY-MM-DD.jsonl`. Dla BigQuery ustaw
`FORGE_LOG_BACKEND=bigquery`, `FORGE_BQ_PROJECT`, `FORGE_BQ_DATASET` oraz
opcjonalnie `FORGE_BQ_APP_LOG_TABLE` (domyślnie `app_logs`). Zależność jest
opcjonalna: `pip install -r requirements-bigquery.txt` (lub extra
`pip install -e .[bigquery]`).
Przy budowie obrazu GCP wskaż `--build-arg REQUIREMENTS_FILE=requirements-bigquery.txt`.
