---
status: active
created: 2026-08-29
type: refactor
services: [adcm]
---

# Task: Compact Session Audit

## Problem

Session Audit zapisuje payloady 1:1 z modelami domenowymi. Przy turze wymagającej
kilku rund fixed-point ten sam materiał trafia do JSONL wielokrotnie:

1. `forge.analysis.completed` zawiera pełny `ForgeAnalysis.model_dump()` — w tym
   `writable[]` (kilkanaście deskryptorów pól), pełne obiekty `MissingRequirement`,
   `foreign`, `proposals` i `diagnostics` — powtarzany w **każdej rundzie**, mimo że
   `writable` jest w praktyce identyczne między rundami.
2. `turn.completed` zawiera `StabilizationReport.model_dump()`, czyli pełną listę
   `proposal_decisions[]` ze wszystkich rund — mimo że każda decyzja ma już własny
   event `proposal.decision`.

Pomiar na `ai-data-contract-manager/logs/sessions/`:

| plik | rozmiar | eventy | `forge.analysis.completed` | z tego `writable[]` | `proposal_decisions[]` w `turn.completed` |
|---|---|---|---|---|---|
| `aaa.jsonl` | 56 958 B | 80 | 19 420 B (34%) | 13 685 B (24% pliku) | 1 927 B |
| `bbb.jsonl` | 130 938 B | 188 | 38 360 B (29%) | 27 370 B (21% pliku) | 6 603 B |

## Goal

Session Audit ma zawierać dokładnie tyle danych, ile potrzeba do diagnostyki tury,
a nie być kopią 1:1 modeli domenowych. Po zmianie z event streamu nadal musi dać się
ustalić: treść wiadomości użytkownika, wynik `IntentResolver`, powstałe candidates i
ich dyspozycje, faktyczne mutacje, proposals z ADCM rules i Forge, powód zastosowania
lub odrzucenia proposal, zmiany w każdej rundzie stabilizacji, moment osiągnięcia
fixed-pointu, końcowy dokument, finalny status Forge i odpowiedź dla użytkownika.

## Scope

Included:
- `forge.analysis.completed` → compact summary (`writable_count`, `missing` jako lista
  ścieżek, `foreign_count`, `proposal_count`, `diagnostic_count`, `status`, `duration_ms`).
- `turn.completed` → `stabilization` zredukowane do `{rounds, converged}`;
  `missing[]` bez pola `message`.
- Nowa warstwa mapująca core model → session audit view (`observability/audit_views.py`).
- `ADCM_AUDIT_LEVEL` (`normal` domyślnie, `debug` = pełny `ForgeAnalysis`).
- Testy regresyjne compact audit + test porównania rozmiaru.
- Synchronizacja `docs/logging-architecture.md` i `docs/logging-implementation-guide.md`.

## Out of scope

- gzip/kompresja, sampling, log rotation, zewnętrzny event store, zmiana formatu JSONL.
- Zmiany logiki biznesowej: `IntentResolver`, `CandidatePolicy`, `DocumentEngine`,
  `ProposalReconciler`, `ConventionRulesEngine`, semantyka `StabilizationEngine`,
  analiza Forge, provenance, precedencja autorytetu, fixed-point.
- Zmiany publicznych modeli core wyłącznie po to, żeby JSONL był mniejszy.
- Redukcja `intent.resolved`, `candidate.*`, `mutation.applied`, `proposal.decision`,
  `rule.proposal.generated`, `forge.proposal.received`, `stabilization.round.*`,
  `stabilization.completed`, `turn.failed`.
- Zmiana envelope eventu (`session_id`, `turn_no`, `correlation_id`, `event_id`,
  `timestamp`, `event_type`).
- Ogólny dedup engine / state machine / event compression service.

## Constraints

- `core impact = none` — modele domenowe pozostają nietknięte, redukcja wyłącznie
  w warstwie observability/audit.
- Wszystkie istniejące testy ADCM i Forge muszą przejść bez modyfikacji.
- `application/` nie może zyskać zależności infrastrukturalnych
  (`test_logging_architecture.py`).

Constraints control expected scope, but they are not proof that an input, contract, schema or assumption is correct. If preserving a constraint requires disproportionate workaround complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [ ] `forge.analysis.completed` w trybie normal jest compact summary bez `writable[]`
      i bez pełnej listy `proposals[]`.
- [ ] `writable[]` nie jest powtarzany w każdej rundzie normalnego audytu.
- [ ] `turn.completed` nie duplikuje historii `proposal_decisions[]`.
- [ ] `turn.completed` nadal zawiera `final_document`, `forge_status`, `missing`,
      `diagnostics`, `external_checks`, `response`.
- [ ] `intent.resolved` pozostaje pełny (candidates, confidence, evidence, unresolved,
      knowledge_query).
- [ ] `mutation.applied` pozostaje pełny (old/new value, source, producer_id, rewizje).
- [ ] proposals i decisions pozostają osobnymi eventami; ścieżkę
      proposal → decision → mutation da się odtworzyć z event streamu.
- [ ] Numery rund i rewizje pozostają czytelne dla diagnostyki fixed-point.
- [ ] Envelope eventu bez zmian.
- [ ] Logika biznesowa bez zmian; wszystkie istniejące testy przechodzą.
- [ ] Nowe testy compact audit przechodzą.
- [ ] Rozmiar przykładowej wielorundowej sesji wyraźnie spadł (pomiar w `IMPLEMENTATION.md`).

## Relevant references

- issue/ticket: —
- prior task/decision: `docs/history/2026-08-29_logs_module_implement/`
- documentation: `docs/logging-architecture.md`, `docs/logging-implementation-guide.md`
