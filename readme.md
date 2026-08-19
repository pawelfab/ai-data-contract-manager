# ADCM monorepo

Repozytorium zawiera niezależnie instalowane i uruchamiane usługi:

```text
ai-data-contract-manager/
  src/adcm/                 # aplikacja, API, CLI i klient MCP
  tests/
  docs/
  pyproject.toml
mcp-servers/
  mcp-contract-forge/
    src/contract_forge/     # właściciel kontraktu i serwer MCP
    config/                 # contract.json i reguły enrichment/workflow
    contracts/              # dodatkowe artefakty kontraktu
    tests/
    docs/
    pyproject.toml
docs/                       # dokumentacja całego monorepo
```

Każda usługa ma własny manifest, środowisko `.venv`, zależności i testy. Korzeń
monorepo nie jest pakietem Pythona.

## Uruchomienie

Terminal 1:

```powershell
cd mcp-servers\mcp-contract-forge
.\.venv\Scripts\Activate.ps1
contract-forge-mcp
```

Terminal 2:

```powershell
cd ai-data-contract-manager
.\.venv\Scripts\Activate.ps1
adcm-cli
```

ADCM łączy się domyślnie z `http://127.0.0.1:8001/mcp`. Nie ma już trybu
`--local-forge`; granica MCP obowiązuje również w minimalnym uruchomieniu.

## Testy

```powershell
ai-data-contract-manager\.venv\Scripts\python.exe -m pytest ai-data-contract-manager\tests -q
mcp-servers\mcp-contract-forge\.venv\Scripts\python.exe -m pytest mcp-servers\mcp-contract-forge\tests -q
```

Dokumentacja architektury całego systemu znajduje się w [docs](docs/).
