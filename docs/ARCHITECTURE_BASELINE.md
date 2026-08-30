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

Adapter HTTP (`adapters/api/`) jest jedynym oficjalnym interfejsem wejściowym.
Web UI nie jest częścią core i nie ma własnego portu — korzysta wyłącznie z REST API.

```text
Web UI
   │  HTTP/JSON
   ▼
adapters/api          app.py (create_app + route'y)
                      models.py (publiczne DTO)
                      mappers.py (core -> DTO)
                      errors.py (kontrakt błędu)
                      composition.py (build_app: ENV -> obiekty)
   │
   ▼
application           TurnOrchestrator, SessionService
   │
   ▼
ports                 SessionRepositoryPort, ContractForgePort, IntentResolverPort, ...
```

Adapter nie zawiera logiki biznesowej. Jego odpowiedzialność to:
walidacja żądania, mapowanie na wejście application, wywołanie application,
mapowanie wyniku i odpowiedź HTTP.

Modele domenowe nie są kontraktem publicznym — `adapters/api/models.py` definiuje
osobne DTO, a `mappers.py` decyduje, co z wyniku tury jest widoczne na zewnątrz.

`composition.py` jest jedynym miejscem, w którym konfiguracja środowiska staje się
obiektami. `build_app()` jest fabryką, więc import modułów adaptera nie ma efektów
ubocznych i cały adapter da się przetestować bez ENV, MCP i dysku.

Przepływ tury:

```text
User message
  -> IntentResolverPort
  -> IntentResolution (raw, audytowalny wynik resolvera)
  -> IntentResolutionPolicy
  -> EffectiveIntentResolution
  -> CandidatePolicy (pomijany dla UNRESOLVED)
  -> DocumentEngine (brak user commands dla UNRESOLVED)
  -> StabilizationEngine
       -> ContractForgePort.analyze
       -> ConventionRulesEngine
       -> ProposalReconciler
       -> DocumentEngine
       -> repeat until fixed point
  -> ExternalCheckCoordinator (na razie pusty)
  -> ResponseComposerPort (prośba o doprecyzowanie dla UNRESOLVED)
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
