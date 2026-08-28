# Black-box module contracts

## ADCM application

| Black box | Input | Output | Nie może robić |
|---|---|---|---|
| `IntentResolverPort` | user message + current document + neutral Forge description | `IntentResolution` | mutować dokumentu |
| `CandidatePolicy` | `ContractState` + candidates | `MutationCommand[]` | znać konkretnego schema path |
| `DocumentEngine` | `ContractState` + commands | `MutationEvent[]` + nowy stan | walidować contract.json |
| `ConventionRulesEngine` | effective rules + state + `ForgeAnalysis` | `Proposal[]` | mutować dokumentu |
| `ProposalReconciler` | state + proposals | commands + decisions | znać SAP/CSV/silver itd. |
| `StabilizationEngine` | state + effective rules | final `ForgeAnalysis` + report | redagować odpowiedzi usera |
| `ExternalCheckCoordinator` | stable document | external check status/findings | mutować kontraktu |
| `ResponseComposerPort` | `TurnOutcome` | jedna odpowiedź | zmieniać stan |

## ADCM ports

- `ContractForgePort.analyze(document) -> ForgeAnalysis`
- `ContractForgePort.describe() -> ForgeDescription`
- `SessionRepositoryPort.get_or_create/save`
- `RulesRepositoryPort.load(session_id) -> RulesDocument`

## Contract Forge

| Black box | Input | Output |
|---|---|---|
| `ContractDefinitionPort` | brak | `ContractDefinition` |
| `ContractDefinitionNormalizer` | raw external definition | neutral wrapper schema + enrichments |
| `ContractAnalyzer` | document | writable/missing/foreign/proposals/diagnostics/status |
| `ContractDescriber` | definition | neutral field descriptors |

Forge nigdy nie dostaje conversation history, provenance, user rules ani session state.
