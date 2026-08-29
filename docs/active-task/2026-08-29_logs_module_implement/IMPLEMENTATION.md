---
status: active
created: 2026-08-29
completed:
---

# Implementation: moduł logowania ADCM i Contract Forge

## Implementation contract

Owning service: `ai-data-contract-manager` (ADCM) oraz `mcp-servers/mcp-contract-forge` (Forge) — dwa niezależne procesy, każdy z własnym `pyproject.toml` i `.venv`. Nie powstaje wspólny pakiet Python dla logowania.

Owning boundary: nowa warstwa obserwowalności w każdym serwisie osobno — porty w `ports/`, logika rekordowania w `application/observability/`, zapis w `adapters/logging/`. ADCM jest jedynym właścicielem session audit trail; Forge pozostaje bezstanowy i ma wyłącznie application logging.

Files expected to change:
- ADCM porty: `src/adcm/ports/app_log_sink.py`, `src/adcm/ports/session_audit_sink.py`
- ADCM application: `src/adcm/application/observability/{models,app_log_recorder,session_audit_recorder,sanitizer}.py`
- ADCM adaptery: `src/adcm/adapters/logging/{local,bigquery}_{app_log,session_audit}_sink.py`, `sanitizer.py`
- ADCM integracja: `src/adcm/adapters/api/app.py`, `src/adcm/application/turn_orchestrator.py`, `src/adcm/adapters/forge_mcp.py`, `src/adcm/domain/turn.py`, `src/adcm/ports/forge.py`
- Forge: `src/contract_forge/ports/app_log_sink.py`, `src/contract_forge/application/observability/`, `src/contract_forge/adapters/logging/`, `src/contract_forge/server.py`
- Zależności i uruchomienie: oba `pyproject.toml`, oba `requirements-bigquery.txt`, oba `Dockerfile`, `docker-compose.yml`

Files/services explicitly not to change:
- `adcm/domain/` poza minimalnym rozszerzeniem `turn.py` o korelację turn
- logika biznesowa `candidate_policy`, `proposal_reconciler`, `stabilization_engine` — dopuszczalne wyłącznie punkty emisji audytu, bez zmiany decyzji
- żaden import kodu Python pomiędzy ADCM a Forge

Main invariant: obserwowalność nigdy nie zmienia zachowania biznesowego. Awaria sinka nie może przerwać tury ani uszkodzić `ContractState`; `domain/`, `application/` i `ports/` nie znają BigQuery, plików ani bibliotek Google; brak BigQuery nie blokuje uruchomienia lokalnego.

Implementation approach: dwa rozdzielne porty (`AppLogSinkPort`, `SessionAuditSinkPort`) zamiast jednego `LoggerPort`, bo application log i session audit mają inny lifecycle i strukturę. Rekordery w warstwie application budują modele Pydantic i łykają wyjątki sinka. Wybór backendu (`local` / `bigquery`) następuje wyłącznie w kompozycji w `adapters/api/app.py` na podstawie zmiennych środowiskowych.

Tests:
- ADCM: `tests/test_logging_architecture.py`, `tests/test_observability.py`, `tests/test_turn_audit.py`, `tests/test_forge_mcp_adapter.py`, `tests/test_document_engine.py`
- Forge: `tests/test_logging_architecture.py`, `tests/test_observability.py`

Architecture risks:
- przeciek infrastruktury do rdzenia (import `google.cloud`, `pathlib`, `open()` w `application`/`domain`) — pilnowany testem architektonicznym
- wyciek sekretów i PII do logów — pilnowany sanitizerem po stronie application i ponownie w adapterze
- pokusa umieszczenia logiki biznesowej w rekorderze audytu

## Current behavior

Przed zmianą oba serwisy nie miały ustrukturyzowanego logowania. `TurnOrchestrator` prowadził turę (intent → candidates → mutacje → propozycje reguł i Forge → stabilizacja → odpowiedź) bez odtwarzalnego śladu decyzji, co uniemożliwiało debugowanie `IntentResolver`: nie dało się odtworzyć, które `MutationCandidate` powstały, które zostały przyjęte lub odrzucone i dlaczego proposal został zastosowany. `ForgeMcpAdapter` nie raportował przebiegu ani błędów wywołań MCP.

Granice opisane w `docs/ARCHITECTURE_BASELINE.md` i `docs/CORE_INVARIANTS.md` pozostają wiążące: ADCM jest właścicielem sesji, historii, mutacji i provenance; Forge jest bezstanowy, nie zna rozmowy i nie mutuje dokumentu.

## Planned changes

1. **Modele zdarzeń** (`application/observability/models.py`) — `AppLogEvent` i `SessionAuditEvent` jako Pydantic `BaseModel` z `extra="forbid"`, domyślnym `event_id`/`timestamp` i walidatorem wymuszającym timezone-aware UTC.
2. **Porty** — `AppLogSinkPort` i `SessionAuditSinkPort` jako `Protocol` z pojedynczą metodą `emit(event) -> None`. Celowo rozdzielone.
3. **Rekordery** — `AppLogRecorder` (poziomy, `service`/`environment`, skróty `info`/`error`) oraz `SessionAuditRecorder` z `bind(session_id, turn_no, correlation_id)` zwracającym `BoundTurnAuditRecorder`. Oba przechwytują wyjątki sinka: awaria application logu idzie na `stderr`, awaria audytu jest raportowana jako `session_audit_sink_failed` w application logu.
4. **Sanitizer** — redakcja kluczy sekretów, nagłówków `Bearer`/`Basic` i przypisań typu `api_key=...`. Stosowany w warstwie application (na komunikatach błędów) i ponownie w adapterach przed zapisem.
5. **Adaptery zapisu** — `LocalAppLogSink` / `LocalSessionAuditSink` piszące JSONL do `logs/{app,session}/YYYY-MM-DD.jsonl` pod blokadą wątkową, oraz warianty BigQuery. Zależność `google-cloud-bigquery` wydzielona do `requirements-bigquery.txt`, żeby lokalne uruchomienie jej nie wymagało.
6. **Kompozycja** — `_build_observability()` w `adapters/api/app.py` wybiera backend przez `ADCM_LOG_BACKEND` (`local`/`bigquery`) plus `ADCM_ENVIRONMENT`, `ADCM_LOG_DIR`, `ADCM_BQ_PROJECT`, `ADCM_BQ_DATASET`, `ADCM_BQ_APP_LOG_TABLE`, `ADCM_BQ_SESSION_AUDIT_TABLE`.
7. **Integracja z turą** — `TurnOrchestrator` przyjmuje opcjonalne `audit` i `app_log`; przez `_audit()` emituje ustabilizowany zbiór typów zdarzeń (`turn.started`, `user.message.received`, `intent.resolved`, `candidate.accepted|rejected|deferred`, `mutation.applied`, `forge.analysis.*`, `rule.proposal.generated`, `proposal.decision`, `stabilization.*`, `external_checks.completed`, `response.composed`, `turn.completed`, `turn.failed`). Oba są opcjonalne (`None`), więc istniejące testy i użycia bez obserwowalności działają bez zmian.
8. **Forge** — analogiczny, ale węższy zestaw: wyłącznie application logging w `server.py`, bez session audit, zgodnie z bezstanowością serwisu.
9. **Test architektoniczny** — `test_logging_architecture.py` w obu serwisach sprawdza, że w `domain/`, `application/` i `ports/` nie występuje `google.cloud`, `contract_forge`, `insert_rows_json`, a w `domain`/`application` dodatkowo `from pathlib import` ani `.open(`.

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

### Finding: bramka pre-commit wymaga IMPLEMENTATION.md, nie tylko TASK.md

Observation: `python scripts/agent/doc_freshness.py --check` zwracał `CURRENT`, ale `git commit` był blokowany jako `STALE`. To dwie różne kontrole — hook `githooks/pre-commit` uruchamia `--check-staged`, nie `--check`.

Affected assumption: założenie, że `--check` odzwierciedla stan bramki pre-commit. `--check` porównuje wyłącznie hashe źródeł ze znacznikiem `docs/.freshness.json`; `--check-staged` czyta indeks Gita i wymaga niezależnie curated doc **oraz** dokumentu zadania pasującego do `^docs/active-task/\d{4}-\d{2}-\d{2}_[^/]+/IMPLEMENTATION\.md$`.

Implementation impact: brak — dotyczy wyłącznie dokumentacji zadania, nie kodu modułu logowania. Katalog zadania zawierał sam `TASK.md`, który przechodzi jako curated evidence, ale celowo nie zaspokaja reguły „jeden dokument zadania na zmianę”.

Workaround complexity: żadna. Rozwiązaniem jest uzupełnienie brakującego pliku wymaganego przez `docs/active-task/README.md`.

Simpler corrective option: rozluźnienie `require_task_doc_for_staged_relevant_code` — odrzucone, bo osłabiłoby bramkę jakości dla całego repozytorium.

Decision: utworzono ten dokument i znormalizowano nazwę katalogu zadania z błędnej daty `2026-09-29` na `2026-08-29`. Rozważane doprecyzowanie różnicy `--check` / `--check-staged` w `scripts/agent/README.md`.

## Deviations from the original plan

`TASK.md` proponował modele w `adcm/domain/logging/`. Umieszczono je w `application/observability/models.py`, bo zdarzenia logowania są artefaktem obserwowalności aplikacji, a nie pojęciem domenowym kontraktu — trzymanie ich w `domain/` rozszerzałoby domenę o odpowiedzialność techniczną. Porty w `ports/` importują modele z warstwy application, a test architektoniczny nadal pilnuje braku infrastruktury w rdzeniu.

## Verification

- [ ] relevant unit tests pass
- [ ] relevant integration tests pass
- [ ] architecture/boundary tests pass when applicable
- [ ] configured quality gates pass
- [ ] documentation freshness reviewed
- [ ] `docs/generated/documentation-impact.md` reviewed
- [ ] required curated documentation updated

Komendy:

```bash
ai-data-contract-manager\.venv\Scripts\python.exe -m pytest ai-data-contract-manager\tests -q
mcp-servers\mcp-contract-forge\.venv\Scripts\python.exe -m pytest mcp-servers\mcp-contract-forge\tests -q
python scripts/agent/doc_freshness.py --check-staged
```

## Final result

Do uzupełnienia po zakończeniu zadania — opisać, co faktycznie zostało wdrożone.

## Unresolved items

- decyzja, czy doprecyzować różnicę `--check` / `--check-staged` w `scripts/agent/README.md`
- weryfikacja ścieżki BigQuery na realnym projekcie (dotąd testowana wyłącznie przez atrapy sinków)

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
8. move the entire task directory from `docs/active-task/2026-08-29_logs_module_implement/` to `docs/history/2026-08-29_logs_module_implement/`.
