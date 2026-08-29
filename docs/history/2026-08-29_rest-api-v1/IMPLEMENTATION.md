---
status: completed
created: 2026-08-29
completed: 2026-08-29
---

# Implementation: Stable REST API v1

## Implementation contract

Owning service: `ai-data-contract-manager` (ADCM)

Owning boundary: `adapters/api` — adapter wejściowy do istniejącej warstwy application.
Nie powstaje `WebPort`; API jest adapterem, nie portem.

Files expected to change:

- `ai-data-contract-manager/src/adcm/adapters/api/app.py` — refaktor do `create_app(...)`, route'y, middleware
- `ai-data-contract-manager/src/adcm/adapters/api/models.py` — **nowy**, publiczne DTO
- `ai-data-contract-manager/src/adcm/adapters/api/mappers.py` — **nowy**, core → DTO
- `ai-data-contract-manager/src/adcm/adapters/api/errors.py` — **nowy**, kontrakt błędów + handlery
- `ai-data-contract-manager/src/adcm/adapters/api/composition.py` — **nowy**, `build_app()` z ENV
- `ai-data-contract-manager/src/adcm/application/session_service.py` — **nowy**, cykl życia sesji
- `ai-data-contract-manager/src/adcm/domain/errors.py` — **nowy**, `AdcmError` / `SessionNotFoundError` / `ForgeUnavailableError`
- `ai-data-contract-manager/src/adcm/domain/session.py` — `TurnSnapshot` + `contract_status`/`missing`/`diagnostics`
- `ai-data-contract-manager/src/adcm/domain/turn.py` — `TurnOutcome` + `unresolved`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py` — wypełnienie dwóch nowych pól
- `ai-data-contract-manager/src/adcm/ports/session_repository.py` — `get()` w `Protocol`
- `ai-data-contract-manager/src/adcm/adapters/session_memory.py` — implementacja `get()`
- `ai-data-contract-manager/src/adcm/adapters/forge_mcp.py` — `ForgeUnavailableError` zamiast `RuntimeError`
- `ai-data-contract-manager/tests/test_api.py` — **nowy**
- `ai-data-contract-manager/tests/test_api_architecture.py` — **nowy**
- `ai-data-contract-manager/Dockerfile`, `docker-compose.yml` — entrypoint `--factory`
- `README.md`, `ai-data-contract-manager/README.md` — polecenie uruchomienia i smoke
- `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE_BASELINE.md`, `docs/MODULE_CONTRACTS.md`,
  `docs/CORE_INVARIANTS.md`, `docs/logging-architecture.md`

Files/services explicitly not to change:

- `mcp-servers/mcp-contract-forge/**` — cały serwis Forge
- `ai-data-contract-manager/resources/ux_rules.json`
- `src/adcm/domain/forge.py` (`ForgeAnalysis` i modele składowe — wyłącznie reużycie)
- `src/adcm/domain/mutations.py`, `src/adcm/domain/provenance.py`, `src/adcm/domain/contract.py`
- `src/adcm/application/document_engine.py`, `stabilization_engine.py`, `proposal_reconciler.py`,
  `rules_engine.py`, `candidate_policy.py`, `external_check_coordinator.py`
- `src/adcm/application/observability/**` (audit views, recordery, sanitizer, modele zdarzeń)
- `src/adcm/adapters/response_basic.py`, `intent_heuristic.py`, `intent_pydantic_ai.py`
- `src/adcm/adapters/logging/**`
- Wszystkie istniejące pliki w `ai-data-contract-manager/tests/`
- Pliki chronione z `scripts/agent/config.json`: `AGENTS.md`, `scripts/agent/`, `.github/`,
  `.claude/`, `.vscode/`, `githooks/`, `.codex/`

Main invariant:

> API nie zawiera logiki domenowej i nie serializuje modeli domenowych jako kontraktu publicznego;
> `domain`, `application` i `ports` nie znają FastAPI.

Wtórnie: zachowanie biznesowe tury (sekwencja wywołań, zdarzenia Session Audit, wynik stabilizacji)
pozostaje bit-w-bit takie samo — zmiany są addytywne.

Implementation approach:

Cztery kroki w kolejności: (0) dokumentacja zadania, (1) addytywne zmiany w core,
(2) adapter API, (3) testy, (4) synchronizacja dokumentacji.
Krok 1 jest celowo pierwszy i minimalny — dostarcza dokładnie te trzy rzeczy, których adapter
nie może sobie sam zbudować bez wchodzenia w logikę domenową: typ błędu niedostępności Forge,
zachowany `unresolved` oraz tani odczyt statusu ostatniej tury.

Kluczowa decyzja projektowa (podjęta z użytkownikiem): stan sesji **nie** dostaje pola
`last_analysis: ForgeAnalysis`. To zbyt mocno wiązałoby `SessionState` z wewnętrznym modelem Forge
i przechowywało dużo niepotrzebnych danych (`writable[]`, `proposals[]`). Zamiast tego `TurnSnapshot`
zyskuje kompaktowy wynik formalnej oceny tego konkretnego stanu dokumentu:

```text
TurnOrchestrator
    ↓
final ForgeAnalysis
    ↓
TurnSnapshot(document, contract_status, missing, diagnostics)
    ↓
SessionState.snapshots
    ↓
GET /v1/sessions/{id}   (tani, deterministyczny, działa przy niedostępnym Forge)
```

Zasada: `TurnSnapshot` = stan dokumentu + wynik formalnej oceny tego stanu.

Tests:

- `tests/test_api.py` — TestClient na `create_app(...)` z fake'ami (bez ENV, bez dysku, bez MCP):
  tworzenie sesji, odczyt stanu, 404 na nieznanej sesji (GET i POST), pojedyncza tura,
  wiele tur z zachowaniem stanu, `unresolved` w odpowiedzi, `complete=true`, `changes`,
  `503` przy `ForgeUnavailableError`, walidacja `4xx`, `/health`, alias `/turn`,
  wąskość kontraktu (brak `forge`/`stabilization`/`new_events`/`mutation_log`/`provenance`),
  OpenAPI, debug endpoint on/off.
- `tests/test_api_architecture.py` — guardrail: brak `fastapi`, `starlette`, `HTTPException`
  w `domain`, `application`, `ports`.
- Regresja: wszystkie istniejące testy ADCM bez modyfikacji.

Architecture risks:

1. **Ryzyko przecieku HTTP do core.** Mitygacja: `domain/errors.py` bez zależności, guardrail test.
2. **Ryzyko rozrostu `TurnSnapshot`.** Mitygacja: tylko trzy pola, reużycie istniejących modeli
   z `domain/forge.py`, brak `writable`/`proposals`.
3. **Ryzyko zmiany zachowania przy przenoszeniu kompozycji do `composition.py`.**
   Mitygacja: przeniesienie bez zmiany logiki; ten sam zestaw ENV, ta sama kolejność budowy.
4. **Ryzyko zerwania uruchomienia lokalnego/Docker** przez zmianę entrypointu na `--factory`.
   Mitygacja: równoczesna aktualizacja Dockerfile, compose i obu README + smoke ręczny.
5. **Ryzyko, że `ForgeUnavailableError` przykryje błędy protokołu.** Mitygacja: błędy
   `model_validate` celowo nie są opakowywane — propagują jako `500 internal_error`.

## Current behavior

Opis dotyczy wyłącznie fragmentów istotnych dla zadania.

`src/adcm/adapters/api/app.py` (178 linii) zawiera całość adaptera: jedyne DTO (`TurnRequest`),
kompozycję na poziomie modułu (linie 90–113), middleware logujące i trzy endpointy:

| endpoint | model odpowiedzi | zachowanie |
|---|---|---|
| `GET /health` | `dict[str, str]` | `{"status": "ok"}`, bez `service` |
| `POST /v1/sessions/{id}/turn` | `TurnOutcome` (domain) | każdy wyjątek → `HTTPException(502, detail=str(exc))` |
| `GET /v1/sessions/{id}` | `SessionState` (domain) | `sessions.get_or_create(...)` — nigdy 404, auto-create |

`TurnOutcome` (`domain/turn.py`) niesie `forge: ForgeAnalysis`, `external_checks`,
`new_events: list[MutationEvent]`, `stabilization: StabilizationReport` — wszystko to jest dziś
serializowane do klienta. `SessionState` (`domain/session.py`) niesie `contract: ContractState`
z `provenance` i `mutation_log`.

`TurnOrchestrator.run_turn` (`application/turn_orchestrator.py:49`) generuje `correlation_id`
(albo przyjmuje z API), wiąże Session Audit przez `audit.bind(session_id, turn_no, correlation_id)`
i buduje wynik w liniach 133–152. `resolution.unresolved` jest w liniach 105 i 113–114 kierowane
wyłącznie do audytu; do `TurnOutcome` nie trafia.

`TurnSnapshot` (`domain/session.py`) ma dziś wyłącznie `turn_no`, `revision`, `document` —
jedyne miejsce konstrukcji to `turn_orchestrator.py:134`.

`SessionRepositoryPort` (`ports/session_repository.py`) deklaruje `get_or_create` i `save`;
brak metody odczytu bez tworzenia. `InMemorySessionRepository` trzyma `dict` pod `asyncio.Lock`
z `deepcopy` na wejściu i wyjściu.

`ForgeMcpAdapter` (`adapters/forge_mcp.py:24,26,53,55`) rzuca gołe `RuntimeError` przy błędzie
narzędzia MCP i braku `structured_content`; błędy transportowe propagują jako wyjątki biblioteki MCP.

Istniejący guardrail `tests/test_logging_architecture.py` skanuje `domain`, `application`, `ports`
pod kątem `google.cloud`, `contract_forge`, `insert_rows_json`, `pathlib`, `.open(` — bez `fastapi`.

## Planned changes

1. **Krok 0 — dokumentacja zadania.** `docs/active-task/2026-08-29_rest-api-v1/{TASK,IMPLEMENTATION}.md`
   (ten katalog). Wymagane przez pre-commit doc gate przed jakąkolwiek zmianą kodu.

2. **Krok 1 — core, addytywnie.**
   1. `domain/errors.py` — `AdcmError`, `SessionNotFoundError`, `ForgeUnavailableError` (bez zależności).
   2. `domain/session.py` — `TurnSnapshot` + `contract_status: ContractStatus`,
      `missing: list[MissingRequirement]`, `diagnostics: list[Diagnostic]` (reużycie `domain/forge.py`).
   3. `domain/turn.py` — `TurnOutcome.unresolved: list[dict[str, Any]]` z defaultem.
   4. `application/turn_orchestrator.py` — wypełnienie obu powyższych z `forge_analysis`
      i `resolution.unresolved`; bez zmiany kolejności etapów.
   5. `ports/session_repository.py` — `async def get(self, session_id) -> SessionState | None`.
   6. `adapters/session_memory.py` — implementacja `get()`.
   7. `application/session_service.py` — `SessionService.create()` / `.get()`;
      to on jest właścicielem formatu identyfikatora, nie API.
   8. `adapters/forge_mcp.py` — `ForgeUnavailableError` dla błędów narzędzia, braku
      `structured_content` i błędów transportowych; błędy `model_validate` bez zmian.

3. **Krok 2 — adapter API.** `models.py`, `mappers.py`, `errors.py`, refaktor `app.py`
   do `create_app(...)`, `composition.py` z `build_app()`; route'y MVP + deprecated alias
   + warunkowy debug endpoint; middleware z trzema zdarzeniami HTTP; entrypoint `--factory`.

4. **Krok 3 — testy.** `tests/test_api.py`, `tests/test_api_architecture.py`, regresja.

5. **Krok 4 — dokumentacja.** Synchronizacja pięciu curated docs, README, Dockerfile, compose;
   `scripts/agent/documentation_update.py`, `doc_freshness.py --mark-current`.

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

### Finding: zawinięcie wyjątku Forge gubiło pierwotną przyczynę z logów

Observation: Po zamianie gołego `RuntimeError` na `raise ForgeUnavailableError(_UNAVAILABLE) from exc`
w `ForgeMcpAdapter`, `str(exc)` widziany dalej w łańcuchu to już tylko ogólne
„Contract Forge is unavailable”. `TurnOrchestrator` loguje `turn_failed` z `message=str(exc)`,
a `ForgeMcpAdapter._error` logował wyłącznie `error_type`. Pierwotna przyczyna
(np. odmowa połączenia z konkretnym adresem) znikała z application logu.

Affected assumption: „opakowanie wyjątku dotyczy tylko odpowiedzi HTTP, logi zostają bez zmian”.
W rzeczywistości opakowanie zmieniało również to, co widzą logi.

Implementation impact: Bez korekty spełnilibyśmy §13 w połowie — klient przestałby dostawać
internals, ale diagnostyka też straciłaby dostęp do przyczyny. Potwierdzone smoke testem:
przy zatrzymanym Forge `contract_forge_unavailable` niósł wyłącznie ogólny komunikat.

Workaround complexity: znikoma — jedna linia.

Simpler corrective option: dodać `message=str(exc)` do `ForgeMcpAdapter._error`, czyli zapisać
pierwotny wyjątek w miejscu, w którym jest jeszcze dostępny.

Decision: Zastosowano prostszą opcję. Zdarzenie `forge_call_failed` niesie teraz pełny komunikat
oryginalnego wyjątku; odpowiedź HTTP pozostaje ogólna. Szczegóły techniczne wracają do
application logu, zgodnie z §13 zadania.

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many special cases, non-obvious transformations or changes across unrelated components, stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema, configuration or protected file.

## Deviations from the original plan

Record only material deviations and why they were necessary.

### Deviation: nazwy zdarzeń HTTP w application logu

Zadanie (§15) proponuje `http.request.started` / `http.request.completed` / `http.request.failed`.
W tym repo notacja z kropkami jest zarezerwowana dla Session Audit `event_type`, a application log
używa wyłącznie snake_case (`docs/logging-architecture.md`, obecne `http_request` / `http_response`).
Zachowano konwencję repo przy zachowaniu semantyki trzech zdarzeń:
`http_request_started` / `http_request_completed` / `http_request_failed`.

## Verification

- [x] relevant unit tests pass — **55 passed** (32 istniejące **bez modyfikacji** + 23 nowe:
      21 w `test_api.py`, 1 guardrail, licząc parametryzacje payloadów walidacji jako jeden test)
- [x] relevant integration tests pass — smoke ręczny na uruchomionych ADCM + Contract Forge
      (sekcja „Smoke test” poniżej)
- [x] architecture/boundary tests pass — `test_api_architecture.py` (brak `fastapi`/`starlette`/
      `HTTPException` w `domain`/`application`/`ports`) oraz istniejący `test_logging_architecture.py`
- [x] configured quality gates pass — ADCM 55 passed; Contract Forge 12 passed uruchomione
      z katalogu usługi (patrz „Unresolved items”)
- [x] documentation freshness reviewed — `doc_freshness.py --check` → `CURRENT`
- [x] `docs/generated/documentation-impact.md` reviewed — wskazał cztery curated docs,
      wszystkie zaktualizowane
- [x] required curated documentation updated — `CURRENT_STATE.md`, `ARCHITECTURE_BASELINE.md`,
      `MODULE_CONTRACTS.md`, `CORE_INVARIANTS.md` oraz dodatkowo `logging-architecture.md`
      i `logging-implementation-guide.md` (nowe nazwy zdarzeń HTTP)

### Smoke test

Contract Forge na `127.0.0.1:8000`, ADCM uruchomiony przez
`uvicorn --factory adcm.adapters.api.composition:build_app`.

| krok | wynik |
|---|---|
| `POST /v1/sessions` | `201 {"session_id":"91f51ff6…","turn_no":0,"status":"created"}` |
| tura 1 `/metadata/sourceSystemGcpId = sap` | `turn_no=1`; `changes` = 8 pozycji (wartość użytkownika + 7 z reguł konwencji i fixed-point) |
| tura 2 `/metadata/dataFileId = sap_id` | `turn_no=2`; dokument z tury 1 zachowany; `changes` = 1 pozycja |
| tura 3 `/metadata/sourceSystemGcpId = rocket` | `changes` z `operation: replace` oraz `old_value`/`new_value`, a także `remove` dla wycofanych wartości pochodnych |
| `GET /v1/sessions/{id}` | `turn_no=3`, dokument i `contract_status` spójne z ostatnią turą |
| `GET /v1/sessions/nieistniejaca` | `404 {"error":{"code":"session_not_found",…}}` |
| `POST /v1/sessions/nieistniejaca/turns` | `404`, sesja **nie** została utworzona |
| `{"message":""}` oraz `{}` | `422 validation_error` |
| `POST …/turn` (alias) | `200`, ten sam kontrakt, w OpenAPI `deprecated: true` |
| Forge zatrzymany → tura | `503 contract_forge_unavailable`, bez stack trace i bez adresu Forge |
| Forge zatrzymany → `/health` i `GET /v1/sessions/{id}` | nadal `200` — nie dotykają Forge |
| `/docs`, `/openapi.json` | `200`; ścieżki, `TurnResponse`, `ErrorResponse`, `responses` 404/422/500/503 obecne |
| `GET /v1/debug/sessions/{id}` | `200` przy `ADCM_DEBUG_API=true`, `404` bez flagi |

Application log po smoke: `http_request_started` ×22, `http_request_completed` ×22,
`route` jako wzorzec ścieżki (`/v1/sessions/{session_id}/turns`), obecne `session_id`,
`correlation_id`, `duration_ms`, `status_code`. Treść wiadomości użytkownika **nie**
wystąpiła w application logu.

## Final result

Zaimplementowano stabilne REST API v1 jako jedyny oficjalny interfejs wejściowy ADCM.

Adapter (`adapters/api/`) rozdzielono na pięć modułów: `models.py` (publiczne DTO),
`mappers.py` (core → DTO), `errors.py` (kontrakt błędu i handlery), `app.py`
(`create_app` + route'y) oraz `composition.py` (`build_app`, jedyne miejsce czytające ENV).
Import modułów adaptera nie ma efektów ubocznych, dzięki czemu cały adapter jest
testowalny bez ENV, MCP i dysku — to odblokowało pierwsze w historii repo testy API.

Endpointy: `GET /health`, `POST /v1/sessions`, `GET /v1/sessions/{id}`,
`POST /v1/sessions/{id}/turns` (canonical), `POST /v1/sessions/{id}/turn`
(deprecated alias na tym samym handlerze) oraz warunkowy `GET /v1/debug/sessions/{id}`.

Kontrakt publiczny zawężono do tego, co potrzebne klientowi: `message`, `document`,
`contract_status`, `missing`, `diagnostics`, `unresolved`, `changes`, `correlation_id`.
`ForgeAnalysis`, przebieg stabilizacji, `external_checks`, `provenance` i `mutation_log`
przestały być serializowane do klienta.

Zmiany w core okazały się wystarczające w zakresie zaplanowanym jako addytywny:
`domain/errors.py` (3 klasy), trzy pola w `TurnSnapshot`, jedno pole w `TurnOutcome`,
`SessionService`, jedna metoda w `SessionRepositoryPort` i jej implementacja,
typowany błąd w `ForgeMcpAdapter`. `TurnOrchestrator` zyskał dokładnie dwie zmiany
w bloku budującym wynik — kolejność etapów, audyt i logi pozostały nietknięte.
Wszystkie 32 istniejące testy przeszły bez żadnej modyfikacji, co potwierdza brak
zmiany zachowania biznesowego.

Decyzja projektowa użytkownika — `TurnSnapshot` zamiast `SessionState.last_analysis` —
okazała się trafna także funkcjonalnie: `GET /v1/sessions/{id}` działa przy zatrzymanym
Contract Forge, co potwierdzono w smoke teście.

## Unresolved items

- **Sesje pozostają in-memory, per proces.** Restart lub druga replika gubi stan.
  Persistence jest osobną iteracją (§10 zadania).
- **`unresolved` ma nieustalony kształt w core.** `IntentResolution.unresolved` to
  `list[dict[str, Any]]`; resolver heurystyczny używa klucza `value`, przykład z zadania
  mówi o `intent`. Mapper akceptuje `intent`/`value`/`text`/`phrase`/`message` zamiast
  wymuszać zmianę resolvera, która była poza zakresem (§7).
- **`HeuristicIntentResolver` nie wypełnia `unresolved`.** Dla nierozpoznanej wypowiedzi
  zwraca `knowledge_query`, które core ignoruje. API poprawnie przenosi `unresolved`
  (potwierdzone testami), ale w trybie heurystycznym pole bywa puste mimo niezrozumienia.
  Naprawa należy do `IntentResolver` — poza zakresem tego zadania.
- **Test Forge `test_correlation_id_is_technical_metadata_only` zależy od cwd.**
  `FORGE_CONTRACT_PATH` ma domyślnie ścieżkę względną, więc test przechodzi uruchomiony
  z katalogu usługi (12 passed), a pada z katalogu głównego repo. Problem sprzed tego
  zadania, niezwiązany ze zmianami w ADCM.
- **`InMemorySessionRepository` nie ma optimistic concurrency.** Dwie równoległe tury na
  tej samej sesji to last-write-wins. Stan sprzed tego zadania.
- **Zmiana entrypointu wymaga uwagi przy wdrożeniu.** `uvicorn adcm.adapters.api.app:app`
  już nie działa; obowiązuje `uvicorn --factory adcm.adapters.api.composition:build_app`.
  Zaktualizowano Dockerfile i oba README; zewnętrzne skrypty wdrożeniowe (jeśli istnieją
  poza repo) wymagają tej samej korekty.

## Completion procedure

Before declaring this task complete:

1. run relevant tests and repository quality gates;
2. verify documentation freshness;
3. review `docs/generated/documentation-impact.md`;
4. update only curated documents whose responsibility or documented behavior changed;
5. record the final implementation result, deviations and unresolved items above;
6. change this document metadata to:

```yaml
status: completed
completed: YYYY-MM-DD
```

7. update `TASK.md` status to `completed`;
8. move the entire task directory from:

`docs/active-task/2026-08-29_rest-api-v1/`

to:

`docs/history/2026-08-29_rest-api-v1/`

Do not leave completed task documentation in `docs/active-task/`.

Wykonane 2026-08-29: kroki 1–5 udokumentowane w sekcjach `Verification`, `Final result`
i `Unresolved items`; front matter obu dokumentów ustawiony na `completed`; katalog
przeniesiony do `docs/history/`. Skrypty w `scripts/agent/` nie przenoszą katalogów
zadań — walidują jedynie obecność dokumentu zadania, więc krok 8 jest zawsze manualny.
