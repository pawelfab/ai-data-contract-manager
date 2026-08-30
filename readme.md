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

Lokalne, niezależne venv — po jednym na usługę, żadna nie korzysta z venv drugiej:

```bash
python -m venv ai-data-contract-manager/.venv
ai-data-contract-manager/.venv/Scripts/python.exe -m pip install -r ai-data-contract-manager/requirements.txt -r ai-data-contract-manager/requirements-dev.txt
ai-data-contract-manager/.venv/Scripts/python.exe -m pip install -e ai-data-contract-manager

python -m venv mcp-servers/mcp-contract-forge/.venv
mcp-servers/mcp-contract-forge/.venv/Scripts/python.exe -m pip install -r mcp-servers/mcp-contract-forge/requirements.txt -r mcp-servers/mcp-contract-forge/requirements-dev.txt
mcp-servers/mcp-contract-forge/.venv/Scripts/python.exe -m pip install -e mcp-servers/mcp-contract-forge
```

Opcjonalny adapter PydanticAI: `ai-data-contract-manager/requirements-ai.txt`.

ADCM: `http://localhost:8080`
Forge MCP: `http://localhost:8000/mcp`

Przykład — sesję tworzy ADCM, klient nie wybiera identyfikatora:

```bash
SESSION=$(curl -sX POST http://localhost:8080/v1/sessions | jq -r .session_id)

curl -X POST http://localhost:8080/v1/sessions/$SESSION/turns \
  -H 'Content-Type: application/json' \
  -d '{"message":"system sap"}'

curl http://localhost:8080/v1/sessions/$SESSION
```

Pełny kontrakt REST API v1 oraz format błędów: `ai-data-contract-manager/README.md`
i OpenAPI pod `http://localhost:8080/docs`.

Wersja bazowa ma heurystyczny resolver intencji, aby działała bez klucza LLM. Port `IntentResolverPort`
pozwala w następnej iteracji włączyć adapter PydanticAI bez zmiany core.

Zobacz `docs/ARCHITECTURE_BASELINE.md` i `docs/NEXT_ITERATIONS.md`.


## Weryfikacja bez Docker

Testy obu usług, każda we własnym venv (te same komendy uruchamia `quality_gate.py --profile pre-push`):

```bash
ai-data-contract-manager/.venv/Scripts/python.exe -m pytest ai-data-contract-manager/tests -q
mcp-servers/mcp-contract-forge/.venv/Scripts/python.exe -m pytest mcp-servers/mcp-contract-forge/tests -q
```

albo zbiorczo:

```bash
python scripts/agent/quality_gate.py --profile pre-push
```

## Testy live (end-to-end)

`ai-data-contract-manager/tests/live/` rozmawia z **realnie uruchomionym** ADCM, który
woła **realnego** Contract Forge. Fixtury same startują obie usługi na wolnych portach
(przez `uvicorn`, bez Dockera) i gaszą je po przebiegu; logi idą do katalogu tymczasowego.
Asercje opierają się wyłącznie na publicznym kontrakcie REST v1.

Suita jest wyłączona z domyślnego przebiegu (`addopts = -m "not live and not llm"`),
więc `pytest ai-data-contract-manager/tests` nadal uruchamia tylko testy in-process.

Deterministycznie (bez LLM, `ADCM_INTENT_MODE=heuristic`):

```bash
ai-data-contract-manager/.venv/Scripts/python.exe -m pytest ai-data-contract-manager/tests/live -q -m live
```

albo jako stage quality gate:

```bash
python scripts/agent/quality_gate.py --stage system_test
```

Scenariusze zależne od prawdziwego LLM są **non-blocking** i wymagają jawnego wyboru.
Bez `OPENAI_BASE_URL`/`ADCM_MODEL`, albo przy niedostępnym endpoincie, dają `skip`:

```powershell
$env:OPENAI_BASE_URL = "http://localhost:3030/v1"
$env:ADCM_MODEL = "openai-chat:auto"
ai-data-contract-manager/.venv/Scripts/python.exe -m pytest ai-data-contract-manager/tests/live -q -m llm
```

`system_test` celowo **nie jest** wpięty w `pre-push`, żeby nie wydłużać każdego pusha.
Ceną jest to, że nic go nie wymusza — dlatego traktujemy go jako **krok wymagany przed
zamknięciem zadania**, obok `--profile pre-push`.

## Automatyka dokumentacji

`scripts/agent/` generuje mapę repozytorium i pilnuje świeżości dokumentacji; opis w `scripts/agent/README.md`.
Instalacja hooków Git: `python scripts/agent/install_git_hooks.py`.
