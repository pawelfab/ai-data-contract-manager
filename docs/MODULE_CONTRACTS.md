# Black-box module contracts

## ADCM application

| Black box | Input | Output | Nie może robić |
|---|---|---|---|
| `IntentResolverPort` | user message + current document + neutral Forge description | raw `IntentResolution` | mutować dokumentu, decydować o dopuszczeniu candidates do mutacji |
| `IntentResolutionPolicy` | raw `IntentResolution` | `EffectiveIntentResolution` | mutować dokumentu, oceniać confidence lub znać schema path |
| `CandidatePolicy` | `ContractState` + candidates | `MutationCommand[]` | znać konkretnego schema path |
| `DocumentEngine` | `ContractState` + commands | `MutationEvent[]` + nowy stan | walidować contract.json |
| `ConventionRulesEngine` | effective rules + state + `ForgeAnalysis` | `Proposal[]` | mutować dokumentu |
| `ProposalReconciler` | state + proposals | commands + decisions | znać SAP/CSV/silver itd. |
| `StabilizationEngine` | state + effective rules | final `ForgeAnalysis` + report | redagować odpowiedzi usera |
| `ExternalCheckCoordinator` | stable document | external check status/findings | mutować kontraktu |
| `ResponseComposerPort` | `TurnOutcome` | jedna odpowiedź | zmieniać stan |
| `SessionService` | brak (create) / `session_id` (get) | `SessionState`; `SessionNotFoundError` gdy brak | prowadzić turę, znać HTTP |
| `TurnOrchestrator` | `session_id` + user message + `correlation_id` | `TurnOutcome` | znać transport, tworzyć sesję na żądanie klienta |

## ADCM adapters

| Black box | Input | Output | Nie może robić |
|---|---|---|---|
| `adapters/api` (REST API v1) | HTTP request | HTTP response wg publicznych DTO | zawierać logiki domenowej, mutować `ContractState`, interpretować wiadomości, wywoływać Forge poza orchestratorem, przechowywać sesje, ustalać formatu `session_id`, zapisywać biznesowych eventów Session Audit |

Adapter API zwraca wyłącznie: `message`, `document`, `contract_status`, `missing`,
`diagnostics`, `unresolved`, `changes`, `correlation_id`. Modele domenowe nie są
serializowane bezpośrednio.

## ADCM ports

- `ContractForgePort.analyze(document) -> ForgeAnalysis`
- `ContractForgePort.describe() -> ForgeDescription`
- `SessionRepositoryPort.get(session_id) -> SessionState | None`
- `SessionRepositoryPort.get_or_create/save`
- `RulesRepositoryPort.load(session_id) -> RulesDocument`

`get` odróżnia odczyt istniejącej sesji od `get_or_create`, które sesję materializuje.
Odczyt przez API musi używać `get`, żeby brak sesji był błędem, a nie cichym utworzeniem.

## ADCM domain

`TurnSnapshot` = stan dokumentu po turze + formalna ocena dokładnie tego stanu
(`contract_status`, `missing`, `diagnostics`). Celowo nie przechowuje całej
`ForgeAnalysis`: `writable` i `proposals` opisują możliwe kolejne kroki, a nie stan,
w którym sesja się zatrzymała. Dzięki temu odczyt stanu sesji nie wymaga Contract Forge.

`TurnOutcome.unresolved` przenosi wynik `IntentResolver` przez warstwę application,
żeby informacja o niezrozumianym fragmencie wypowiedzi nie kończyła się w Session Audit.

`IntentResolution` jest niezmienianym wynikiem resolvera zapisywanym w Session Audit.
`IntentResolutionPolicy` tworzy osobny `EffectiveIntentResolution`: dla `KNOWLEDGE`
usuwa candidates i wymaga `knowledge_query`, dla `MUTATION` usuwa `knowledge_query`,
dla `MIXED` zachowuje candidates i wymaga `knowledge_query`, a dla `UNRESOLVED` nie
dopuszcza żadnego kanału i zapewnia powód. Niespójne `KNOWLEDGE` lub `MIXED` degraduje
się bezpiecznie do effective `UNRESOLVED`. `CandidatePolicy` otrzymuje wyłącznie
effective candidates, nie zna `IntentKind` i nie jest wywoływane dla `UNRESOLVED`.

`TurnOutcome.intent_kind` jest wewnętrznym wynikiem effective policy dla
`ResponseComposerPort`. Nie jest częścią publicznego REST DTO. `BasicResponseComposer`
dla `UNRESOLVED` zwraca prośbę o doprecyzowanie zamiast statusu kontraktu lub YAML.

## Contract Forge

| Black box | Input | Output |
|---|---|---|
| `ContractDefinitionPort` | brak | `ContractDefinition` |
| `ContractDefinitionNormalizer` | raw external definition | neutral wrapper schema + enrichments |
| `ContractAnalyzer` | document | writable/missing/foreign/proposals/diagnostics/status |
| `ContractDescriber` | definition | neutral field descriptors |

Forge nigdy nie dostaje conversation history, provenance, user rules ani session state.
