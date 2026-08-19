# AI Data Contract Manager

ADCM jest usługą rozmowy i orkiestracji. Nie posiada schematu kontraktu ani reguł
enrichmentu i nie importuje pakietu `contract_forge`. Wszystkie operacje na
kanonicznym kontrakcie wykonuje przez Contract Forge MCP.

## Struktura

```text
src/adcm/
  api.py             # FastAPI
  cli.py             # klient terminalowy
  gateway.py         # klient MCP Streamable HTTP
  orchestrator.py    # deterministyczna pętla rozmowy
  heuristics.py      # parsowanie bez LLM
  semantic.py        # kontrolowany resolver Pydantic AI
  models.py          # modele aplikacji i DTO odpowiedzi Forge
tests/
docs/
scripts/smoke_demo.py
```

## Instalacja

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[openai,dev]"
Copy-Item .env.example .env
```

Konfiguracja lokalnego gatewaya OpenAI-compatible:

```dotenv
ADCM_LLM_MODE=pydantic
ADCM_LLM_PROVIDER=openai_compatible
ADCM_MODEL=auto
OPENAI_BASE_URL=http://127.0.0.1:3030/v1
OPENAI_API_KEY=local-gateway
```

## Uruchomienie

Najpierw uruchom osobny serwis `mcp-contract-forge`, a następnie:

```powershell
adcm-cli
# albo
adcm-api
```

Endpoint MCP można zmienić przez `ADCM_MCP_URL`. Tryb in-process
`--local-forge` został usunięty, aby pakiety pozostały niezależnymi usługami.

## Testy

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testy używają fałszywego gatewaya na granicy MCP; nie instalują ani nie importują
implementacji Contract Forge.
