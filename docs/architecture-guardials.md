# Zasady rozwoju architektury — modularność, black box i rozszerzalność

## 1. Cel

Aplikacja ma być rozwijana jako zestaw małych, niezależnych modułów o jasno określonych wejściach i wyjściach.

Najważniejsze cele architektoniczne:

* łatwe dodawanie nowych funkcjonalności,
* ograniczenie wpływu zmian na istniejący kod,
* możliwość testowania modułów niezależnie,
* możliwość wymiany implementacji bez zmiany core,
* ograniczenie ilości kontekstu potrzebnego LLM do wykonania zmiany,
* brak rozlewania wiedzy o szczegółach jednego modułu na pozostałe,
* przewidywalne granice odpowiedzialności,
* łatwe diagnozowanie błędów.

Preferowany model:

```text
typed input
    │
    ▼
┌───────────────┐
│   BLACK BOX   │
└───────────────┘
    │
    ▼
typed output
```

Kod poza modułem powinien znać jego kontrakt, ale nie powinien znać szczegółów jego implementacji.

---

# 2. Podstawowa zasada

Przed dodaniem nowego feature należy odpowiedzieć:

> Czy nowa funkcjonalność może zostać dodana jako nowy moduł, port, adapter lub nowa implementacja istniejącego interfejsu bez zmiany core?

Jeżeli odpowiedź brzmi TAK, preferuj takie rozwiązanie.

Jeżeli nowy feature wymaga zmian w wielu istniejących modułach, najpierw sprawdź, czy:

* brakuje właściwej abstrakcji,
* odpowiedzialności są źle rozdzielone,
* istniejący moduł wie zbyt dużo,
* orchestrator zawiera logikę należącą do osobnego komponentu,
* konkretna integracja przeciekła do core.

Nie dodawaj automatycznie kolejnych wyjątków tylko po to, aby nowy test przeszedł.

---

# 3. Warstwy architektury

Preferowany podział:

```text
DOMAIN
   │
   ▼
APPLICATION
   │
   ▼
PORTS
   │
   ▼
ADAPTERS
```

## Domain

Zawiera:

* trwałe pojęcia domenowe,
* modele stanu,
* niezmienniki,
* fakty domenowe,
* czyste reguły niezależne od infrastruktury.

Domain NIE zna:

* MCP,
* HTTP,
* FastAPI,
* BigQuery,
* filesystem,
* PydanticAI,
* OpenAI,
* Google Cloud,
* konkretnego transportu,
* konkretnej bazy danych.

Domain powinien być możliwy do testowania bez uruchamiania infrastruktury.

---

## Application

Zawiera:

* use-case services,
* orkiestrację istniejących modułów,
* deterministyczne polityki,
* koordynację przepływu.

Application może znać:

* modele domenowe,
* porty.

Application NIE powinien znać:

* szczegółów MCP,
* klientów HTTP,
* klientów BigQuery,
* struktury filesystem,
* szczegółów konkretnego dostawcy LLM.

---

## Ports

Port definiuje:

> Czego aplikacja potrzebuje od świata zewnętrznego?

Port nie opisuje technologii.

Dobrze:

```text
ContractForgePort
SchemaExplorerPort
IntentResolverPort
SessionRepositoryPort
SessionAuditSinkPort
```

Źle:

```text
McpPort
HttpPort
BigQueryPort
OpenAIPort
```

Port powinien być nazwany zgodnie z capability lub rolą biznesową, a nie technologią transportową.

Przykład:

```python
class SchemaExplorerPort(Protocol):
    async def check_columns(...) -> ColumnCheckResult:
        ...
```

Nie:

```python
class McpClientPort(Protocol):
    async def call_tool(...):
        ...
```

---

## Adapters

Adapter odpowiada na pytanie:

> Jak technicznie realizujemy dany port?

Przykłady:

```text
ContractForgePort
    ↓
ForgeMcpAdapter
```

```text
SchemaExplorerPort
    ↓
SchemaExplorerMcpAdapter
```

```text
SessionAuditSinkPort
    ↓
LocalJsonlSessionAuditSink
```

lub:

```text
SessionAuditSinkPort
    ↓
BigQuerySessionAuditSink
```

Zmiana adaptera nie powinna wymagać zmiany domain/application.

---

# 4. Serwisy są od siebie niezależne

Każdy serwis:

* ma własne źródła,
* ma własny `pyproject.toml`,
* ma własne dependencies,
* ma własne `.venv`,
* ma własny Docker image,
* może być wdrażany niezależnie.

Aktualna struktura:

```text
/
├── docs/
├── ai-data-contract-manager/
└── mcp-servers/
    ├── mcp-contract-forge/
    └── future-mcp/
```

Nie wolno tworzyć bezpośrednich importów Python pomiędzy usługami.

Niedozwolone:

```python
from contract_forge.domain import ForgeAnalysis
```

po stronie ADCM.

Granica między usługami jest kontraktem wire-format:

```text
JSON / MCP / HTTP
```

Każdy serwis mapuje wire-format na swoje własne modele.

---

# 5. Publiczny kontrakt ważniejszy niż implementacja

Każdy większy moduł powinien mieć stabilne:

```text
INPUT
OUTPUT
ERRORS
INVARIANTS
```

Przykład:

```text
IntentResolver

INPUT:
- user message
- current document
- contract description

OUTPUT:
- IntentResolution

NIE:
- mutuje ContractState
- wykonuje Forge
- zapisuje sesję
```

Inny moduł:

```text
DocumentEngine

INPUT:
- ContractState
- MutationCommand[]

OUTPUT:
- ContractState
- MutationEvent[]

NIE:
- interpretuje tekst użytkownika
- wywołuje LLM
- zna contract.json
```

To pozwala LLM pracować nad jednym modułem bez potrzeby czytania całej aplikacji.

---

# 6. Jeden właściciel każdej odpowiedzialności

Każda istotna decyzja powinna mieć dokładnie jednego właściciela.

Przykładowo:

```text
rozumienie użytkownika
    → ADCM IntentResolver

mutowanie ContractState
    → DocumentEngine

formalna struktura kontraktu
    → Contract Forge

reguły contract.json
    → Contract Forge

reguły ADCM / ux_rules
    → ConventionRulesEngine

autorytet wartości
    → ProposalReconciler / CandidatePolicy

zewnętrzna weryfikacja schematu
    → ExternalCheckCoordinator + SchemaExplorerPort

historia sesji
    → ADCM

session audit
    → SessionAuditRecorder
```

Jeżeli ta sama decyzja zaczyna być podejmowana w kilku miejscach, należy zatrzymać implementację i poprawić granice.

---

# 7. Core nie może znać konkretnej struktury kontraktu

ADCM core powinien traktować kontrakt jako generyczny dokument JSON.

Niedozwolone w core:

```python
if path == "/metadata/sourceSystemGcpId":
```

```python
if contract.silver.tables:
```

```python
if source_type == "jdbc":
```

jeżeli wiedza ta może pochodzić z:

* Contract Forge,
* `contract.json`,
* `ux_rules`,
* konfiguracji.

Core powinien operować na generycznych pojęciach:

```text
JsonPointer
MutationCommand
Proposal
Requirement
Diagnostic
FieldPolicy
ExternalCheckDescriptor
```

Nowa wersja `contract.json` nie powinna wymagać zmian w ADCM core.

---

# 8. Preferuj dane i konfigurację zamiast kolejnych `if`

Jeżeli różnice pomiędzy systemami lub wariantami można opisać jako dane, nie koduj ich w orchestratorze.

Preferowane:

```json
{
  "system": "sap",
  "path": "/source/sourceType",
  "value": "csv"
}
```

zamiast:

```python
if source_system == "sap":
    source_type = "csv"
```

Analogicznie:

```text
external_checks
priority
scope
conditions
templates
```

powinny być konfiguracją, jeśli ich semantyka jest już obsługiwana przez istniejący engine.

---

# 9. Reguła „proposal, nie mutation”

Komponenty wyliczające automatyczne wartości nie powinny bezpośrednio modyfikować dokumentu.

Dotyczy:

* Forge enrichment,
* Forge defaults,
* ADCM rules,
* user rules.

Powinny zwracać:

```text
Proposal
```

Dopiero dedykowany mechanizm:

```text
ProposalReconciler
```

decyduje:

```text
APPLY
KEEP_CURRENT
REJECT
```

i tworzy:

```text
MutationCommand
```

Dopiero:

```text
DocumentEngine
```

zmienia dokument.

Preferowany przepływ:

```text
RULE / FORGE
     ↓
Proposal
     ↓
ProposalReconciler
     ↓
MutationCommand
     ↓
DocumentEngine
     ↓
MutationEvent
```

Nie wolno omijać tego przepływu.

---

# 10. LLM nie jest właścicielem procesu

LLM służy do zadań niedeterministycznych:

* rozumienie języka użytkownika,
* mapowanie intencji,
* semantic advice,
* redakcja odpowiedzi.

LLM nie powinien decydować:

* czy wywołać Forge,
* czy uruchomić fixed-point,
* jak zastosować proposal,
* jaki autorytet ma wartość,
* czy external check jest obowiązkowy,
* jak wykonać mutation.

LLM zwraca ustrukturyzowany wynik.

Przykład:

```text
PydanticAI
    ↓
IntentResolution
```

Reszta jest deterministyczna.

---

# 11. Pydantic jako kontrakt między black boxami

Preferuj jawne modele Pydantic dla wejść i wyjść większych modułów.

Przykłady:

```text
IntentResolution
MutationCandidate
MutationCommand
MutationEvent
ForgeAnalysis
ForgeProposal
ProposalDecision
ExternalCheckResult
TurnOutcome
```

Nie przekazuj pomiędzy modułami nieudokumentowanych `dict[str, Any]`, jeżeli struktura jest stabilna i ma znaczenie dla kontraktu modułu.

Wyjątkiem jest sam dokument kontraktu, którego struktura jest zewnętrzna i dynamiczna.

---

# 12. Nowy feature powinien rozszerzać system, nie przebudowywać istniejące moduły

Przykład: nowy Schema Explorer.

Preferowane:

```text
ExternalCheckCoordinator
        │
        ▼
SchemaExplorerPort
        │
        ▼
SchemaExplorerMcpAdapter
```

Nie:

```text
TurnOrchestrator
    if columns:
        call schema explorer

    if table:
        call schema explorer
```

Dodanie kolejnego MCP powinno oznaczać przede wszystkim:

```text
new port / capability
new adapter
configuration
registration
tests
```

a nie rozbudowę istniejącego orchestratora.

---

# 13. Opcjonalne integracje muszą być fail-open

Dodatkowe usługi typu:

```text
Schema Explorer
Jira
Data Catalog
future Context MCP
```

nie mogą zatrzymywać podstawowego działania ADCM, chyba że konkretna capability jest jawnie oznaczona jako obowiązkowa.

Preferowany rezultat:

```text
provider disabled
    ↓
check = SKIPPED
    ↓
core działa dalej
```

Nie:

```text
provider disabled
    ↓
exception
    ↓
tura nie działa
```

Forge jest wyjątkiem, jeśli jest wymaganym elementem core workflow.

---

# 14. Orchestrator ma być cienki

`TurnOrchestrator` powinien:

* wywołać moduły w odpowiedniej kolejności,
* przekazywać ich wyniki,
* składać wynik tury.

Nie powinien implementować szczegółowej logiki biznesowej.

Jeżeli orchestrator zaczyna zawierać wiele:

```python
if ...
elif ...
if source_system ...
if complete ...
if optional_section ...
```

jest to sygnał, że logika powinna zostać wydzielona do osobnego black boxa.

---

# 15. Nie twórz abstrakcji bez potrzeby

Modularność NIE oznacza tworzenia klasy dla każdej funkcji.

Nie twórz automatycznie:

```text
Manager
Factory
Coordinator
Dispatcher
Handler
Processor
Service
Facade
Registry
```

jeżeli nie ma dla nich jasno określonej odpowiedzialności.

Nowa abstrakcja powinna istnieć tylko wtedy, gdy:

* izoluje zmienną część systemu,
* wyznacza granicę odpowiedzialności,
* umożliwia wymianę implementacji,
* znacząco upraszcza istniejący moduł,
* jest potrzebna przez więcej niż jeden use case.

Preferuj najprostsze rozwiązanie spełniające granice architektoniczne.

---

# 16. Zasada minimalnego wpływu zmiany

Przed implementacją feature określ:

```text
który moduł jest właścicielem zmiany
```

Następnie dąż do:

```text
1 główny moduł
+
jego testy
+
ewentualny nowy adapter/port
```

Jeżeli feature wymaga zmian w:

```text
orchestrator
domain
Forge
rules engine
session
API
adapterach
```

jednocześnie, najpierw sprawdź, czy granice są właściwe.

Duży blast radius jest sygnałem ostrzegawczym.

---

# 17. Zasada rozszerzenia przed modyfikacją

Przy nowym feature preferuj:

```text
dodanie nowego modułu
```

nad:

```text
rozbudową istniejącego dużego modułu
```

jeżeli nowy feature ma własną odpowiedzialność.

Przykład:

```text
SessionAuditRecorder
```

jest lepszy niż dodawanie kilkudziesięciu instrukcji logujących bezpośrednio do `TurnOrchestrator`.

---

# 18. Testowanie black box

Każdy większy komponent powinien mieć testy jego publicznego kontraktu.

Przykład:

```text
INPUT
    ↓
ConventionRulesEngine
    ↓
OUTPUT RuleProposal[]
```

Test nie powinien wymagać:

* FastAPI,
* prawdziwego MCP,
* BigQuery,
* prawdziwego LLM,

jeżeli nie są one przedmiotem testu.

Dodatkowo wymagane są testy integracyjne granic:

```text
ADCM → Forge
ADCM → MCP adapter
Port → Adapter
```

Nie polegaj wyłącznie na mockach.

---

# 19. Test architektury

Tam gdzie jest to możliwe, zabezpieczaj reguły architektury automatycznie.

Przykłady:

ADCM core nie może importować:

```text
google.cloud
mcp
fastapi
contract_forge
```

Forge nie może importować:

```text
adcm
pydantic_ai
```

ADCM core nie może zawierać konkretnych ścieżek kontraktu:

```text
sourceSystemGcpId
silver.tables
gold.entries
```

jeżeli wiedza ta należy do konfiguracji lub Forge.

---

# 20. Nowe use case nie usprawiedliwiają specjalnych wyjątków

Jeżeli nowy test nie przechodzi, NIE stosuj automatycznie:

```python
if special_case:
    ...
```

Najpierw sklasyfikuj problem:

```text
A. istniejący mechanizm działa błędnie
B. konfiguracja jest niepełna
C. adapter działa błędnie
D. brakuje nowego trwałego pojęcia domenowego
E. architektura ma złą granicę
```

Dopiero D lub E mogą uzasadniać rozszerzenie core.

---

# 21. Kiedy zatrzymać implementację

Agent powinien przerwać implementację i zgłosić problem, jeśli:

* feature wymaga konkretnej ścieżki kontraktu w ADCM core,
* jeden moduł zaczyna znać szczegóły implementacyjne innego modułu,
* wymagany jest bezpośredni import pomiędzy serwisami,
* potrzebne są liczne specjalne przypadki w orchestratorze,
* implementacja wymaga obejścia istniejącego portu zamiast jego użycia,
* dwa moduły zaczynają posiadać tę samą odpowiedzialność,
* wymagane jest znaczące zwiększenie złożoności tylko dla jednego use case,
* trzeba zmienić publiczny kontrakt kilku black boxów dla lokalnej funkcjonalności,
* test przechodzi tylko po dodaniu zachowania specyficznego dla konkretnego przykładu.

W takiej sytuacji agent NIE powinien „dowieźć testu za wszelką cenę”.

Powinien zgłosić:

```text
- problem,
- dlaczego obecna abstrakcja nie wystarcza,
- proponowaną nową abstrakcję,
- wpływ na istniejące moduły,
- prostszą alternatywę, jeśli istnieje.
```

---

# 22. Procedura dodawania nowego feature

Przed kodowaniem wykonaj kolejno:

## Krok 1 — znajdź właściciela

Określ:

```text
który istniejący moduł powinien odpowiadać za feature?
```

Jeśli żaden — zaproponuj nowy black box.

---

## Krok 2 — zdefiniuj kontrakt

Przed implementacją określ:

```text
INPUT
OUTPUT
SIDE EFFECTS
ERRORS
INVARIANTS
```

---

## Krok 3 — oceń zależności

Feature powinien zależeć od:

```text
portów
```

a nie od:

```text
konkretnych adapterów
```

---

## Krok 4 — oceń wpływ na core

Odpowiedz:

```text
Czy core wymaga zmiany?

Jeśli tak:
- dlaczego?
- jakie nowe trwałe pojęcie powstaje?
- czy zamiast tego wystarczy adapter/configuration?
```

---

## Krok 5 — implementuj moduł osobno

Najpierw:

```text
model
port
application logic
unit tests
```

Dopiero później integracja z orchestrator/composition root.

---

## Krok 6 — integracja

Połączenie z aplikacją powinno być małe.

Preferowane:

```text
composition root
    ↓
inject new component
```

Nie:

```text
przebudowa całego orchestratora
```

---

## Krok 7 — regresja

Po zmianie uruchom:

```text
unit tests
integration tests
architecture tests
existing business scenarios
```

Nowy feature nie może zmieniać wcześniejszego zachowania bez jawnej decyzji biznesowej.

---

# 23. Wymagany opis planu implementacyjnego

Przed implementacją większego feature agent powinien podać:

```text
## Ownership
Który moduł jest właścicielem feature.

## New black boxes
Jakie nowe moduły powstaną.

## Inputs / Outputs
Kontrakty nowych modułów.

## Ports
Nowe lub zmieniane porty.

## Adapters
Nowe implementacje infrastrukturalne.

## Existing modules touched
Lista istniejących modułów, które trzeba zmienić.

## Core impact
Czy core się zmienia i dlaczego.

## Risks
Ryzyka architektoniczne.

## Tests
Jak zostanie sprawdzona niezależność modułu.
```

Jeżeli sekcja `Existing modules touched` jest duża, agent powinien przed kodowaniem sprawdzić możliwość uproszczenia rozwiązania.

---

# 24. Kryterium dobrej modularności

Architektura jest właściwa, jeśli dla większości nowych funkcjonalności można powiedzieć:

```text
dodaliśmy nowy klocek
+
podłączyliśmy go przez istniejący port lub nowy mały port
+
core pozostał bez zmian
```

Przykład:

```text
nowy Schema Explorer
```

powinien oznaczać głównie:

```text
SchemaExplorerPort
SchemaExplorerMcpAdapter
ExternalCheck configuration
tests
```

Nie przebudowę kontraktu, stabilizacji i orchestratora.

---

# 25. Kryterium black box dla LLM

Agent pracujący nad jednym modułem powinien w większości przypadków potrzebować przeczytać:

```text
jego modele
jego port
jego implementację
jego testy
kontrakty bezpośrednich sąsiadów
```

a nie całe repozytorium.

Jeżeli do każdej małej zmiany konieczne jest zrozumienie całego systemu, granice modułów są zbyt słabe.

---

# 26. Niezmienniki architektoniczne

Traktuj poniższe zasady jako domyślne i obowiązujące dla wszystkich nowych feature:

1. Jeden właściciel jednej odpowiedzialności.
2. Core nie zna infrastruktury.
3. Core nie zna konkretnego `contract.json`.
4. LLM nie mutuje stanu.
5. Adapter nie zawiera logiki domenowej.
6. Port opisuje capability, nie technologię.
7. Serwisy nie importują się wzajemnie.
8. Integracje opcjonalne nie blokują core.
9. Automatyczne źródła wartości generują proposals, nie mutacje.
10. Tylko właściciel mutacji zmienia `ContractState`.
11. Orchestrator koordynuje, ale nie przejmuje logiki modułów.
12. Nowy use case nie jest automatycznym uzasadnieniem dla nowego `if`.
13. Konfiguracja jest preferowana dla różnic danych i wariantów.
14. Publiczne kontrakty modułów mają być małe i stabilne.
15. Zmiana implementacji black boxa nie powinna wpływać na jego klientów.
16. Każdy ważny moduł musi dać się testować niezależnie.
17. Jeżeli prosty feature powoduje duży blast radius, zatrzymaj implementację i oceń architekturę.
18. Nie twórz abstrakcji bez konkretnej potrzeby.
19. Prostota jest ważniejsza niż liczba warstw.
20. Kod powinien być zoptymalizowany pod przyszłą czytelność i zmianę, nie tylko pod przejście aktualnego testu.

---

# 27. Zasada końcowa dla agentów LLM

Podczas implementacji nie optymalizuj kodu wyłącznie pod aktualne testy.

Celem jest:

```text
poprawny feature
+
zachowanie granic
+
mały wpływ na istniejący system
+
łatwa możliwość kolejnego rozszerzenia
```

Jeżeli najszybsza implementacja pogarsza modularność, zwiększa sprzężenie lub tworzy specjalny przypadek w core, wybierz prostsze architektonicznie rozwiązanie albo zgłoś konieczność zmiany abstrakcji przed implementacją.
