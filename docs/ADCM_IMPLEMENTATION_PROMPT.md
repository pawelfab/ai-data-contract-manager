# Prompt implementacyjny --- rozwój ADCM do pełnej aplikacji

Jesteś głównym inżynierem odpowiedzialnym za rozwój istniejącego
repozytorium ADCM.

Twoim zadaniem jest przekształcenie dostarczonego szkieletu
architektonicznego w działającą aplikację produkcyjną, zachowując
istniejące granice odpowiedzialności i architektoniczne invarianty.

## 1. Najpierw poznaj repozytorium

Przed jakąkolwiek implementacją:

1.  Przeczytaj: `README.md`, `LLM_REPO_GUIDE.md`, całą dokumentację w
    `docs/`, kod `domain/`, `application/`, definicje `ports/`,
    istniejące adaptery i testy.
2.  Znajdź dostarczone pliki `contract.json` oraz plik/pliki enrichment
    rules.
3.  Przeanalizuj ich rzeczywistą strukturę.
4.  Nie zakładaj struktury na podstawie nazw plików lub dokumentacji,
    jeśli kod lub pliki źródłowe mówią coś innego.
5.  Przed implementacją utwórz raport opisujący: obecne działanie ADCM,
    strukturę `contract.json`, defaults, required fields,
    `x-contract-rules`, enrichment rules, reguły zależne od systemu
    źródłowego, enrichmenty globalne/defaultowe, zależności pól, etapy
    onboardingowe oraz elementy szkieletu wymagające adaptacji.

Nie implementuj niczego, dopóki analiza nie zostanie zakończona.

## 2. Fundamentalne granice odpowiedzialności

### ADCM odpowiada za

chat, sesję użytkownika, historię rozmowy, semantic interpretation,
extraction wartości z tekstu, signals, pre-path signals, cross-cutting
preferences, ValueCandidates, Evidence, revisions, audit, provenance,
rozstrzyganie kandydatów, przechowywanie draftu, orchestrację MCP,
capability routing, fast-forward workflow i prezentację odpowiedzi.

### Contract Forge MCP odpowiada za

`contract.json`, strukturę kontraktu, istniejące ścieżki,
`allowed_paths`, wymagane pola, typy, constraints, defaults,
`x-contract-rules`, enrichment rules, derived values, etapowość
onboardingu, zależności między etapami, partial validation i final
validation.

### LLM odpowiada wyłącznie za semantykę

Wykrywa intencję, ekstrahuje informacje z języka naturalnego, wykrywa
korekty i niepewność, potencjalne literówki, semantycznie dopasowuje
informacje użytkownika do aktualnie dopuszczonych concept/path
candidates oraz formułuje odpowiedź.

LLM NIE JEST źródłem prawdy dla struktury kontraktu.

## 3. Najważniejszy invariant

Schema jest autorytetem. Signal nie jest autorytetem. LLM nie może
stworzyć ścieżki kontraktu.

Żadna wartość nie może trafić do `ContractDraft`, jeśli ścieżka nie
została wcześniej uznana przez Contract Forge za legalną.

Nigdy nie implementuj `draft.set(llm_generated_path, value)`.

Poprawny przepływ:

`User text → Signal / Preference → ValueCandidate → legal path potwierdzony przez MCP → ResolvedValue → DraftProjector → ContractDraft`

## 4. Model informacji

Zachowaj rozdzielenie:

`Raw User Message → Evidence → Signal / Preference → ValueCandidate → ResolvedValue → ContractDraft`

Nie upraszczaj tego do jednego `dict`.

Signal opisuje semantyczną informację użytkownika nawet wtedy, gdy
aktualnie nie znamy ścieżki kontraktu. Może być `unbound`.

Preference reprezentuje cross-cutting preference, np. `encoding=UTF-8`
lub `encryption=disabled`. Jedna preference może później utworzyć
kandydatów dla wielu legalnych pól.

Każda konkretna propozycja wartości dla legalnej ścieżki musi być
ValueCandidate i przechowywać co najmniej: path, value, origin,
evidence, priority, status, opcjonalnie confidence i rule id.

ResolvedValue jest zwycięskim kandydatem dla konkretnego path.

ContractDraft zawiera tylko dane, które rzeczywiście mogą wejść do
kontraktu. Nie przechowuje rozmowy ani luźnych signals.

## 5. Provenance i Evidence

Obsługuj co najmniej pochodzenia: - USER_EXPLICIT - USER_PREFERENCE -
EXISTING_CONTRACT - MCP_ENRICHMENT - MCP_DERIVED - MCP_DEFAULT -
EXTERNAL_SCHEMA - EXTERNAL_REPOSITORY

Każda wartość musi mieć możliwe do prześledzenia pochodzenie, np.:
`ResolvedValue → ValueCandidate → Preference → Evidence → user message`.

Nigdy nie usuwaj historii kandydatów po override. Stara wartość ma
zostać `superseded`.

## 6. Priorytety wartości

Priorytety mają być deterministyczne i implementowane po stronie ADCM,
nie w promptach.

Domyślna relacja:
`USER_EXPLICIT > USER_PREFERENCE > EXISTING_CONTRACT > EXTERNAL/POLICY > MCP_ENRICHMENT > MCP_DERIVED > MCP_DEFAULT`

LLM nie rozstrzyga, który kandydat wygrywa.

## 7. Pre-path signals

Aplikacja musi obsługiwać informacje przekazane zanim MCP ujawni
odpowiednią ścieżkę.

Jeżeli user mówi „Pliki są rozdzielane średnikiem", a onboarding jest
dopiero na etapie systemu źródłowego, ADCM zapisuje:
`concept=field_delimiter, value=";", status=unbound`.

Dopiero gdy Contract Forge zwróci legalną ścieżkę np.
`source.delimited.delimiter`, SignalBinder może utworzyć ValueCandidate.

LLM może zaproponować binding semantyczny, ale ADCM MUSI sprawdzić, że
path znajduje się w `allowed_paths`.

## 8. Cross-cutting preferences

Jeżeli user mówi „Nie używamy szyfrowania", nie twórz automatycznie
dowolnego `encryption.enabled=false`.

Zapisz preference: `concept=encryption, value=disabled, scope=global`.

Gdy MCP ujawni legalne pola związane z encryption, PreferenceExpander
może utworzyć ValueCandidates. Nigdy nie generuj nowych ścieżek na
podstawie samej nazwy preference.

## 9. Contract Forge onboarding

Contract Forge nie powinien przekazywać agentowi całego schematu jako
listy pytań. MCP prowadzi onboarding etapami.

Rzeczywista kolejność MUSI wynikać z aktualnego `contract.json`,
enrichment rules i workflow Contract Forge. Nie hardcoduj etapów w ADCM.

Etapy mogą być dynamiczne i conditional: np. CSV może wymagać
preparatora, Parquet go pomijać, a database source używać innej ścieżki.

## 10. Nieznany system źródłowy

Brak system-specific enrichment NIE może zatrzymywać onboardingu.

Nadal stosuj global rules, defaults, source-type rules, format rules i
standardową logikę etapów wynikającą z kontraktu. `no enrichment found`
nie jest błędem.

## 11. User może podać cały kontrakt w jednym promptcie

LLM powinien wyekstrahować wszystkie możliwe informacje podczas jednego
turnu. ADCM zapisuje je jako signals/preferences/candidates.

WorkflowRunner prowadzi Contract Forge etap po etapie. Jeżeli MCP
potrzebuje wartości, którą ADCM już posiada, nie pytaj usera ---
zastosuj ją i kontynuuj.

Fast-forward powinien działać logicznie tak:

1.  get next requirements
2.  bind signals
3.  expand preferences
4.  resolve candidates
5.  submit available values
6.  jeśli naprawdę brakuje informacji użytkownika --- zatrzymaj się i
    zapytaj
7.  jeśli complete --- validate i finish

User powinien dostać pytanie tylko wtedy, kiedy po wykorzystaniu
wartości usera, preferences, enrichmentów, derived values, defaults i
external MCP results nadal brakuje wymaganej informacji.

## 12. Turn processing

Każdy turn: 1. save raw user message 2. build AgentContext 3. semantic
interpretation 4. extract signals/preferences/corrections 5. reconcile
with existing state 6. append evidence 7. run Contract Forge workflow 8.
bind pending signals 9. expand applicable preferences 10. resolve
ValueCandidates 11. project legal values to ContractDraft 12. perform
required external MCP calls 13. continue Contract Forge workflow 14.
partial/final validation 15. save revision 16. save audit 17. generate
user response

Nigdy nie generuj finalnej odpowiedzi użytkownikowi przed zakończeniem
wewnętrznego workflow dla tego turnu.

## 13. Powtarzające się informacje i korekty

SemanticInterpreter ma rozróżniać m.in.: `new_information`,
`correction`, `confirmation`, `uncertain_change`, `question`.

Jeżeli wcześniej `system=Oracle`, a user mówi „Jednak PostgreSQL",
Oracle staje się superseded, PostgreSQL active i powstaje revision.

Jeżeli user mówi „Może PostgreSQL?" i intencja nie jest pewna, nie
nadpisuj automatycznie. Zapytaj o potwierdzenie.

## 14. Literówki

LLM powinien wykrywać prawdopodobne literówki, np.
`PostgrSQL → PostgreSQL`.

Nie zmieniaj automatycznie wartości biznesowej przy istotnej
niepewności. Zapytaj: „Czy chodziło Ci o PostgreSQL?".

Jeśli polityka pozwala na auto-normalization przy bardzo wysokim
confidence, zachowaj `raw_value` i `normalized_value` w
evidence/audicie.

## 15. Pydantic AI

Pydantic AI wykorzystuj przede wszystkim jako implementację portu
`SemanticInterpreter`.

Agent ma zwracać typowany `TurnInterpretation`, zawierający co
najmniej: - intent - extracted_signals - preferences - corrections -
confirmations - possible_typos

Nie wykorzystuj głównego agenta jako workflow engine.

LLM nie decyduje: jaki etap jest następny, które pole jest required, czy
path istnieje, które enrichment jest ważniejsze, czy kontrakt jest
poprawny ani czy etap można pominąć.

## 16. Historia rozmowy

Zachowaj osobno `chat history` i `ConversationState`.

Chat history służy LLM do rozumienia kontekstu językowego.
ConversationState jest źródłem prawdy aplikacji.

Nie rekonstruuj stanu kontraktu wyłącznie z historii rozmowy przy każdym
turnie.

## 17. Porty i adaptery

Zachowaj co najmniej porty: - SemanticInterpreter - ContractForgePort -
SchemaExplorerPort - SessionRepository - AuditSink - LoggerPort

Nie importuj konkretnego providera LLM, BigQuery, GitHub ani klienta MCP
do domeny/application layer.

Adaptery mają być wymienne, np.: - SemanticInterpreter →
PydanticAIInterpreter - SessionRepository → FileSessionRepository /
przyszły DBSessionRepository - AuditSink → JsonlAuditSink / przyszły
BigQueryAuditSink - ContractForgePort → McpContractForgeAdapter

## 18. Enrichment source

Contract Forge początkowo używa enrichment rules z pliku, ale enrichment
engine nie może zależeć bezpośrednio od filesystemu.

Zachowaj port `EnrichmentRepository`.

Aktualny adapter: `JsonEnrichmentRepository`. Przyszły:
`GitHubEnrichmentRepository`. Możliwy później:
`CompositeEnrichmentRepository`.

Logika enrichmentów nie może zależeć od miejsca ich przechowywania.

## 19. Przyszłe MCP

Architektura musi umożliwiać dodanie bez przebudowy głównego workflow: -
Schema Explorer MCP - Repository/GitHub MCP - Atlassian MCP - Data
Catalog MCP - Naming Policy MCP

Użyj CapabilityRouter.

Contract Forge może zwracać zapotrzebowanie na capability, np.
`schema.table_exists`, `schema.get_columns`, `repository.find_contract`.

ADCM rozwiązuje capability poprzez odpowiedni port/adapter.

Contract Forge nie powinien bezpośrednio komunikować się ze Schema
Explorer.

## 20. Schema Explorer

Wyniki Schema Explorer nie mogą bezpośrednio modyfikować draftu.

Przepływ:
`Schema Explorer result → Evidence → ValueCandidate albo ValidationFinding → resolver → DraftProjector`.

## 21. DraftProjector

DraftProjector jest obowiązkową barierą.

Każde pole przed wpisaniem do draftu musi przejść:
`ResolvedValue + MCP/schema allowed path → ContractDraft`.

Jeżeli path nie jest legalny, nie zapisuj go do draftu i wygeneruj
diagnostic/audit event.

## 22. Walidacja

Obsłuż partial validation i final validation.

Walidację wykonuje Contract Forge. LLM może wyjaśnić błąd userowi, ale
nie może sam uznać kontraktu za valid.

## 23. Audit i revisions

Każda istotna zmiana stanu musi być możliwa do odtworzenia.

Przechowuj: - revision number - old value - new value - path/concept -
origin - evidence - trigger message - timestamp - reason

Oddziel technical logs od business audit.

## 24. Implementacja etapami

Nie implementuj wszystkiego jednym dużym patchem.

### ETAP 1 --- Discovery

Bez zmian produkcyjnych. Przeanalizuj repo, `contract.json` i enrichment
rules. Utwórz: - `docs/CURRENT_CONTRACT_ANALYSIS.md` -
`docs/IMPLEMENTATION_PLAN.md`

### ETAP 2 --- Domain adaptation

Dostosuj modele: Signal, Preference, ValueCandidate, ResolvedValue,
Evidence, Revision, ConversationState, ContractDraft. Dodaj testy
invariantów. Nie implementuj jeszcze prawdziwego MCP.

### ETAP 3 --- Contract Forge adapter

Zamień mock na realny adapter Contract Forge. Zaimplementuj mapping
odpowiedzi MCP do typów domenowych/application DTO. Nie dopuść do
przeciekania surowych struktur MCP do całej aplikacji.

### ETAP 4 --- WorkflowRunner

Zaimplementuj staged onboarding, fast-forward, missing information
detection, conditional stages, unknown source system handling, defaults,
enrichments i validation. Testuj bez LLM przy użyciu
FakeSemanticInterpreter.

### ETAP 5 --- Semantic Interpreter

Zaimplementuj pełny Pydantic AI interpreter: intent, signals,
preferences, correction, typo detection, semantic binding. Nie modyfikuj
domeny tylko po to, aby uprościć prompt.

### ETAP 6 --- persistence/audit

Dodaj session storage, revision persistence, audit, lokalny adapter i
przygotowanie pod docelową infrastrukturę.

### ETAP 7 --- API/chat

Podłącz endpointy/UI. ChatService ma być cienką warstwą.

### ETAP 8 --- end-to-end

Przetestuj pełne scenariusze.

## 25. Obowiązkowe scenariusze testowe

A. User podaje tylko system --- workflow pyta tylko o naprawdę brakujące
informacje.

B. User podaje cały kontrakt w jednej wiadomości --- ADCM wykonuje
fast-forward bez niepotrzebnych pytań.

C. User podaje separator przed wyborem typu źródła --- pozostaje unbound
signal, później zostaje poprawnie związany.

D. User mówi „zawsze UTF-8" --- preference zostaje wykorzystana później
bez ponownego pytania.

E. User mówi „nie używamy szyfrowania" --- preference wpływa na wiele
legalnych pól, ale nie tworzy nieistniejących ścieżek.

F. Contract Forge zwraca enrichment i contract default dla tego samego
pola --- enrichment wygrywa.

G. User podaje własną wartość dla pola posiadającego enrichment --- user
wygrywa, enrichment pozostaje w candidates/evidence.

H. User później zmienia wartość --- stara pozostaje superseded, powstaje
revision.

I. System źródłowy nie istnieje w system-specific enrichment ---
workflow nadal działa z global/default rules.

J. LLM wymyśla path niewystępujący w MCP allowed paths ---
DraftProjector go odrzuca.

K. Schema Explorer informuje, że tabela już istnieje --- informacja
powstaje jako evidence/finding i nie jest bezpośrednio wpisywana do
draftu.

L. LLM wykrywa `PostgrSQL` i przy odpowiedniej niepewności pyta „Czy
chodziło Ci o PostgreSQL?".

## 26. Architektoniczne invarianty

1.  No ContractDraft path without Contract Forge authorization.
2.  No ResolvedValue without at least one ValueCandidate.
3.  No ValueCandidate without origin.
4.  User-origin ValueCandidate must reference Evidence.
5.  Signal may exist without a contract path.
6.  Preference may affect zero, one or many paths.
7.  Changing a value never deletes history.
8.  LLM cannot mutate ContractDraft directly.
9.  External MCP cannot mutate ContractDraft directly.
10. Contract schema always wins over semantic inference.
11. User response is generated only after internal turn processing
    finishes.
12. Conversation history is not the authoritative application state.
13. Unknown enrichment source/system must not break generic onboarding.
14. Contract-specific paths must not be hardcoded in ADCM application
    logic.

## 27. Nie over-engineeruj

Nie dodawaj bez konkretnej potrzeby: - event bus - Kafka - CQRS
framework - pełnego Event Sourcing - Temporal - multi-agent
architecture - osobnego repository dla każdej klasy domenowej - graph
workflow tylko dlatego, że framework go oferuje

Preferuj prosty, jawny Python. Architektura ma być rozszerzalna przez
porty i typowane kontrakty, a nie przez nadmiar abstrakcji.

## 28. Dokumentacja

Po każdym etapie aktualizuj: - `README.md` - `LLM_REPO_GUIDE.md` -
`docs/ARCHITECTURE.md` - `docs/DOMAIN_MODEL.md` -
`docs/TURN_LIFECYCLE.md` - `docs/MCP_CONTRACT.md`

Jeżeli zmieni się decyzja architektoniczna, zapisz ją w
`docs/DESIGN_DECISIONS.md`.

`LLM_REPO_GUIDE.md` musi pozwalać przyszłemu agentowi zrozumieć repo bez
ponownej analizy całego kodu. Powinien zawierać aktualną architekturę,
odpowiedzialność modułów, główne klasy, przepływ turnu, dane
wejściowe/wyjściowe MCP, invarianty, miejsca rozszerzeń, aktualne
adaptery i listę rzeczy, których agent nie może robić.

## 29. Sposób pracy

Dla każdego etapu: 1. przeczytaj aktualny kod, 2. przedstaw krótki plan
zmian, 3. wskaż pliki do zmiany, 4. implementuj małymi spójnymi
patchami, 5. uruchom testy, 6. napraw wszystkie regresje, 7. wykonaj
review własnych zmian, 8. sprawdź invarianty, 9. zaktualizuj
dokumentację, 10. dopiero potem przejdź dalej.

Nie przepisuj działającego kodu bez powodu. Nie zmieniaj architektury
tylko dlatego, że inny wzorzec wydaje się bardziej elegancki. Preferuj
rozszerzenie istniejącego rozwiązania.

## 30. Pierwsze zadanie

Teraz wykonaj WYŁĄCZNIE ETAP 1 --- Discovery.

Przeanalizuj całe repozytorium oraz dostarczone: - `contract.json` -
enrichment rules

Nie implementuj jeszcze zmian aplikacji.

Przygotuj: - `docs/CURRENT_CONTRACT_ANALYSIS.md` -
`docs/IMPLEMENTATION_PLAN.md`

W `IMPLEMENTATION_PLAN.md` rozpisz konkretne zmiany w formacie:
`plik → klasa/funkcja → co zmienić → dlaczego → zależności → testy`.

Na końcu przedstaw najważniejsze ryzyka lub niezgodności między
rzeczywistym kontraktem/enrichment rules a aktualnym szkieletem ADCM.
