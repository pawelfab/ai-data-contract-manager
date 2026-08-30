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
- deterministyczna `IntentResolutionPolicy` oddzielająca raw wynik resolvera od
  candidates dopuszczonych do `CandidatePolicy`,
- jawny `UNRESOLVED` z wymaganym powodem, pominięciem `CandidatePolicy` i odpowiedzią
  proszącą użytkownika o doprecyzowanie,
- podstawowa odpowiedź tekstowa i YAML dla `valid && complete`,
- stabilne REST API v1 jako jedyny interfejs wejściowy ADCM,
- testy jednostkowe obu usług, testy kontraktu API i test kompatybilności wire-format.

## REST API v1

Publiczny kontrakt HTTP (OpenAPI pod `/docs` i `/openapi.json`):

```text
GET  /health                            -> {"status": "ok", "service": "adcm"}
POST /v1/sessions                       -> 201 {session_id, turn_no, status}
GET  /v1/sessions/{session_id}          -> 200 | 404
POST /v1/sessions/{session_id}/turns    -> 200 | 404 | 422 | 503
POST /v1/sessions/{session_id}/turn     -> deprecated alias dla /turns
GET  /v1/debug/sessions/{session_id}    -> tylko przy ADCM_DEBUG_API=true
```

Identyfikator sesji generuje ADCM (`SessionService`), a nie klient — format identyfikatora
nie jest częścią kontraktu publicznego.

Odpowiedź tury zawiera wyłącznie to, co potrzebne klientowi: `message`, `document`,
`contract_status`, `missing`, `diagnostics`, `unresolved`, `changes`, `correlation_id`.
Pełny `ForgeAnalysis` (`writable`, `foreign`, `proposals`), przebieg stabilizacji,
`external_checks`, `provenance` i `mutation_log` pozostają modelami wewnętrznymi —
dostępnymi w Session Audit oraz przez debug endpoint.

`unresolved` przenosi wynik `IntentResolver` do odpowiedzi, dzięki czemu informacja
o niezrozumianym fragmencie wypowiedzi nie ginie między application a API.

`GET /v1/sessions/{id}` czyta ostatni `TurnSnapshot` i nie wywołuje Contract Forge —
działa również, gdy Forge jest niedostępny. Sesja bez żadnej tury ma `contract_status: null`.

Błędy mają jeden kształt niezależnie od statusu:

```json
{"error": {"code": "...", "message": "...", "correlation_id": "..."}}
```

Kody: `session_not_found` (404), `validation_error` (422),
`contract_forge_unavailable` (503), `internal_error` (500).
Odpowiedź nigdy nie zawiera stack trace, adresu Forge ani internals MCP —
szczegóły techniczne trafiają wyłącznie do application logu.

Aplikację buduje fabryka `adcm.adapters.api.composition:build_app` (uvicorn `--factory`);
import modułu nie czyta środowiska i nie tworzy zasobów.

## Intentionally not implemented yet

- pełne dopasowanie do produkcyjnego, zewnętrznego `contract.json`,
- pełna semantyka jego `x-contract-enrichment`, oneOf/discriminator i wszystkich x-contract-rules,
- user-specific `ux_rules` z przeglądarki i merge z default rules,
- regex/valueFrom/concat/lower/upper oraz bogatszy expression engine,
- `fieldPolicies` i external check capabilities,
- Schema Explorer MCP i inne Context MCP,
- Web UI korzystające z REST API v1,
- uwierzytelnianie, autoryzacja, CORS i rate limiting w API,
- streaming odpowiedzi (SSE/WebSocket) i endpointy `history`/`audit`,
- trwały storage sesji,
- semantyczne restore typu „wróć do dataFileId, które podałem wcześniej”,
- semantic advisor,
- pełny PydanticAI intent resolver jako domyślny tryb,
- bezpieczne wycofanie automatycznie aktywowanego całego subtree, jeżeli ma potomka o wyższym autorytecie,
- pełne SC-01..SC-22 / EC-01..EC-14 jako E2E.

## Observability implemented

- niezależne application logging w ADCM i Contract Forge,
- session audit w ADCM,
- lokalne sinki JSONL oraz opcjonalne sinki BigQuery,
- techniczny `correlation_id` propagowany przez wywołanie MCP,
- batchowanie auditów BigQuery per tura przy evencie terminalnym,
- redakcja sekretów przed zapisem,
- best-effort policy: awaria logowania nie zatrzymuje business flow, a awaria
  session audit emituje dodatkowo application error.

## Known baseline limitations

`resources/contract.json` w Forge jest wyłącznie lokalnym fixture. Nie jest zamiennikiem ani kopią właścicielskiego `contract.json`.
`ContractDefinitionNormalizer` jest celowym adapterem/seamem, który trzeba dopasować do rzeczywistego formatu bez przenoszenia tej wiedzy do ADCM.

Natural-language aliases may map to the semantically closest writable field. In particular, phrases such as “system źródłowy” may be resolved to /source/systemZrodlowy instead of /metadata/sourceSystemGcpId. This is currently accepted as a known limitation of the LLM resolver and should not trigger core architecture changes.
