# Handoff: Source → Bronze → Silver/Gold

Status: **zaimplementowane** (2026-08-23). Zakres zgodny z `PLAN.md` i `IMPLEMENTATION_GUIDE.md`.

## Co zostało zmienione

### Kod Forge

- `src/contract_forge/domain/enrichment/models.py` — `EnrichmentCondition` dostał
  `requirements_complete` (alias JSON `requirementsComplete`) oraz `populate_by_name`.
- `src/contract_forge/application/services/enrichment_resolver.py` — `resolve_enrichment()`
  przyjmuje **obowiązkowy** keyword-only `open_requirement_paths`; publiczne
  `requirement_is_under()` / `requirements_complete()` realizują semantykę prefiksu.
- `src/contract_forge/application/use_cases/evaluate_contract.py` — zbiór budowany z pełnych
  `formal_requirements`, przed `fillable_requirements()` i przed discovery.

### `resources/ux_rules.json` (wersja `5` → `6`)

Dodane globalne reguły: `global.activate_bronze` (scaffold `{}`, priorytet 50),
`global.bronze_{project,dataset,table,columns}` (priorytet 100),
`global.{silver,gold}_*` (priorytet 100). `global.enable_silver` / `global.enable_gold`
zachowały identyfikatory, dostały warunki kompletności Source + Bronze.
Usunięta reguła systemowa `sap.silver_dataset`.
Bez zmian: `global.source_system.*`, `sap.enable_converter`, `sap.enable_preparator`.

## Kluczowe własności

**Rozdzielenie faz przez warunki, nie przez priorytety.** Scaffold wymaga
`/bronzeTable exists=false`, każde dziecko `exists=true`. Pojedyncza ewaluacja nigdy nie zwróci
jednocześnie `/bronzeTable` i ścieżki pod nim, więc pusty obiekt nie może nadpisać wypełnionego
Bronze. Nie polegamy na sortowaniu w `ValueResolver` ani na `ContractState`.

Było to konieczne: `/bronzeTable/columns` jest osiągalny przez `enrichment_target_reachable()`
także przy nieistniejącym `/bronzeTable`, więc bez `exists=true` obie reguły odpaliłyby w jednej
rundzie.

**`requirementsComplete` ≠ poprawność.** Oznacza brak brakujących wymagań formalnych pod
prefiksem. Błędy walidacji formalnej nadal mogą utrzymywać `valid=false`.

**Zweryfikowany fixed-point** (dla każdego z czterech typów źródła):

```text
1. Source kompletne          → /bronzeTable = {}
2. dzieci Bronze             → table.* = {system}_bronze, columns = []
3. Bronze kompletne          → /silver/enabled, /gold/enabled
4. warstwy aktywne           → nazwy {system}_silver / {system}_gold, source = {system}_bronze
5. stały punkt               → otwarte tylko /silver/tables/0/pk i /silver/tables/0/columns
```

## Testy

`tests/unit/test_enrichment_repository.py` — semantyka `requirements_complete()`, alias JSON,
gating reguły przez adapter. Wszystkie dotychczasowe wywołania `resolve_enrichment` przekazują
teraz `open_requirement_paths` jawnie.

`tests/unit/test_evaluate_contract.py` — scenariusze parametryzowane po `jdbc`, `json`, `txt`,
`fixed_width` na **niesystemowym** `sourceSystemGcpId=rocket` (izolacja od SAP Converter/
Preparator): brak aktywacji przy niekompletnym Source, aktywacja wyłącznie Bronze, wartości
Bronze, aktywacja Silver/Gold, globalne identyfikatory, Silver `pk`/`columns` jako pytania,
kolejność faz z limitem 10 iteracji, przeliczenie nazw po zmianie systemu. Osobny test SAP
sprawdza współistnienie reguł systemowych z globalną konwencją.

Invariant sprawdzany w każdej ewaluacji dotyczy **wyłącznie Bronze** — nie ustanowiono globalnego
zakazu par parent/descendant, bo przyszłe sugestie strukturalne mogą celowo korzystać
z priorytetowego overlay.

Wynik: Forge 84 passed, ADCM 29 passed.

## Świadome ograniczenia

- SAP z aktywnym Preparatorem nadal produkuje issue `preparator.enabled_requires_operation`.
  Test SAP tego nie maskuje i nie oczekuje `valid=true`. Poza zakresem tego zadania.
- Reguły SAP Converter/Preparator nadal odpalają się na sam `/source/sourceType exists`, czyli
  mogą aktywować się przy niekompletnym Source. Świadomie zostawione bez zmian zgodnie z guide §5.
- Pierwszeństwo wartości użytkownika nad derived jest odpowiedzialnością ADCM i nie było tu
  testowane w Forge; pełny zestaw testów ADCM przechodzi bez zmian w kodzie ADCM.

## Nietknięte

`contract.json`, `discovery_rules.json`, `schema_paths.py`, union/discriminator, całe ADCM,
Forge MCP API, `docs/architecture-guardrails.md`.
