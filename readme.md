# ADCM baseline

Minimalny, działający szkielet monorepo dla dwóch osobnych usług:

- `ai-data-contract-manager` — ADCM, właściciel sesji, mutacji, provenance, reguł ADCM i stabilizacji.
- `mcp-servers/mcp-contract-forge` — bezstanowy MCP Contract Forge, właściciel definicji i formalnej analizy kontraktu.

Usługi **nie importują kodu Pythona między sobą**. Granicą jest MCP + wersjonowany model JSON.
Każda usługa ma własny `pyproject.toml`, `requirements.txt`, Dockerfile i własne środowisko.

## Uruchomienie

Docker:

```bash
docker compose up --build
```

Lokalne, niezależne venv:

```bash
./scripts/bootstrap_local.sh
```

Skrypt tworzy osobne `.venv` w `ai-data-contract-manager` i `mcp-servers/mcp-contract-forge`; żadna usługa nie korzysta z venv drugiej.

ADCM: `http://localhost:8080`
Forge MCP: `http://localhost:8000/mcp`

Przykład:

```bash
curl -X POST http://localhost:8080/v1/sessions/demo/turn \
  -H 'Content-Type: application/json' \
  -d '{"message":"system sap"}'
```

Wersja bazowa ma heurystyczny resolver intencji, aby działała bez klucza LLM. Port `IntentResolverPort`
pozwala w następnej iteracji włączyć adapter PydanticAI bez zmiany core.

Zobacz `docs/ARCHITECTURE_BASELINE.md` i `docs/NEXT_ITERATIONS.md`.


## Weryfikacja bez Docker

```bash
./scripts/test_all.sh
```

Uruchamia testy obu serwisów osobno oraz serializuje odpowiedź Forge do JSON i waliduje ją modelem ADCM, bez wspólnych importów.
