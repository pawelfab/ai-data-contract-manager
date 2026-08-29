# Current state — baseline 0.1

## Implemented

- dwa niezależne serwisy Python: ADCM i Contract Forge,
- osobne `pyproject.toml`, requirements i Dockerfile,
- komunikacja ADCM -> Forge przez MCP Streamable HTTP,
- Forge tools `contract_analyze` i `contract_describe`,
- generyczny dokument JSON w ADCM; brak modelu konkretnego kontraktu,
- provenance i append-only `MutationEvent` log w sesji,
- generyczne operacje add/replace/remove po JSON Pointer,
- deterministyczny `ConventionRulesEngine` dla defaultowego `ux_rules.json`,
- global/system scope, conditions `exists`, `equals`, `requirementsComplete`, template `{/json/pointer}` i priorytety,
- rozstrzyganie USER > USER_RULE > APP_RULE > Forge enrichment > Forge default,
- wykrywanie konfliktu równorzędnych propozycji,
- automatyczne wycofywanie wartości pochodnych po wygaśnięciu producenta,
- fixed-point z limitem rund,
- automatyczne usuwanie `foreign` zgłoszonych przez Forge,
- pusty `ExternalCheckCoordinator`,
- in-memory session repository,
- heurystyczny resolver intencji do smoke testów,
- opcjonalny adapter PydanticAI przygotowany za `IntentResolverPort`,
- podstawowa odpowiedź tekstowa i YAML dla `valid && complete`,
- testy jednostkowe obu usług i test kompatybilności wire-format.

## Intentionally not implemented yet

- pełne dopasowanie do produkcyjnego, zewnętrznego `contract.json`,
- pełna semantyka jego `x-contract-enrichment`, oneOf/discriminator i wszystkich x-contract-rules,
- user-specific `ux_rules` z przeglądarki i merge z default rules,
- regex/valueFrom/concat/lower/upper oraz bogatszy expression engine,
- `fieldPolicies` i external check capabilities,
- Schema Explorer MCP i inne Context MCP,
- trwały storage sesji,
- semantyczne restore typu „wróć do dataFileId, które podałem wcześniej”,
- semantic advisor,
- pełny PydanticAI intent resolver jako domyślny tryb,
- bezpieczne wycofanie automatycznie aktywowanego całego subtree, jeżeli ma potomka o wyższym autorytecie,
- pełne SC-01..SC-22 / EC-01..EC-13 jako E2E.

## Known baseline limitations

`resources/contract.json` w Forge jest wyłącznie lokalnym fixture. Nie jest zamiennikiem ani kopią właścicielskiego `contract.json`.
`ContractDefinitionNormalizer` jest celowym adapterem/seamem, który trzeba dopasować do rzeczywistego formatu bez przenoszenia tej wiedzy do ADCM.
