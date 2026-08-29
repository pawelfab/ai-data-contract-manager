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