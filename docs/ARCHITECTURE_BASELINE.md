# Architecture baseline

## Monorepo

```text
root/
├── docs/
├── ai-data-contract-manager/
└── mcp-servers/
    └── mcp-contract-forge/
```

Każdy serwis jest niezależnym projektem Pythona.

## ADCM

Warstwy:

- `domain` — modele Pydantic niezależne od transportu i konkretnego kontraktu,
- `application` — deterministyczne use-case/core engines,
- `ports` — interfejsy black-box,
- `adapters` — MCP, HTTP, plik konfiguracyjny, LLM.

Przepływ tury:

```text
User message
  -> IntentResolverPort
  -> MutationCandidate
  -> DocumentEngine
  -> StabilizationEngine
       -> ContractForgePort.analyze
       -> ConventionRulesEngine
       -> ProposalReconciler
       -> DocumentEngine
       -> repeat until fixed point
  -> ExternalCheckCoordinator (na razie pusty)
  -> ResponseComposerPort
```

## Forge

Forge otrzymuje z ADCM tylko aktualny `document`. Definicję kontraktu pobiera przez `ContractDefinitionPort`.
Obecnie adapter czyta plik. Późniejszy adapter API może zastąpić źródło bez zmiany application/domain Forge.

Forge wystawia MCP tools:

- `contract_analyze(document)`
- `contract_describe()`

## Wire boundary

Modele po obu stronach są celowo zdefiniowane oddzielnie. To wymusza brak współdzielonego pakietu Python.
Kompatybilność jest pilnowana przez `protocol_version` oraz testy/fixture JSON.

## Pydantic i PydanticAI

Pydantic jest używany do wszystkich wejść/wyjść black-boxów i stanu domenowego.
PydanticAI jest przewidziany jako adapter `IntentResolverPort`/semantic advisor/response composer. W baseline domyślnie działa
heurystyczny resolver bez klucza API, żeby uruchomienie infrastruktury było deterministyczne.
