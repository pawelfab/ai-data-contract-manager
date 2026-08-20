# MCP Contract Forge

Contract Forge jest samodzielnym serwisem MCP i właścicielem kanonicznego kontraktu.
Zawiera schemat, reguły enrichmentu/workflow, walidację i stan sesji Forge.

## Struktura

```text
src/contract_forge/
  contracts/        # port źródła kontraktu + adaptery
  compiler.py       # walidacja definicji -> CompiledContract
  contract_rules.py # wykonanie x-contract-rules
config/
  contract.json
  ux_rules_contract_v1.json
  ux_rules_original.json
tests/
docs/
```

Reguły biznesowe kontraktu opisuje [docs/CONTRACT_RULES.md](docs/CONTRACT_RULES.md).
Kontrakt z nieznanym `kind` lub operatorem jest odrzucany przy starcie serwera.

## Instalacja i uruchomienie

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
contract-forge-mcp
```

Domyślny endpoint to `http://127.0.0.1:8001/mcp`. Konfigurację można zmienić
zmiennymi opisanymi w `.env.example`.

## Testy

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testy Forge nie importują ADCM.
