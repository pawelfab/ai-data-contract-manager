---
status: completed
created: 2026-08-29
type: feature
services: [adcm]
---

# Task: Stable REST API v1

## Problem

Web UI ma być następną iteracją, ale zanim powstanie, ADCM musi mieć stabilny publiczny kontrakt HTTP.
Dzisiejszy adapter (`ai-data-contract-manager/src/adcm/adapters/api/app.py`, 178 linii) tego nie zapewnia.

1. **Modele domenowe są serializowane wprost jako kontrakt publiczny.**
   `POST /v1/sessions/{id}/turn` ma `response_model=TurnOutcome`, czyli wystawia pełny `ForgeAnalysis`
   (`writable[]` — kilkanaście deskryptorów pól, `foreign`, `proposals`), `StabilizationReport.proposal_decisions[]`
   oraz pełne `MutationEvent` (`mutation_id`, `producer_id`, `revision_before`, `revision_after`, `source`).
   `GET /v1/sessions/{id}` zwraca `SessionState`, czyli cały `mutation_log` i mapę `provenance`.
   Wewnętrzna architektura jest de facto publicznym kontraktem — każda zmiana modelu core staje się
   breaking change dla klienta.

2. **Unresolved intents giną między application a API.**
   `IntentResolution.unresolved` trafia wyłącznie do Session Audit (`intent.resolved`, `candidate.deferred`)
   i do licznika w app logu. `TurnOutcome` nie ma takiego pola, więc użytkownik, który napisze
   "włącz target bronze", dostaje wyłącznie informację o brakującym polu kontraktu i nigdy nie dowiaduje się,
   czego ADCM nie zrozumiał.

3. **Nie ma cyklu życia sesji.**
   Nie istnieje `POST /v1/sessions`; identyfikator wybiera klient jako path param.
   Zarówno `GET /v1/sessions/{id}`, jak i handler tury wołają `sessions.get_or_create(...)`,
   więc nieistniejąca sesja jest po cichu tworzona — `404` nie występuje nigdy, a Web UI nie ma
   sposobu odróżnienia literówki w identyfikatorze od pustej sesji.

4. **Kontrakt błędów jest niestabilny i wycieka internals.**
   Każdy wyjątek w handlerze tury → `HTTPException(status_code=502, detail=str(exc))`.
   Surowy tekst wyjątku (URL Forge, internals MCP, komunikaty biblioteczne) trafia do klienta bez sanityzacji.
   Nie ma typu `ForgeUnavailableError` — niedostępność Forge, błąd JSON Pointer i konflikt reguł
   dają identyczną odpowiedź `502`.

5. **Adapter jest nietestowalny.**
   Cała kompozycja dzieje się na poziomie modułu (linie 90–113): import `app.py` czyta ENV,
   tworzy sinki logów (zapis na dysk), `ForgeMcpAdapter` i `TurnOrchestrator`, a przy złym ENV
   rzuca `RuntimeError`. Dlatego dziś nie istnieje ani jeden test API.
   Narusza to guardrail 22 z `AGENTS.md` ("każdy istotny moduł musi być niezależnie testowalny").

6. **Brak guardrailu chroniącego core przed HTTP.**
   `tests/test_logging_architecture.py` sprawdza `google.cloud`, `contract_forge`, `insert_rows_json`,
   `pathlib` i `.open(`, ale **nie** `fastapi` — mimo że `docs/architecture-guardials.md` §19 tego wymaga.

## Goal

Jeden oficjalny adapter REST ADCM z jawnymi request/response DTO, wąskim kontraktem publicznym
zoptymalizowanym dla klienta i stabilnym formatem błędów.

Obserwowalny rezultat:

- można utworzyć sesję (`POST /v1/sessions`), a identyfikator generuje ADCM, nie klient;
- można wysłać wiele tur do tej samej sesji z zachowaniem stanu między requestami;
- można pobrać aktualny stan sesji bez wywoływania Forge;
- odpowiedź tury zawiera dokładnie to, co Web UI musi pokazać: `message`, `document`,
  `contract_status`, `missing`, `diagnostics`, `unresolved`, `changes`;
- nieistniejąca sesja daje `404` z ustandaryzowanym payloadem;
- niedostępny Forge daje `503` bez stack trace i bez internals;
- OpenAPI (`/docs`, `/openapi.json`) jest kompletne i może służyć jako kontrakt dla Web UI;
- `domain`, `application` i `ports` nie zależą od FastAPI, co chroni test architektury.

## Scope

Included:

- **Publiczne DTO API** — `adapters/api/models.py`: `HealthResponse`, `CreateSessionResponse`,
  `SessionStateResponse`, `TurnRequest`, `TurnResponse`, `ContractStatusView`, `MissingItem`,
  `DiagnosticItem`, `UnresolvedItem`, `ChangeItem`, `ErrorResponse`/`ErrorBody`.
- **Mappery** — `adapters/api/mappers.py`: czyste funkcje core model → DTO, bez I/O.
- **Kontrakt błędów** — `adapters/api/errors.py`: jeden payload `{"error": {code, message, correlation_id}}`,
  handlery dla `SessionNotFoundError` (404), `ForgeUnavailableError` (503), `RequestValidationError` (422),
  `HTTPException`, `Exception` (500); deklaracje `responses=` dla OpenAPI.
- **`create_app()`** — `adapters/api/app.py` bez side effects przy imporcie; wiring z ENV przeniesiony
  do `adapters/api/composition.py::build_app()`; entrypoint uvicorn na `--factory`.
- **Endpointy MVP** — `GET /health`, `POST /v1/sessions`, `GET /v1/sessions/{id}`,
  `POST /v1/sessions/{id}/turns` (canonical) + `POST /v1/sessions/{id}/turn` (deprecated alias,
  ten sam handler, ten sam kontrakt).
- **Opcjonalny debug endpoint** — `GET /v1/debug/sessions/{id}`, rejestrowany wyłącznie przy `ADCM_DEBUG_API=true`.
- **Cykl życia sesji** — `application/session_service.py` (`SessionService`), rozszerzenie
  `SessionRepositoryPort` o `get()`, implementacja w `InMemorySessionRepository`.
  API nie trzyma własnego słownika sesji.
- **Typy błędów core** — `domain/errors.py`: `AdcmError`, `SessionNotFoundError`, `ForgeUnavailableError`;
  `ForgeMcpAdapter` rzuca `ForgeUnavailableError` zamiast gołego `RuntimeError`.
- **Zachowanie unresolved** — `TurnOutcome.unresolved` (pole addytywne z defaultem), wypełniane
  przez `TurnOrchestrator` z `IntentResolution.unresolved`.
- **Tani `GET` stanu sesji** — `TurnSnapshot` rozszerzony o `contract_status`, `missing`, `diagnostics`
  (reużycie `ContractStatus` / `MissingRequirement` / `Diagnostic` z `domain/forge.py`).
- **Application logging HTTP** — `http_request_started` / `http_request_completed` / `http_request_failed`
  z `method`, `route`, `status_code`, `duration_ms`, `correlation_id`, `session_id`.
- **Testy** — `tests/test_api.py` (TestClient, ~16 przypadków z §23 zadania) oraz
  `tests/test_api_architecture.py` (guardrail: brak `fastapi`/`starlette`/`HTTPException` w core).
- **Dokumentacja** — synchronizacja `CURRENT_STATE.md`, `ARCHITECTURE_BASELINE.md`,
  `MODULE_CONTRACTS.md`, `CORE_INVARIANTS.md`, `logging-architecture.md`, README, Dockerfile, compose.

## Out of scope

- Web UI w dowolnej formie: HTML, React, Vue, szablony Jinja, frontend assets.
- Authentication, OAuth, IAM, autoryzacja debug endpointu, API gateway, rate limiting.
- CORS (również "minimalna konfiguracja na później").
- SSE, WebSockets, token streaming, background jobs, async queue.
- Persistence sesji: Redis, Postgres, Firestore, BigQuery session storage; TTL/eviction sesji;
  optimistic concurrency w `InMemorySessionRepository`.
- Endpointy `DELETE /v1/sessions/{id}`, `GET /v1/sessions/{id}/history`, `GET /v1/sessions/{id}/audit`.
- Mechanizm wielu wersji API (prefix `/v1/` wystarcza).
- Zmiany logiki biznesowej: `IntentResolver` (w tym kształt `unresolved`), `ExplicitSyntaxResolver`,
  `CandidatePolicy`, `DocumentEngine`, `ProposalReconciler`, `ConventionRulesEngine`,
  semantyka `StabilizationEngine`, `BasicResponseComposer`, `ux_rules.json`.
- Zmiany `ForgeAnalysis` i semantyki Contract Forge; jakiekolwiek zmiany w `mcp-servers/mcp-contract-forge/`.
- Nowy Session Audit: envelope, katalog `event_type`, payloady, poziomy `ADCM_AUDIT_LEVEL`.
- Naprawa istniejącej dwukierunkowej zależności `ports/*_sink.py` ↔ `application/observability/models.py`.
- Naprawa `mcp-contract-forge` (brak `.venv` w drzewie, zależny od cwd `FORGE_CONTRACT_PATH`).

## Constraints

- **Core impact = minimal, wyłącznie addytywny.** Dopuszczalne: nowe pola z wartością domyślną,
  nowy plik `domain/errors.py`, nowy `SessionService`, jedna metoda w `SessionRepositoryPort`.
  Niedopuszczalne: zmiana istniejących pól, zmiana kolejności wywołań w `TurnOrchestrator`,
  zmiana `ForgeAnalysis`.
- **Wszystkie istniejące testy ADCM i Forge muszą przejść bez modyfikacji.** Jeżeli którykolwiek
  istniejący test wymaga zmiany, to sygnał, że zmiana w core nie jest addytywna — zatrzymać się
  i zapisać finding w `IMPLEMENTATION.md`.
- **Zachowanie biznesowe tury pozostaje identyczne.** Ta sama sekwencja: describe → intent →
  candidate policy → user mutations → stabilization → external checks → response → save.
  Te same zdarzenia Session Audit w tej samej kolejności.
- **`domain`, `application`, `ports` nie mogą importować `fastapi`, `starlette` ani `HTTPException`.**
  HTTP jest szczegółem adaptera (`docs/architecture-guardials.md` §3, §19).
- **API nie zawiera logiki biznesowej.** Handler wykonuje wyłącznie: walidację → mapowanie do wejścia
  application → wywołanie application → mapowanie wyjścia → odpowiedź HTTP.
  API nie modyfikuje `ContractState`, nie interpretuje wiadomości, nie wykonuje reguł,
  nie wywołuje Forge poza orchestratorem, nie zna `contract.json`, nie decyduje o authority/provenance,
  nie implementuje fixed-point.
- **API nie zapisuje biznesowych zdarzeń Session Audit** (`intent.resolved`, `mutation.applied`,
  `proposal.decision`). Może emitować wyłącznie techniczny HTTP application log.
- **Nie budować drugiego API obok istniejącego** — rozszerzyć/zrefaktoryzować obecny adapter.
- **`correlation_id` pozostaje wyłącznie metadanymi technicznymi** (`docs/CORE_INVARIANTS.md` #15)
  i nie może być używany jako identyfikator sesji.
- **Konwencja nazw zdarzeń app logu pozostaje snake_case.** Notacja z kropkami jest w tym repo
  zarezerwowana dla Session Audit `event_type` (`docs/logging-architecture.md`).
- Brak zmian w plikach chronionych z `scripts/agent/config.json` (`AGENTS.md`, `scripts/agent/`,
  `.github/`, `.claude/`, `githooks/`).

Constraints control expected scope, but they are not proof that an input, contract, schema or assumption is correct. If preserving a constraint requires disproportionate workaround complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [ ] 1. Istnieje jeden oficjalny REST API adapter ADCM — nie powstało drugie API obok istniejącego.
- [ ] 2. Można utworzyć sesję: `POST /v1/sessions` → `201` z `session_id` wygenerowanym po stronie ADCM,
      `turn_no = 0`, `status = "created"`.
- [ ] 3. Można wysłać wiele tur do tej samej sesji: `turn_no` rośnie, dokument z poprzedniej tury
      jest zachowany.
- [ ] 4. Można pobrać aktualny stan sesji: `GET /v1/sessions/{id}` zwraca `document`, `contract_status`,
      `missing`, `diagnostics` bez wywołania Contract Forge.
- [ ] 5. Web UI nie potrzebuje bezpośredniego dostępu do core — cztery endpointy MVP wystarczają.
- [ ] 6. API nie zawiera logiki domenowej — handlery ograniczone do walidacji, wywołania application
      i mapowania.
- [ ] 7. API nie zwraca domyślnie całego `ForgeAnalysis` — `writable`, `foreign`, `proposals`,
      `stabilization`, `external_checks`, `provenance`, `mutation_log` nie występują w publicznej odpowiedzi.
- [ ] 8. Unresolved intents nie są gubione — `unresolved` z `IntentResolver` jest obecne w odpowiedzi tury.
- [ ] 9. Błędy mają stabilny format JSON `{"error": {"code", "message", "correlation_id"}}`;
      nieistniejąca sesja → `404 session_not_found` dla `GET` i dla `POST .../turns`.
- [ ] 10. Błędy infrastrukturalne nie ujawniają internals — niedostępny Forge →
      `503 contract_forge_unavailable`, bez stack trace, URL Forge, szczegółów MCP i credentials;
      szczegóły techniczne pozostają w application logu.
- [ ] 11. OpenAPI jest poprawne — `/openapi.json` zawiera wszystkie endpointy z jawnymi modelami
      request/response, `/turn` oznaczony jako `deprecated`, `/docs` renderuje się poprawnie.
- [ ] 12. `domain`, `application` i `ports` nie zależą od FastAPI — potwierdzone testem architektury.
- [ ] 13. Istniejące zachowanie biznesowe pozostaje bez zmian — sekwencja tury i zdarzenia
      Session Audit identyczne.
- [ ] 14. Wszystkie testy przechodzą — istniejące bez modyfikacji plus nowe testy API i guardrail.
- [ ] 15. Błędny request (`{}`, `{"message": ""}`, `{"message": "   "}`, nadmiarowe pole) daje `4xx`
      przez walidację Pydantic/FastAPI, bez ręcznej warstwy walidacji.
- [ ] 16. `POST /v1/sessions/{id}/turn` nadal działa jako deprecated alias zwracający ten sam
      nowy kontrakt co `/turns`.

## Relevant references

- issue/ticket: —
- prior task/decision: `docs/history/2026-08-29_compact-session-audit/`,
  `docs/history/2026-08-29_logs_module_implement/`, `docs/history/planning/stages/stage-01.md`
- documentation: `docs/ARCHITECTURE_BASELINE.md`, `docs/CORE_INVARIANTS.md`,
  `docs/MODULE_CONTRACTS.md`, `docs/architecture-guardials.md` (§3, §14, §18, §19),
  `docs/logging-architecture.md`, `AGENTS.md` (guardrails 3, 5, 22, 23)
