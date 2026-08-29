---
status: active
created: 2026-08-29
completed:
---

# Implementation: Compact Session Audit

## Implementation contract

Owning service: `adcm`

Owning boundary: `application/observability` (mapowanie core → session audit view)

Files expected to change:
- `ai-data-contract-manager/src/adcm/application/observability/audit_views.py` (nowy)
- `ai-data-contract-manager/src/adcm/application/observability/session_audit_recorder.py`
- `ai-data-contract-manager/src/adcm/application/stabilization_engine.py` (tylko `_analyze`)
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py` (tylko payload `turn.completed`)
- `ai-data-contract-manager/src/adcm/adapters/api/app.py` (`ADCM_AUDIT_LEVEL`)
- `ai-data-contract-manager/tests/test_audit_compact.py` (nowy)
- `docs/logging-architecture.md`, `docs/logging-implementation-guide.md`

Files/services explicitly not to change:
- `src/adcm/domain/**` — `ForgeAnalysis`, `StabilizationReport`, `IntentResolution`,
  `MutationEvent`, `ProposalDecision`
- `application/candidate_policy.py`, `document_engine.py`, `proposal_reconciler.py`,
  `rules_engine.py`, `external_check_coordinator.py`
- pętla fixed-point w `stabilization_engine.py` (`stabilize()`)
- `mcp-servers/mcp-contract-forge/**`
- istniejące testy

Main invariant: audyt jest **widokiem** faktów domenowych, nie ich kopią. Zmiana
dotyka wyłącznie kształtu pola `data` dwóch typów eventów; żadna decyzja biznesowa,
kolejność eventów ani wynik tury nie zmienia się.

Implementation approach: wprowadzić brakującą warstwę mapującą jako czyste funkcje
w `observability/audit_views.py` i wywołać je w dwóch istniejących call-site'ach
zamiast `model_dump()`. Poziom szczegółowości (`normal`/`debug`) czytany w composition
root i przenoszony przez `SessionAuditRecorder`.

Tests:
- `tests/test_audit_compact.py` — 9 testów (compact summary, pełny `intent.resolved`,
  pełny `mutation.applied`, snapshot `turn.completed`, rekonstrukcja
  proposal → decision → mutation, wielorundowość, envelope, rozmiar debug vs normal,
  pełne `writable[]` w debug)
- regresja: cały `ai-data-contract-manager/tests` + `mcp-servers/mcp-contract-forge/tests`

Architecture risks:
- `BoundTurnAuditRecorder` ma `__getattr__` mapujący nazwy na typy eventów — nowy
  atrybut `level` musi być realną property, inaczej wpadnie w `_EVENT_NAMES`
  i rzuci `AttributeError`.
- `audit_views.py` leży w `application/`, więc nie może importować `pathlib`, sinków
  ani `google.cloud` (`test_logging_architecture.py`).

## Current behavior

`StabilizationEngine._analyze()` buduje payload `forge.analysis.completed` jako
`analysis.model_dump(mode="json")` z nałożonym kontekstem rundy. `TurnOrchestrator.run_turn()`
buduje `turn.completed` m.in. z `outcome.stabilization.model_dump(mode="json")`.
Nie istnieje żadna warstwa mapująca — `BoundTurnAuditRecorder.emit()` woła wyłącznie
generyczny `_dump()`. `ADCM_AUDIT_LEVEL` nie istnieje.

`StabilizationReport.foreign_removed` jest konsumowane przez
`adapters/response_basic.py`; `proposal_decisions` jest konsumowane wyłącznie przez audyt —
zgodnie z zakresem zadania model i tak pozostaje bez zmian.

## Planned changes

1. `observability/audit_views.py` — `forge_analysis_completed_view()`,
   `turn_completed_view()`, stałe `AUDIT_LEVEL_NORMAL`/`AUDIT_LEVEL_DEBUG`.
2. `session_audit_recorder.py` — `level` w `SessionAuditRecorder`, property `level`
   na `BoundTurnAuditRecorder`, domyślnie `normal`.
3. `stabilization_engine.py::_analyze` — payload z widoku zamiast `model_dump()`.
4. `turn_orchestrator.py` — payload `turn.completed` z widoku.
5. `adapters/api/app.py` — `ADCM_AUDIT_LEVEL` z walidacją, raport w `configuration_loaded`.
6. Testy `tests/test_audit_compact.py`.
7. Dokumentacja.

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

### Finding: cel 40–60% redukcji JSONL nie jest osiągalny w zadanym zakresie

Observation: envelope eventu (`event_id`, `timestamp`, `session_id`, `turn_no`,
`correlation_id`, `event_type`) zajmuje 18 915 B / 33,2% w `aaa.jsonl` i
44 445 B / 33,9% w `bbb.jsonl`. Symulacja docelowych payloadów daje −33,8% i −31,0%
rozmiaru całego pliku.

Affected assumption: „minimum 40–60% mniejszy JSONL" liczone od rozmiaru pliku.

Implementation impact: brak — zakres implementacji się nie zmienia.

Workaround complexity: osiągnięcie 40–60% na całym pliku wymagałoby skrócenia envelope
(zakazane) albo agregacji per-rundowych `proposal.decision` / `rule.proposal.generated`
(zakazane).

Simpler corrective option: raportować redukcję również dla samego pola `data`, gdzie
wynosi ~47% (`aaa`) i ~51% (`bbb`) — czyli cel jest spełniony na payloadach.

Decision: uzgodnione z użytkownikiem — trzymamy się zakresu zadania, pozostały narzut
raportujemy.

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many special cases, non-obvious transformations or changes across unrelated components, stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema, configuration or protected file.

## Deviations from the original plan

Dodano `measure_audit_size.py` w katalogu zadania — pomiar §22 na nagranych sesjach
uruchamia realne funkcje widoku zamiast ręcznej symulacji. Poza tym `None.`

## Verification

- [x] relevant unit tests pass — `ai-data-contract-manager/tests`: **32 passed**
      (23 istniejące bez modyfikacji + 9 nowych)
- [x] relevant integration tests pass — `mcp-servers/mcp-contract-forge/tests`:
      **12 passed** (uruchomione z katalogu pakietu)
- [x] architecture/boundary tests pass — `test_logging_architecture.py`,
      `test_turn_audit.py`, `test_stabilization.py` bez zmian
- [x] configured quality gates pass — `quality_gate.py --profile pre-push` zgłasza
      jedną porażkę: `mcp-contract-forge/tests/test_observability.py::test_correlation_id_is_technical_metadata_only`.
      **Porażka jest wcześniejsza i niezwiązana z tą zmianą** — test czyta
      `resources/contract.json` po ścieżce względnej, więc przechodzi z katalogu
      pakietu, a zawodzi gdy gate uruchamia pytest z korzenia repo. Zweryfikowane
      przez `git stash`: ten sam test zawodzi identycznie na stanie sprzed zmiany.
- [x] documentation freshness reviewed
- [x] `docs/generated/documentation-impact.md` reviewed
- [x] required curated documentation updated — `docs/logging-architecture.md`,
      `docs/logging-implementation-guide.md`, `ai-data-contract-manager/README.md`,
      `docker-compose.yml`

## Final result

Wprowadzono brakującą warstwę mapującą core → session audit view
(`application/observability/audit_views.py`) i wpięto ją w dwa istniejące call-site'y.
Modele domenowe nie zostały zmienione (**core impact = none**).

Zmienione payloady:
- `forge.analysis.completed` — compact summary: `status`, `writable_count`,
  `missing` jako lista ścieżek, `foreign_count`, `proposal_count`,
  `diagnostic_count`, `duration_ms`, `round`, `contract_revision`,
  `definition_version`, opcjonalne `phase`; `diagnostics` tylko gdy niepuste.
- `turn.completed` — `stabilization` → `{rounds, converged}`; `missing[]` bez pola
  `message`. Snapshot końcowy (`final_document`, `forge_status`, `diagnostics`,
  `external_checks`, `response`) bez zmian.

Bez zmian: `intent.resolved`, `candidate.*`, `mutation.applied`,
`forge.proposal.received`, `rule.proposal.generated`, `proposal.decision`,
`stabilization.round.started/completed`, `stabilization.completed`,
`external_checks.completed`, `response.composed`, `turn.started`,
`user.message.received`, `turn.failed`, envelope eventu, liczba eventów.

Dodano `ADCM_AUDIT_LEVEL` (`normal` domyślnie, `debug` = pełny `ForgeAnalysis`).

### Pomiar rozmiaru

Nagrane sesje sprzed zmiany, przepuszczone przez realne funkcje widoku
(`measure_audit_size.py`):

| plik | eventy | całość przed | całość po | redukcja | payload przed | payload po | redukcja payloadu |
|---|---|---|---|---|---|---|---|
| `aaa.jsonl` | 80 | 56 958 B | 37 846 B | **−33,6%** | 38 203 B | 19 091 B | **−50,0%** |
| `bbb.jsonl` | 188 | 130 938 B | 90 532 B | **−30,9%** | 86 869 B | 46 463 B | **−46,5%** |

Test `test_compact_audit_is_substantially_smaller_than_full_audit` na
syntetycznej turze 3-rundowej: 36 097 B → 19 572 B (**−45,8%**), payload
26 066 B → 9 496 B (**−63,6%**).

Co nadal zajmuje najwięcej miejsca (`bbb.jsonl` po zmianie):

| pozycja | rozmiar | udział |
|---|---|---|
| envelope wszystkich eventów | 44 445 B | 49% pliku po zmianie |
| `proposal.decision` (49 eventów) | 26 709 B | 29,5% |
| `rule.proposal.generated` (30 eventów) | 16 429 B | 18,1% |
| `mutation.applied` (14 eventów) | 7 991 B | 8,8% |
| `forge.proposal.received` (15 eventów) | 7 599 B | 8,4% |
| `forge.analysis.completed` (10 eventów) | 5 416 B | 6,0% (przed: 38 360 B) |

Wszystkie te pozycje są chronione zakresem zadania: envelope przez §17,
proposals/decisions przez §11–§12.

## Unresolved items

- Cel „minimum 40–60% mniejszego JSONL" liczony od rozmiaru pliku nie jest
  osiągalny bez naruszenia §17 lub §11–§12. Osiągnięto −31…−34% pliku i −47…−50%
  payloadu. Uzgodnione z użytkownikiem.
- `mcp-contract-forge/tests/test_observability.py::test_correlation_id_is_technical_metadata_only`
  zawodzi przy uruchomieniu z korzenia repo (ścieżka względna `resources/contract.json`).
  Problem istniał przed tą zmianą; poprawka to osobne zadanie.

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

`docs/active-task/2026-08-29_compact-session-audit/`

to:

`docs/history/2026-08-29_compact-session-audit/`

Do not leave completed task documentation in `docs/active-task/`.
