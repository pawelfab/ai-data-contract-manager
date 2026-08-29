---
status: active
created: 2026-08-29
completed:
---

# Implementation: Aktualizacja automatyki agentowej po przejściu na strukturę v6

## Implementation contract

Owning service: brak — zmiana obejmuje wyłącznie automatykę repozytorium i dokumentację sterującą.

Owning boundary: `scripts/agent/` (konfiguracja) + dokumenty kurowane w `docs/` i README.

Files expected to change:
- `scripts/agent/config.json`
- `scripts/agent/config.example.json`
- `AGENTS.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/agent/START_HERE.md`
- `mcp-servers/mcp-contract-forge/README.md`
- `docker-compose.yml`
- `mcp-servers/mcp-contract-forge/tests/test_analyzer.py`
- `docs/generated/*`, `docs/.freshness.json` (generowane)

Files/services explicitly not to change:
- `ai-data-contract-manager/src/`
- `mcp-servers/mcp-contract-forge/src/`
- skrypty `.py` w `scripts/agent/`
- `githooks/pre-commit`, `githooks/pre-push`

Main invariant: `documentation_map` i `documentation_evidence_patterns` mogą odwoływać się wyłącznie
do plików istniejących w drzewie repozytorium. Dokument, który jest dowodem dokumentacyjnym, nie może
jednocześnie być „relevant code" — inaczej sam zaspokaja własną bramkę.

Implementation approach: zmiana wyłącznie deklaratywna w `config.json`; skrypty czytają wszystkie
ścieżki repo przez konfigurację, więc nie wymagają modyfikacji.

Tests:
- `scripts/agent/tests/test_documentation_update.py`
- `quality_gate.py --profile pre-push` (testy obu usług)
- symulacja `doc_freshness.check_staged` na 7 scenariuszach stage'owania

Architecture risks:
- zbyt szerokie `documentation_evidence_patterns` osłabiają bramkę do fikcji;
- dodanie `resources/` do `documentation_relevant_patterns` wymusza dokumentowanie każdej zmiany
  reguł UX — to zamierzone, `ux_rules.json` jest kontraktem zachowania, nie plikiem pomocniczym.

## Current behavior

Przed zmianą (potwierdzone uruchomieniem read-only):

- `source_files()` indeksuje 53 pliki; `ux_rules.json` ADCM nie jest wśród nich;
- `doc_freshness.py --check` → `STALE`;
- `docs/generated/documentation-impact.md` wylicza ~200 ścieżek z drzewa v5, w większości nieistniejących;
- `quality_gate.py --profile pre-push` → exit 1 (4/4 testy Forge failują na `FileNotFoundError`,
  testy ADCM nie startują — brak `pytest` w venv).

Skrypty same w sobie działają poprawnie: `ROOT` w `scripts/agent/common.py:11` rozwiązuje się do
korzenia repo, a `configured_source_paths()` filtruje wyłącznie na podstawie konfiguracji.

## Planned changes

1. `source_roots` += `ai-data-contract-manager/resources`.
2. `documentation_relevant_patterns`: dopisać `resources/` dla ADCM; zawęzić `^scripts/agent/`
   do `^scripts/agent/[^/]*\.(py|json)$`.
3. `documentation_map`: przemapować 8 wpisów na istniejące dokumenty `docs/*.md`; usunąć wpisy dla
   `discovery_rules.json` i forge'owego `ux_rules.json`.
4. `documentation_evidence_patterns`: zastąpić zestawem odpowiadającym aktualnym `docs/*.md`.
5. Usunąć martwe klucze `session_state_dir`, `session_state_max_age_hours`,
   `require_freshness_marker_for_staged_relevant_code`.
6. `protected_agent_paths` += `.codex/agents/`, `.codex/config.toml`, `.claude/`.
7. Zsynchronizować `config.example.json`.
8. Naprawić martwe odnośniki w `AGENTS.md`, `README.md`, `docs/CURRENT_STATE.md`,
   `docs/agent/START_HERE.md`.
9. Zregenerować `docs/generated/*`.

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

### Finding: `require_freshness_marker_for_staged_relevant_code` jest nieimplementowalny w obecnej kolejności hooka

Observation: klucz był ustawiony na `true` w `config.json`, ale żaden skrypt go nie czyta.

Affected assumption: założenie, że to działająca bramka wymuszająca obecność `docs/.freshness.json`
w commicie.

Implementation impact: pierwotnie rozważano implementację zamiast usunięcia.

Workaround complexity: implementacja wymagałaby odwrócenia kolejności w `githooks/pre-commit` —
`doc_freshness.py --check-staged` biegnie *przed* `documentation_update.py --staged`, więc w momencie
sprawdzenia marker z definicji nie jest jeszcze zastage'owany. Bramka failowałaby zawsze.

Simpler corrective option: usunąć klucz. Marker i tak jest stage'owany automatycznie przez
`documentation_update.stage_generated_artifacts()` w tym samym commicie.

Decision: usunięto klucz. Bramka nie jest potrzebna, bo generator sam gwarantuje ten warunek.

### Finding: bramka `pre-push` była czerwona przed rozpoczęciem zadania

Observation: `quality_gate.py --profile pre-push` kończył się exit 1 z dwóch niezależnych powodów:
`tests/test_analyzer.py:8` i `mcp-servers/mcp-contract-forge/README.md:12` wskazywały
`resources/contract.example.json` (plik przemianowany na `contract.json`), a venv ADCM nie miał
zainstalowanego `pytest`.

Affected assumption: założenie, że rename `contract.example.json` → `contract.json` był kompletny.

Implementation impact: bez naprawy nie dało się zweryfikować kryterium akceptacji „pre-push exit 0".
Ten sam rename nie został też odzwierciedlony w `docker-compose.yml:10` — montowany był nieistniejący
plik, więc `docker compose up` nie wystartowałby Forge.

Workaround complexity: znikoma — trzy jednoliniowe poprawki ścieżki.

Simpler corrective option: brak, poprawka jest minimalna.

Decision: naprawiono wszystkie trzy odwołania w ramach tego zadania (ta sama klasa nieaktualności
co reszta zakresu). W venv ADCM zainstalowano dokładnie wersje pinowane w
`ai-data-contract-manager/requirements-dev.txt` (`pytest==8.4.1`, `pytest-asyncio==0.25.3`) —
to uzupełnienie środowiska lokalnego, nie zmiana w repozytorium.

### Finding: `scripts/agent/README.md` mógłby zaspokajać własną bramkę

Observation: dokument stał się celem `documentation_map` i wzorcem dowodowym, a jednocześnie
pasował do `documentation_relevant_patterns` przez szeroki wzorzec `^scripts/agent/`.

Affected assumption: rozłączność zbiorów „kod wymagający dokumentacji" i „dokumentacja jako dowód".

Implementation impact: zastage'owanie samego `scripts/agent/README.md` przechodziłoby bramkę,
mimo że nie towarzyszy mu żaden dokument zadania.

Workaround complexity: znikoma.

Simpler corrective option: zawężenie wzorca do rozszerzeń `.py` i `.json`.

Decision: zawężono do `^scripts/agent/[^/]*\.(py|json)$`. Zweryfikowane scenariuszem nr 5.

### Finding: szablon `docs/templates/task/IMPLEMENTATION.md` odsyłał do usuniętego dokumentu

Observation: szablon zawierał odwołanie do `docs/architecture-guardrails.md`, usuniętego w `af8652b`.

Affected assumption: aktualność szablonów zadań.

Implementation impact: każde nowe zadanie dziedziczyło martwy odnośnik.

Workaround complexity: znikoma.

Simpler corrective option: podmiana na istniejące `docs/ARCHITECTURE_BASELINE.md` i
`docs/CORE_INVARIANTS.md`.

Decision: poprawiono szablon.

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many special cases, non-obvious transformations or changes across unrelated components, stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema, configuration or protected file.

## Deviations from the original plan

Zakres rozszerzony o trzy poprawki nieobjęte planem, wszystkie tej samej klasy (niedokończony rename
`contract.example.json` → `contract.json`): `mcp-servers/mcp-contract-forge/tests/test_analyzer.py`,
`mcp-servers/mcp-contract-forge/README.md` oraz `docker-compose.yml`. Bez nich nie dało się osiągnąć
kryterium „pre-push exit 0", a `docker compose up` pozostawałby zepsuty.

Plan zakładał weryfikację bramki przez faktyczne stage'owanie plików. Zrealizowano ją zamiast tego
przez podmianę `doc_freshness.staged_files()`, żeby nie naruszyć przygotowanego indeksu Git.

Komenda z planu `python -m unittest discover -s scripts/agent/tests -t scripts/agent` nie działa —
katalog `tests/` nie ma `__init__.py`. Użyto `python -m unittest tests.test_documentation_update`
z katalogu `scripts/agent/`.

## Verification

- [x] relevant unit tests pass — `scripts/agent/tests/test_documentation_update.py`: 3/3 OK
- [x] relevant integration tests pass — ADCM 5/5, Forge 4/4
- [ ] architecture/boundary tests pass when applicable — brak takich testów w drzewie v6
- [x] configured quality gates pass — `quality_gate.py --profile pre-push` exit 0
- [x] documentation freshness reviewed — `doc_freshness.py --check` → `CURRENT`, exit 0
- [x] `docs/generated/documentation-impact.md` reviewed — 8/8 celów istnieje na dysku
- [x] required curated documentation updated

Symulacja bramki `check_staged` (7 scenariuszy, bez naruszania indeksu):

| Scenariusz | Wynik |
|---|---|
| kod ADCM + `MODULE_CONTRACTS.md` + dokument zadania | `CURRENT` |
| sam kod, bez dokumentów | `STALE` |
| kod + dokument kurowany, bez dokumentu zadania | `STALE` |
| `ux_rules.json` + `BUSINESS_BEHAVIOR.md` + dokument zadania | `CURRENT` |
| sam `scripts/agent/README.md` | `CURRENT` (nie jest „relevant code") |
| `config.json` + `AGENTS.md` + dokument zadania | `CURRENT` |
| kod + tylko `docs/generated/` (non-evidence) | `STALE` |

Niezweryfikowane: `docker compose config` — brak `docker` w `PATH` sesji, w której prowadzono prace.
Poprawka montażu w `docker-compose.yml:10` została zweryfikowana wyłącznie przez sprawdzenie
istnienia pliku na dysku.

## Final result

Skrypty `scripts/agent/*.py` **nie wymagały żadnych zmian** — cała wiedza o strukturze repozytorium
jest w `config.json`, a `ROOT` rozwiązuje się poprawnie. Nieaktualna była konfiguracja i dokumentacja
sterująca.

Zmienione:

- `scripts/agent/config.json` — `source_roots` += `ai-data-contract-manager/resources`;
  `documentation_map` z 9 wpisów (14 martwych celów) na 8 wpisów wskazujących wyłącznie istniejące
  pliki; `documentation_evidence_patterns` przemapowane na aktualny zestaw `docs/*.md`;
  `^scripts/agent/` zawężone do `\.(py|json)$`; usunięte 3 martwe klucze; `protected_agent_paths`
  += `.codex/agents/`, `.codex/config.toml`, `.claude/`.
- `scripts/agent/config.example.json` — zsynchronizowany kształt, zachowany charakter szablonu.
- `AGENTS.md` — 4 martwe odnośniki do dokumentów zastąpione aktualnym zestawem; poprawione nazwy
  artefaktów generowanych (`repositorymap.md` → `repository-map.md`,
  `repositoryinventory.json` → `repository-inventory.json`).
- `README.md` — nieistniejące `scripts/bootstrap_local.sh` i `scripts/test_all.sh` zastąpione
  realnymi krokami; dodana sekcja o automatyce dokumentacji.
- `docs/CURRENT_STATE.md`, `docs/agent/START_HERE.md`, `mcp-servers/mcp-contract-forge/README.md`,
  `docker-compose.yml`, `mcp-servers/mcp-contract-forge/tests/test_analyzer.py` — martwe odnośniki
  i niedokończony rename.
- `docs/templates/task/IMPLEMENTATION.md` — odnośnik do usuniętego `docs/architecture-guardrails.md`.
- `docs/generated/*` i `docs/.freshness.json` — zregenerowane; inwentarz 53 → 54 pliki,
  `documentation-impact.md` skrócony o 254 linie martwych ścieżek.
- Usunięte `scripts/agent/__pycache__/` i `scripts/agent/tests/__pycache__/` — zawierały `.pyc`
  po skasowanych modułach `validate_setup`, `doc_impact`, `setup_workflow`.

## Unresolved items

- `pre_commit_quality_stages` (`format_check`, `lint`) pozostają puste — pre-commit nie uruchamia
  żadnej kontroli jakości kodu. Poza zakresem tego zadania.
- `docs/protocol/*.schema.json` nie są objęte `source_roots`: leżą pod `docs/`, a
  `check_staged()` wyklucza ścieżki z `architecture_docs_dir` ze zbioru „relevant code" —
  włączenie ich dałoby sprzeczność semantyczną. Do rozstrzygnięcia osobno.
- `docker compose config` niezweryfikowane (brak `docker` w środowisku).

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

`docs/active-task/2026-08-29_agent-automation-refresh/`

to:

`docs/history/2026-08-29_agent-automation-refresh/`

Do not leave completed task documentation in `docs/active-task/`.
