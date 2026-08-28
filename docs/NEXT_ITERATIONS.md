# Następne iteracje

Baseline celowo nie implementuje całego zachowania biznesowego. Kolejne kroki powinny rozszerzać istniejące black-boxy, a nie orchestrator przez przypadki specjalne.

1. Dopasować `ContractDefinitionNormalizer` do rzeczywistego, zewnętrznego `contract.json` i jego istniejącego `x-contract-enrichment`.
2. Dodać pełne warianty/oneOf/discriminator i wszystkie reguły formalne Forge.
3. Rozszerzyć `ux_rules` o `valueFrom`, regex/template transforms i user rules z przeglądarki.
4. Dodać bezpieczne wycofywanie derived subtree bez usuwania potomków o wyższym autorytecie.
5. Dodać PydanticAI intent resolver używający `contract_describe` jako kontekstu.
6. Dodać `SchemaExplorerPort` i adapter MCP pod `ExternalCheckCoordinator`; brak providera ma dawać `SKIPPED/degraded`, nie awarię tury.
7. Dodać trwały `SessionRepositoryPort`, historię per pole i restore po semantycznym odwołaniu usera.
8. Dodać pełny YAML artifact renderer po `valid && complete`.
9. Dodać testy E2E dla całej macierzy SC/EC z dokumentu biznesowego.
