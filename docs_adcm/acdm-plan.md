# Status i roadmapa ACDM

Ten plik opisuje wyłącznie stan etapów. Aktualna architektura i zachowanie są
opisane w `architecture.md` oraz `agent-workflow.md`.

## Wykonane

- jeden agent Pydantic AI `turn_orchestrator`;
- lokalna aplikacja Starlette z `Agent.to_web()`;
- konfiguracja modelu, transportu i audytu z `.env`;
- aktywny katalog source/target pobierany z MCP;
- typowany `ContractState` i port `SessionStatePort`;
- deterministyczne patche ograniczone do `allowed_paths`;
- wymagane i opcjonalne pola z opisami oraz przykładami;
- walidacja MCP z limitem automatycznych napraw;
- generowanie i tekstowe zatwierdzanie YAML;
- append-only audit JSONL oraz testowalny decision trace;
- współdzielona sesja MCP stdio uruchamiana i zamykana z aplikacją;
- modułowy podział fabryki agenta, narzędzi i audytu.

## Następne etapy

### Trwały stan

- adapter SQLite albo PostgreSQL dla `SessionStatePort`;
- optimistic locking lub atomowa aktualizacja sesji;
- odtwarzanie aktywnego draftu po restarcie;
- retencja i rotacja logów audytowych.

### Kontekst i załączniki

- kontrolowane ograniczanie długiej historii;
- bezpieczny upload plików;
- artifact store, hash i limity rozmiaru;
- typowane evidence z dokumentów.

### Funkcje odłożone

- Schema Advisor jako osobny port i osobny MCP;
- własny frontend oparty na UI Event Stream;
- uwierzytelnianie i autoryzacja użytkowników;
- produkcyjny transport Streamable HTTP.

Schema Advisor i własny wygląd UI nie są częścią obecnego etapu.
