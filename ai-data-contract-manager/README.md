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