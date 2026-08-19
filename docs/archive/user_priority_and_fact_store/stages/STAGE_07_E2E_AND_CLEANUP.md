# STAGE 07 — end-to-end, regresja i uproszczenie

## GOAL

Połączyć wszystkie poprzednie stage'e i potwierdzić docelowy minimalny behavior.

Nie dodawaj nowych funkcji produktowych.

## REQUIRED E2E SCENARIO A — dużo informacji w pierwszej wiadomości

User w jednej wiadomości podaje przykładowo:
- source system SAP;
- pipeline id;
- owner;
- CSV URI;
- source columns z typami;
- własny schedule.

Expected:

1. Forge na początku pyta tylko o source system.
2. ADCM rozpoznaje SAP.
3. Forge stosuje enrichment/defaults.
4. Forge odkrywa kolejne pola.
5. ADCM wykorzystuje już istniejące informacje bez ponownego pytania.
6. Schedule USER nadpisuje schedule enrichment/default, jeśli jest poprawny.
7. User jest pytany dopiero o pierwsze faktycznie brakujące pole.
8. Final contract przechodzi Forge validation.

## REQUIRED E2E SCENARIO B — user poprawia sam siebie

User:
```text
owner team_a
```

później:
```text
owner jednak team_b
```

Jeśli Forge dopiero potem odkrywa owner albo owner był wcześniej wypełniony:
- ADCM wybiera `team_b` jako najnowszy UserFact;
- do Forge trafia tylko aktualny USER candidate;
- wynik canonical contract ma być `team_b`;
- provenance ma mieć `origin=USER`;
- Forge nie musi porównywać sequence obu wiadomości.

## REQUIRED E2E SCENARIO C — partial columns

User:
```text
data_d, sap1, sap2, sap3
```

Expected:
- ADCM zachowuje names;
- pyta tylko o brakujące typy;
- po podaniu typów scala;
- submituje complete candidate;
- nie powtarza identycznego pytania bez wyjaśnienia.

## REQUIRED E2E SCENARIO D — deterministic before LLM

Dane są deterministycznie rozpoznawalne.

Expected:
- LLM call count = 0 dla tych pól.

Następnie użyj wypowiedzi, którą rozwiąże fake semantic resolver.

Expected:
- LLM jest fallback;
- candidate ograniczony do Forge paths.

## REQUIRED E2E SCENARIO E — nowy prosty required field

Zmodyfikuj testowy schema przez dodanie nowego prostego required field.

Expected:
- orchestrator nie wymaga zmiany;
- Forge wystawia requirement;
- generic resolver / user answer obsługuje je.

## CLEANUP TODO

1. Usuń martwy kod pozostawiony po starym flow.
2. Nie rób szerokiego rename/refactoru, jeśli nie jest konieczny.
3. Upewnij się, że istnieje jeden model:
   - Requirement;
   - CandidateValue;
   - UserFact;
   - provenance/origin.
   Nie twórz równoległych wersji tych samych pojęć.
4. Upewnij się, że:
   - precedence originów istnieje w jednym miejscu po stronie Forge;
   - latest-user-wins istnieje w jednym miejscu po stronie ADCM/UserFact store;
   - te dwa mechanizmy nie są zduplikowane.
5. Upewnij się, że orchestrator nie modyfikuje canonical contract.
6. Upewnij się, że LLM nie ma dowolnego MCP tool loop.
7. Sprawdź `max_auto_steps` / loop guard.
8. Uruchom:
   - unit tests;
   - integration tests;
   - CLI smoke test;
   - API smoke test.
9. Jeśli dostępny jest realny MCP Streamable HTTP, uruchom smoke E2E przez prawdziwy transport.
10. Zaktualizuj:
   - `docs/CURRENT_STATE.md`;
   - `docs/ARCHITECTURE.md`, tylko jeśli rzeczywisty model różni się od opisu;
   - `docs/DECISIONS.md`, tylko jeśli podjęto trwałą nową decyzję.

## FINAL ARCHITECTURAL CHECK

Końcowy flow:

```text
USER
  ↓
ADCM ConversationMemory
  ├─ messages
  ├─ latest UserFacts
  └─ partial facts
  ↓
Forge state
  ├─ pending
  └─ overridable
  ↓
ADCM resolver
  1. known UserFact
  2. deterministic extraction
  3. partial merge
  4. LLM fallback
  5. ask user
  ↓
CandidateValue(origin=USER)
  ↓
Contract Forge
  1. schema validation
  2. precedence
  3. enrichment
  4. defaults
  5. pending discovery
  ↓
loop
```

## OUT OF SCOPE AFTER THIS SERIES

Nadal poza zakresem:
- arbitrary JSON Schema engine po stronie ADCM;
- Schema Explorer MCP;
- existing YAML editing;
- optional decisions workflow;
- web UI;
- DB session persistence;
- auth;
- multi-instance production session store;
- rozbudowany audit UI.

## DONE WHEN

Wszystkie scenariusze E2E przechodzą, dokumentacja odpowiada kodowi, a minimalny ADCM spełnia ustalone ownership i precedence bez zbędnej złożoności.
