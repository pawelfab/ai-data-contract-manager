---
status: active
created: 2026-08-29
type: chore
services: [adcm, contract-forge]
---

# Task: Aktualizacja automatyki agentowej po przejściu na strukturę v6

## Problem

Commit `af8652b "inicjalny"` na gałęzi `adcm_v6_core` zastąpił strukturę v5 (hexagonal:
`adapters/inbound|outbound/`, `application/use_cases/`, `application/ports/`, `bootstrap/`,
`domain/contract/`, per-serwisowe katalogi `docs/`) płaską strukturą v6 core.

`scripts/agent/config.json` nie został wtedy zaktualizowany. Skutki:

- `documentation_map` wskazuje 14 nieistniejących plików — cały `ai-data-contract-manager/docs/`,
  cały `mcp-servers/mcp-contract-forge/docs/` oraz `docs/documentation-automation.md`;
- `documentation_evidence_patterns` trafia dziś wyłącznie w `docs/CURRENT_STATE.md`; pozostałe
  cztery wzorce (`architecture`, `DECISIONS`, `KNOWN_ISSUES`, `documentation-automation`) celują
  w pliki usunięte. **Aktualizacja `docs/MODULE_CONTRACTS.md`, `docs/CORE_INVARIANTS.md`,
  `docs/ARCHITECTURE_BASELINE.md` czy `docs/BUSINESS_BEHAVIOR.md` nie liczy się jako dowód**,
  więc `githooks/pre-commit` odrzuca poprawnie udokumentowane commity;
- `ai-data-contract-manager/resources/ux_rules.json` (przeniesiony z Forge) nie jest objęty
  `source_roots` — jest niewidoczny dla inwentarza i dla hasha świeżości, mimo że to zasób runtime;
- w konfiguracji zostały martwe klucze po usuniętym `validate_setup.py`.

Dodatkowo bramka `pre-push` była czerwona niezależnie od powyższego: rename
`resources/contract.example.json` → `contract.json` nie został odzwierciedlony w teście Forge,
w `docker-compose.yml` ani w README Forge.

## Goal

`githooks/pre-commit` i `pre-push` znów są użyteczne: przepuszczają zmianę z prawidłową
dokumentacją, blokują zmianę bez niej, a `docs/generated/*` opisuje faktyczne drzewo repozytorium.

## Scope

Included:
- `scripts/agent/config.json` — `source_roots`, `documentation_relevant_patterns`,
  `documentation_evidence_patterns`, `documentation_map`, `protected_agent_paths`, martwe klucze;
- `scripts/agent/config.example.json` — synchronizacja kształtu przy zachowaniu charakteru szablonu;
- `AGENTS.md`, `README.md` (root), `docs/CURRENT_STATE.md`, `docs/agent/START_HERE.md`,
  `mcp-servers/mcp-contract-forge/README.md` — martwe odnośniki;
- `docker-compose.yml` i `mcp-servers/mcp-contract-forge/tests/test_analyzer.py` — rename
  `contract.example.json` → `contract.json`;
- regeneracja `docs/generated/*` i `docs/.freshness.json`.

## Out of scope

- kod produkcyjny obu usług (`src/`) — nie zmieniany;
- odtwarzanie usuniętych per-serwisowych katalogów `docs/`;
- dodawanie katalogów `tests/` oraz `docs/protocol/*.schema.json` do `source_roots`;
- implementacja nowych bramek jakości (`format_check`, `lint`, `typecheck` pozostają puste).

## Constraints

- skrypty w `scripts/agent/` nie zmieniają się — problem leży wyłącznie w konfiguracji i dokumentacji;
- `config.example.json` pozostaje szablonem: `strict_stop_gate: false`, puste `quality_commands`,
  bez lokalnych ścieżek `.venv`;
- `documentation_map` może wskazywać wyłącznie pliki istniejące w drzewie;
- `scripts/agent/`, `AGENTS.md`, `githooks/` są w `protected_agent_paths` — edycje wymagają
  ręcznego zatwierdzenia.

Constraints control expected scope, but they are not proof that an input, contract, schema or assumption is correct. If preserving a constraint requires disproportionate workaround complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [x] `repo_inventory.py` indeksuje `ai-data-contract-manager/resources/ux_rules.json`
- [x] każda ścieżka w sekcji „Curated documentation to review" w `docs/generated/documentation-impact.md` istnieje na dysku
- [x] `doc_freshness.py --check` → `CURRENT`, exit 0
- [x] kod + `docs/MODULE_CONTRACTS.md` + dokument zadania → `--check-staged` = `CURRENT`
- [x] sam kod bez dokumentów → `--check-staged` = `STALE`, exit 1
- [x] `scripts/agent/README.md` sam z siebie nie jest „relevant code" (nie może zaspokoić własnej bramki)
- [x] testy automatyki `scripts/agent/tests/` przechodzą
- [x] `quality_gate.py --profile pre-push` → exit 0
- [x] brak odwołań do `contract.example.json` poza `docs/generated/`

## Relevant references

- issue/ticket: —
- prior task/decision: commit `af8652b "inicjalny"` (przejście v5 → v6 core)
- documentation: `scripts/agent/README.md`, `docs/ARCHITECTURE_BASELINE.md`
