# ADCM — staged implementation plan

Ten pakiet służy do sekwencyjnego wdrażania brakujących elementów w obecnym minimalnym ADCM.

## Zasada użycia

Wykonuj stage po stage'u, w kolejności:

1. `STAGE_00_BASELINE.md`
2. `STAGE_01_FORGE_PRECEDENCE.md`
3. `STAGE_02_USER_FACT_MEMORY.md`
4. `STAGE_03_STAIR_STEP_RESOLUTION.md`
5. `STAGE_04_PARTIAL_STRUCTURED_INPUT.md`
6. `STAGE_05_LLM_SEMANTIC_FALLBACK.md`
7. `STAGE_06_SCHEMA_DRIVEN_REQUIREMENTS.md`
8. `STAGE_07_E2E_AND_CLEANUP.md`

Nie łącz kilku stage'ów w jeden duży refactor.

Każdy stage:
- najpierw wymaga przeczytania `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`;
- wymaga sprawdzenia rzeczywistego kodu przed zmianami;
- określa `GOAL`, `BOUNDARY`, `NON-GOALS`, `TODO`, testy i kryterium zakończenia;
- kończy się aktualizacją `docs/CURRENT_STATE.md`;
- nie może implementować funkcjonalności z kolejnego stage'u.

## Docelowy model odpowiedzialności

### ADCM
- prowadzi rozmowę;
- przechowuje transcript i fakty użytkownika;
- normalizuje wejście;
- używa deterministycznych heurystyk przed LLM;
- wykonuje kontrolowany stair-step loop;
- wysyła do Forge wyłącznie kandydatów dla pól wystawionych przez Forge;
- nie posiada kontraktu.

### Contract Forge MCP
- posiada canonical contract;
- interpretuje `contract.json`;
- stosuje system enrichment;
- stosuje generic enrichment;
- stosuje JSON Schema defaults;
- rozstrzyga precedence wartości;
- odkrywa wymagania;
- waliduje kandydatów i finalny kontrakt.

### LLM
- jest semantic fallback;
- nie steruje loopem;
- nie wybiera dowolnych pathów;
- nie modyfikuje canonical contract bezpośrednio;
- informacja wydobyta przez LLM z wypowiedzi użytkownika nadal jest faktem USER, a nie niezależnym biznesowym źródłem wartości.

## Dwa osobne mechanizmy kolejności

Nie mieszamy dwóch odpowiedzialności.

### ADCM — recency faktów USER

Dla tego samego path ADCM przechowuje najnowszy fakt użytkownika:

1. nowsza informacja USER;
2. starsza informacja USER.

ADCM rozstrzyga to na podstawie kolejności wiadomości / `message_sequence`.

### Contract Forge — precedence źródeł wartości

Forge rozstrzyga, które źródło może zapisać wartość do canonical contract:

1. `USER`;
2. `SYSTEM_ENRICHMENT`;
3. `GENERIC_ENRICHMENT`;
4. `SCHEMA_DEFAULT`.

Brak wartości po zastosowaniu powyższych źródeł oznacza requirement do rozwiązania przez ADCM/usera.

`deterministic` i `llm` określają **metodę ekstrakcji faktu użytkownika**, a nie jego biznesowy priorytet.

Informacja wyciągnięta przez LLM z wypowiedzi usera nadal ma `origin=USER`.

## Ważne ograniczenie tej serii

Nie implementujemy obecnie uniwersalnego interpretera dowolnego JSON Schema.

Wspieramy obecny zakres i projektujemy interfejsy tak, aby w przyszłości można było rozszerzyć obsługę.

Nie należy teraz implementować m.in.:
- pełnego `allOf` / dowolnego `anyOf`;
- remote `$ref`;
- dynamicznych zewnętrznych schema registry;
- automatycznej interpretacji nieznanych `x-contract-rules`;
- nowych enrichment action rozpoznawanych przez LLM;
- Schema Explorer MCP;
- web UI;
- persistent database session store.

## Definicja zakończenia całej serii

Po Stage 07 powinien działać scenariusz:

1. User w pierwszej wiadomości może wkleić wiele informacji naraz.
2. Forge na początku żąda tylko source system.
3. ADCM znajduje source system w wiadomości i wysyła do Forge.
4. Forge stosuje enrichment/defaulty i odkrywa następne requirement.
5. ADCM bez pytania usera przeszukuje już posiadaną rozmowę/fakty.
6. Jeśli wartość istnieje, wysyła ją do Forge.
7. Loop trwa, dopóki ADCM ma dane.
8. User jest pytany dopiero o faktycznie brakującą informację.
9. Jeśli user poda wartość dla pola wcześniej wypełnionego enrichmentem/defaultem, Forge przyjmuje USER jako wyższy origin.
10. Jeśli user poda tę samą informację ponownie, ADCM wybiera najnowszy UserFact i wysyła go do Forge.
11. Forge nie analizuje historii rozmowy ani nie ustala, która wiadomość usera jest nowsza.
12. Heurystyki są używane przed LLM.
13. ADCM nie hardkoduje struktury kontraktu tam, gdzie Forge może wystawić requirement/schema metadata.
