# Przewodnik po implementacji logowania i audytu sesji

## 1. Cel dokumentu

Ten dokument opisuje stan implementacji obserwowalności po wdrożeniu modułu
logowania. Jest przeznaczony dla nowej osoby oraz kolejnej sesji LLM, która
ma zrozumieć kod bez odtwarzania architektury wyłącznie na podstawie nazw klas.

Dokument odpowiada na cztery pytania:

1. co jest logiem aplikacyjnym, a co audytem sesji,
2. gdzie i dlaczego powstają zdarzenia,
3. jakie zmiany były potrzebne poza katalogami `observability` i `logging`,
4. czy implementacja jest zgodna z `docs/architecture-guardials.md` i czy nie
   zawiera sygnałów overengineeringu.

Opis dotyczy bieżącego kodu. Sekcja 14 oddziela stan zaimplementowany od
rekomendowanych uproszczeń.

## 2. Najkrótszy model mentalny

W systemie istnieją dwa różne strumienie obserwowalności:

| Strumień | Pytanie, na które odpowiada | Właściciel | Usługi |
|---|---|---|---|
| Application log | „Czy proces i integracje działają technicznie?” | `AppLogRecorder` danej usługi | ADCM i Contract Forge |
| Session audit | „Co wydarzyło się w konkretnej turze i dlaczego zmienił się kontrakt?” | `SessionAuditRecorder` w ADCM | tylko ADCM |

Granica domenowa pozostaje następująca:

```text
DOMAIN
ContractState + MutationEvent + ValueProvenance
                    |
                    | mapowanie faktów i decyzji
                    v
OBSERVABILITY
SessionAuditEvent + AppLogEvent
```

`MutationEvent` jest faktem domenowym: dokument rzeczywiście został zmieniony.
`SessionAuditEvent` jest technicznym zapisem przebiegu tury. `AppLogEvent` jest
technicznym zapisem działania procesu. Modele logowania nie znajdują się w
`domain/` i nie są częścią domeny kontraktu.

Awaria wywołania sinka działa w trybie fail-open. Recorder przechwytuje wyjątek
adaptera, aby niedostępny plik lub BigQuery nie zmieniły wyniku biznesowego.
Nie jest to jednak pełna gwarancja dla całego procesu tworzenia eventu: błąd
walidacji modelu albo serializacji payloadu może obecnie wystąpić przed blokiem
chroniącym wywołanie sinka.

## 3. Rozmieszczenie odpowiedzialności

### 3.1 ADCM

```text
src/adcm/
  application/observability/
    models.py                  # AppLogEvent, SessionAuditEvent
    app_log_recorder.py        # budowa AppLogEvent i polityka fail-open
    session_audit_recorder.py  # związanie kontekstu tury i emisja audytu
    sanitizer.py               # wspólna redakcja sekretów

  ports/
    app_log_sink.py            # AppLogSinkPort.emit(AppLogEvent)
    session_audit_sink.py      # SessionAuditSinkPort.emit(SessionAuditEvent)

  adapters/logging/
    local_app_log_sink.py
    local_session_audit_sink.py
    bigquery_app_log_sink.py
    bigquery_session_audit_sink.py
    sanitizer.py               # publiczny re-export sanitizera application

  adapters/api/app.py          # wybór backendu i composition root
```

Warstwa application tworzy poprawne zdarzenie i określa reakcję na błąd
sinka. Port określa jedną wymaganą zdolność: `emit`. Adapter odpowiada za
konkretny zapis do JSONL albo BigQuery.

### 3.2 Contract Forge

Forge ma własne, niezależne modele, recorder, port i adaptery application log.
Nie importuje kodu ADCM. Duplikacja małych modeli i recorderów jest celowa,
ponieważ niezależność usług jest ważniejsza niż współdzielony pakiet
techniczny.

Forge nie ma `SessionAuditEvent`. Nie jest właścicielem rozmowy ani sesji.
Rejestruje konfigurację podczas bootstrapu oraz techniczne rozpoczęcie,
zakończenie i błąd narzędzi `contract_analyze` i `contract_describe`.

## 4. Kontrakty zdarzeń

### 4.1 `AppLogEvent`

Model zawiera:

- `event_id` i znacznik czasu UTC,
- `level`, `service`, `environment`, `component` i `event`,
- opcjonalne `message`, `correlation_id`, `session_id`, `turn_no` i
  `duration_ms`,
- rozszerzalny słownik `data`.

To jest zdarzenie operacyjne. Nie powinno służyć do odtwarzania pełnej historii
zmian kontraktu.

### 4.2 `SessionAuditEvent`

Model zawiera:

- `event_id` i znacznik czasu UTC,
- wymagane `session_id`, `turn_no` i `event_type`,
- opcjonalne `correlation_id`,
- rozszerzalny słownik `data`.

Recorder jest wiązany z turą:

```python
audit = session_audit.bind(session_id, turn_no, correlation_id)
audit.record("intent.resolved", resolution)
```

`BoundTurnAuditRecorder` przechowuje tylko techniczny kontekst tury. Dzięki
temu kod emitujący zdarzenie nie powtarza trzech identyfikatorów, a równoległe
tury nie współdzielą mutowalnego kontekstu w recorderze.

### 4.3 Porty sinków

Oba porty mają celowo minimalny kontrakt:

```python
class AppLogSinkPort(Protocol):
    def emit(self, event: AppLogEvent) -> None: ...

class SessionAuditSinkPort(Protocol):
    def emit(self, event: SessionAuditEvent) -> None: ...
```

Port audytu nie ma `flush()`. Batching jest szczegółem adaptera BigQuery i nie
przecieka do orchestratora ani recordera.

## 5. Pełny przepływ tury ADCM

Poniższa kolejność pokazuje, gdzie powstają zdarzenia audytu. Zdarzenia rund
stabilizacji mogą wystąpić wielokrotnie.

```text
HTTP middleware
  -> tworzy correlation_id
  -> http_request (application log)

TurnOrchestrator.run_turn
  -> turn.started
  -> user.message.received
  -> Forge.describe(correlation_id)
  -> intent resolver
  -> intent.resolved
  -> CandidatePolicy.evaluate
       -> candidate.accepted / candidate.rejected
  -> unresolved z IntentResolution
       -> candidate.deferred
  -> DocumentEngine.apply
       -> mutation.applied, ale tylko dla zwróconych MutationEvent
  -> StabilizationEngine.stabilize
       -> stabilization.round.started
       -> forge.analysis.started
       -> Forge.analyze(document, correlation_id=...)
       -> forge.analysis.completed
       -> forge.proposal.received / rule.proposal.generated
       -> ProposalReconciler.reconcile
       -> proposal.decision
       -> DocumentEngine.apply
       -> mutation.applied
       -> stabilization.round.completed
       -> stabilization.completed
  -> external_checks.completed
  -> response.composed
  -> SessionRepository.save
  -> turn.completed
  -> http_response (application log)
```

Jeżeli etap wykonywany wewnątrz głównego bloku `try` rzuci wyjątek,
`TurnOrchestrator` emituje `turn.failed`, zapisuje application log
`turn_failed` i ponownie zgłasza oryginalny wyjątek. Pobranie sesji, wyliczenie
numeru tury, związanie recordera oraz początkowe `turn.started`,
`user.message.received` i application log `turn_started` znajdują się przed
tym blokiem. Ich awaria nie generuje obecnie `turn.failed`. Audyt nie maskuje
oryginalnego błędu biznesowego.

### 5.1 Katalog zdarzeń session audit

| `event_type` | Miejsce emisji | Znaczenie danych |
|---|---|---|
| `turn.started` | `TurnOrchestrator` | rewizja kontraktu na początku tury |
| `user.message.received` | `TurnOrchestrator` | surowa wiadomość po późniejszej redakcji w sinku |
| `intent.resolved` | `TurnOrchestrator` | pełny wynik resolvera: kandydaci, query i nierozstrzygnięte elementy |
| `candidate.accepted` | `TurnOrchestrator` | kandydat, powód decyzji i ID utworzonej komendy |
| `candidate.rejected` | `TurnOrchestrator` | odrzucony kandydat i deterministyczny powód |
| `candidate.deferred` | `TurnOrchestrator` | element `IntentResolution.unresolved` |
| `mutation.applied` | orchestrator lub stabilizer | dokładny `MutationEvent` po realnej mutacji |
| `stabilization.round.started` | `StabilizationEngine` | numer rundy i rewizja wejściowa |
| `forge.analysis.started` | `StabilizationEngine` | runda, rewizja i opcjonalna faza |
| `forge.analysis.completed` | `StabilizationEngine` | compact summary wyniku Forge, kontekst rundy i czas (patrz 5.2) |
| `forge.proposal.received` | `StabilizationEngine` | propozycja pochodząca z Forge |
| `rule.proposal.generated` | `StabilizationEngine` | propozycja pochodząca z reguły ADCM |
| `proposal.decision` | `StabilizationEngine` | decyzja reconciliatora oraz proponowana i obecna wartość/proweniencja |
| `stabilization.round.completed` | `StabilizationEngine` | zmiana rewizji i informacja, czy runda coś zmieniła |
| `stabilization.completed` | `StabilizationEngine` | liczba rund, zbieżność i końcowa rewizja |
| `external_checks.completed` | `TurnOrchestrator` | wynik opcjonalnych kontroli zewnętrznych |
| `response.composed` | `TurnOrchestrator` | odpowiedź przeznaczona dla użytkownika |
| `turn.completed` | `TurnOrchestrator` | końcowy snapshot, statusy, diagnostyka i odpowiedź (patrz 5.2) |
| `turn.failed` | `TurnOrchestrator` | etap, typ błędu, komunikat i aktualna rewizja |

`mutation.applied` nie jest tworzone dla samego zamiaru zmiany. Najpierw
`DocumentEngine` musi zastosować `MutationCommand` i zwrócić domenowy
`MutationEvent`. Audyt serializuje ten fakt, ale go nie tworzy i nie zmienia
`ContractState`.

### 5.2 Session audit jako widok, nie kopia modelu

Session audit nie jest serializacją 1:1 modeli domenowych. Mapowanie
core → session audit view należy do `application/observability/audit_views.py`
i jest zbudowane z czystych funkcji:

```
CORE MODEL                    -> AUDIT VIEW                 -> JSONL / BigQuery
ForgeAnalysis                    forge_analysis_completed_view()
TurnOutcome + StabilizationReport  turn_completed_view()
```

Zasada: dane, które mają własny dedykowany event, nie są powtarzane w evencie
zbiorczym. Dane, które nie zmieniają się między rundami fixed-point, nie są
zapisywane w każdej rundzie.

`forge.analysis.completed` w trybie `normal` zawiera:

| pole | znaczenie |
|---|---|
| `round`, `contract_revision` | kontekst fixed-point |
| `phase` | tylko dla `final_validation` |
| `definition_version` | wersja definicji kontraktu |
| `status` | `valid` / `complete` / `clean` |
| `writable_count` | licznik zamiast `writable[]` — lista jest w praktyce identyczna w każdej rundzie |
| `missing` | lista ścieżek; pełne `MissingRequirement` jest w `turn.completed` |
| `foreign_count`, `proposal_count`, `diagnostic_count` | liczniki |
| `diagnostics` | tylko gdy niepuste |
| `duration_ms` | czas wywołania Forge |

Szczegóły propozycji pozostają w `forge.proposal.received` i
`rule.proposal.generated`, a decyzje w `proposal.decision`. Ścieżkę
`proposal → decision → mutation` odtwarza się po `proposal_id` i `path`.

`turn.completed` pozostaje pełnym snapshotem końcowym (`final_document`,
`forge_status`, `missing`, `diagnostics`, `external_checks`, `response`), ale
`stabilization` jest zredukowane do `{rounds, converged}` — pełna historia
`proposal_decisions[]` jest już w osobnych eventach `proposal.decision`.
`StabilizationReport` w domenie pozostaje bez zmian; redukcja dotyczy wyłącznie
mapowania audytowego.

Tryb `debug` (`ADCM_AUDIT_LEVEL=debug`) przywraca pełny `ForgeAnalysis` i pełne
`MissingRequirement`. Na nagranych sesjach wielorundowych compact audit zmniejsza
JSONL o ok. 31–34% (payload `data` o ok. 47–50%); reszta pliku to envelope
eventu, który jest stały i nie podlega redukcji.

## 6. Elementy dołożone poza `observability`

Ta sekcja jest najważniejsza przy analizie zasięgu zmiany.

### 6.1 `TurnOrchestrator`

Do orchestratora dodano:

- opcjonalne zależności `SessionAuditRecorder` i `AppLogRecorder`,
- techniczny argument `correlation_id` w `run_turn`,
- związanie recordera z `(session_id, turn_no, correlation_id)`,
- emisję zdarzeń na granicach istniejących etapów,
- obsługę terminalnego `turn.failed`,
- pełny snapshot w `turn.completed`.

Orchestrator pozostaje właścicielem kolejności tury, dlatego zna momenty emisji.
Obecnie zna jednak również nazwy zdarzeń i buduje część payloadów audytowych.
To jest główne miejsce wzrostu odpowiedzialności poza modułem
`observability`.

### 6.2 `StabilizationEngine`

Dodano opcjonalny, związany recorder audytu i `correlation_id`. Stabilizer zna
rzeczywiste granice rund, analiz Forge, propozycji, decyzji i mutacji, więc jest
najdokładniejszym miejscem do określenia czasu zdarzenia.

Dodatkowo `_record_proposal_decisions` buduje bogaty payload audytowy z:

- decyzji `ProposalDecision`,
- danych źródłowej `Proposal`,
- aktualnej wartości dokumentu,
- aktualnego `ValueProvenance`.

Jest to uzasadnione diagnostycznie, ale mapowanie obserwowalności zwiększa
rozmiar stabilizera i jest kandydatem do przeniesienia do istniejącego
`SessionAuditRecorder`, jeśli katalog zdarzeń będzie dalej rósł.

### 6.3 `CandidatePolicy`

Przed zmianą `CandidatePolicy.decide()` zwracał wyłącznie listę komend. Taki
wynik zachowywał kandydatów zaakceptowanych, ale bezpowrotnie gubił informację
o odrzuceniach. Audyt wymaga odpowiedzi na pytanie „dlaczego kandydat nie
zmienił kontraktu”, dlatego dodano:

- `CandidateDisposition` — jawny wynik `accepted`, `rejected` lub `deferred`,
- `CandidateDecision` — oryginalny kandydat, disposition, powód i opcjonalne
  ID komendy,
- `CandidatePolicyResult` — równoległe listy komend i decyzji,
- `evaluate()` — pełny wynik polityki,
- pozostawione `decide()` — kompatybilny widok zwracający tylko komendy.

Te klasy nie są modelami logowania. Są typowanym wynikiem deterministycznej
polityki application. Nie znają recordera ani sinka. Audyt jedynie konsumuje
ich wynik. Jest to lepsze niż wstrzyknięcie loggera do `CandidatePolicy`, bo
polityka zachowuje czystość i może być użyta bez obserwowalności.

W bieżącym kodzie `CandidateDisposition.DEFERRED` nie jest zwracane przez
`CandidatePolicy`. Zdarzenia `candidate.deferred` powstają z
`IntentResolution.unresolved`. Wartość enumu jest więc aktualnie nadmiarowa.

### 6.4 `IntentResolution.unresolved`

Do modelu wyniku resolwera dodano `unresolved`, aby zachować nierozstrzygnięte
fragmenty intencji i zapisać je jako `candidate.deferred`. Pole ma obecnie typ
`list[dict[str, Any]]`. Funkcjonalnie spełnia zadanie, ale jest słabiej typowane
niż pozostałe kontrakty Pydantic i stanowi dług architektoniczny.

### 6.5 `ProposalDecision` i `ProposalReconciler`

`ProposalDecision` udostępnia `path`, `action`, `proposal_id` i `reason`.
Reconciler zawsze zwraca decyzje razem z komendami. Stabilizer może dzięki temu
powiązać decyzję z propozycją i aktualnym stanem, nie ingerując w algorytm
wyboru zwycięskiej propozycji.

### 6.6 Port Forge, adapter MCP i serwer Forge

Do `ContractForgePort.analyze` i `describe` dodano keyword-only
`correlation_id`. Adapter MCP przekazuje go w argumentach narzędzia, a Forge
umieszcza w application logach.

Obowiązuje niezmiennik:

```text
analyze(document=X, correlation_id=AAA)
==
analyze(document=X, correlation_id=BBB)
```

Identyfikator nie jest przekazywany do `ContractAnalyzer` ani
`ContractDescriber`. Nie jest wejściem biznesowym i nie może wpływać na
`ForgeAnalysis` ani `ForgeDescription`.

### 6.7 Composition root, konfiguracja i runtime

`adapters/api/app.py` wybiera backend i poziom audytu (`ADCM_AUDIT_LEVEL`) na
podstawie konfiguracji, tworzy sinki, recordery i wstrzykuje je do adaptera Forge
oraz orchestratora. Nieznana wartość `ADCM_AUDIT_LEVEL` zatrzymuje start procesu,
tak samo jak nieznany `ADCM_LOG_BACKEND`. Middleware HTTP
tworzy `correlation_id`, zapisuje request/response i zwraca go w nagłówku
`X-Correlation-ID`.

Pliki zależności, Dockerfile, Compose i README zostały rozszerzone o opcjonalny
klient BigQuery, zmienne środowiskowe oraz katalogi logów. To są zmiany
integracyjne, a nie nowe reguły biznesowe.

## 7. Adapter lokalny JSONL

Backend `local` jest domyślny.

- application log: `logs/app/YYYY-MM-DD.jsonl`,
- session audit: `logs/sessions/<bezpieczny-session-id>.jsonl`.

Każde wywołanie `emit` dopisuje jeden rekord. Zapis w procesie jest chroniony
blokadą. Niebezpieczne znaki w `session_id` nie trafiają do ścieżki pliku;
identyfikator jest kodowany w sposób odporny na kolizje i traversal.

Lokalny audit nie czeka do końca tury. Każde zdarzenie jest od razu dopisywane
do JSONL, więc częściowa historia pozostaje dostępna także przy awarii tury.

## 8. Adapter BigQuery i batching

Application log wykonuje jeden `insert_rows_json` dla jednego zdarzenia.
Session audit działa inaczej:

```text
emit(non-terminal event)
  -> sanitize
  -> dopisz do bufora (session_id, turn_no, correlation_id)
  -> brak wywołania BigQuery

emit(turn.completed | turn.failed)
  -> dopisz event terminalny
  -> atomowo wyjmij bufor tej tury
  -> jedno insert_rows_json ze wszystkimi rekordami
```

Batching należy wyłącznie do `BigQuerySessionAuditSink`. Orchestrator nie zna
pojęcia batcha ani `flush()`.

Blokada chroni mapę buforów, ale wywołanie sieciowe odbywa się poza blokadą.
Przeplatane tury mają osobne klucze i osobne inserty.

Ograniczenia bieżącego MVP:

- bufor jest wyłącznie procesowy,
- twarde zakończenie procesu przed eventem terminalnym traci bufor,
- batch jest usuwany z pamięci przed wywołaniem BigQuery; błąd inserta oznacza
  utratę batcha bez retry,
- trwała kolejka, retry i dead-letter queue nie są zaimplementowane.

Jest to zgodne z bieżącym best-effort, ale nie zapewnia trwałego audytu. Jeżeli
audyt stanie się wymaganiem regulacyjnym, politykę należy zmienić jawnie zamiast
ukrywać retry w orchestratorze.

## 9. Polityka błędów

### 9.1 Awaria application sinka

`AppLogRecorder` przechwytuje wyjątek rzucony przez sink, redaguje jego
komunikat, zapisuje błąd przez standardowy logger i na `stderr`, a następnie
pozwala procesowi biznesowemu działać dalej. Konstrukcja i walidacja
`AppLogEvent` odbywają się przed `try`, dlatego ich wyjątki nie są fail-open.

### 9.2 Awaria session audit sinka

`SessionAuditRecorder` przechwytuje wyjątek sinka i emituje application log:

```json
{
  "event": "session_audit_sink_failed",
  "level": "ERROR",
  "session_id": "aaa",
  "turn_no": 3,
  "correlation_id": "...",
  "data": {
    "failed_event_type": "intent.resolved",
    "failed_event_count": 1
  }
}
```

Dla nieudanego batcha BigQuery `failed_event_count` obejmuje wszystkie rekordy
wyjęte z bufora. Jeżeli zawiedzie także application sink, jego własna polityka
fallback zapisze informację na `stderr`.

Ani błąd sinka audytu, ani późniejszy błąd application sinka nie przerywa tury.
Budowa `SessionAuditEvent` i `_dump()` payloadu odbywają się wcześniej i nie są
objęte tą gwarancją.

## 10. Redakcja danych wrażliwych

Sanitizer działa rekurencyjnie na słownikach, listach, tuple i napisach.
Redaguje między innymi:

- pola z nazwami takimi jak `authorization`, `api_key`, `password`, `secret`,
  `token`, `credentials`, `cookie` i `private_key`,
- warianty wielkości liter i separatorów,
- tokeny `Bearer` i `Basic` w tekście,
- przypisania sekretów, także wieloliniowe.

Sanityzacja jest wykonywana przed trwałym zapisem w adapterach. Fallback
recordera także redaguje komunikat wyjątku.

Należy jednak unikać wkładania nieograniczonego `str(exc)` do payloadu.
Arbitralny tekst wyjątku może zawierać sekret w formacie, którego heurystyka
nie rozpozna. `TurnOrchestrator` zapisuje obecnie `str(exc)` w `turn.failed` i
application log `turn_failed`; bezpieczniejszy kontrakt powinien preferować typ
błędu, etap i ewentualnie ograniczony, jawnie oczyszczony komunikat.

### 10.1 Zakres i klasyfikacja zapisywanych danych

Session audit zapisuje znacznie więcej niż typowa telemetria techniczna:

- surową wiadomość użytkownika,
- pełny wynik rozpoznania intencji,
- kandydatów oraz przyczyny ich przyjęcia lub odrzucenia,
- proponowane i aktualne wartości kontraktu,
- pełny końcowy dokument,
- odpowiedź dla użytkownika i komunikat błędu.

Sanitizer usuwa rozpoznane sekrety, ale nie jest mechanizmem anonimizacji PII
ani klasyfikacji danych. Nie gwarantuje usunięcia nazw osób, adresów, danych
biznesowych ani sekretów zapisanych w nieznanym formacie. W bieżącej
implementacji nie ma również polityki retencji, kontroli dostępu opisanej w
kodzie, limitowania rozmiaru payloadu ani segmentacji danych według
wrażliwości.

Pełny `final_document` oraz rozbudowane wyniki Forge mogą zbliżyć pojedynczy
rekord do limitów BigQuery. Ponieważ wszystkie eventy tury są wysyłane jednym
insertem, zbyt duży rekord terminalny może spowodować odrzucenie i utratę całego
batcha. Przed produkcyjnym użyciem należy ustalić klasyfikację danych, dostęp,
retencję, limity rozmiaru i ewentualne zastąpienie pełnych wartości skrótami
lub referencjami.

## 11. `correlation_id`

Przepływ identyfikatora:

```text
middleware ADCM
  -> application log ADCM
  -> TurnOrchestrator i session audit
  -> ForgeMcpAdapter
  -> argument MCP
  -> application log Forge
```

Służy wyłącznie do łączenia technicznych zapisów z jednego requestu. Nie jest
częścią `ContractState`, mutacji, propozycji ani analizy Forge.

## 12. Audyt overengineeringu

### 12.1 Szukane abstrakcje

W kodzie nie występują:

- `EventBus`,
- `EventDispatcher`,
- `AuditPipeline`,
- `AuditProcessor`,
- `LogFactory`,
- `SinkManager`,
- `TelemetryManager`,
- loggingowe klasy o rolach `Registry`, `Facade`, `Manager`, `Factory`,
  `Dispatcher` lub `Processor`.

Nie ma centralnej szyny zdarzeń, ukrytego dispatchu ani ogólnego frameworka
telemetrii. Zdarzenie powstaje jawnie w miejscu, które zna fakt biznesowy lub
granicę procesu, po czym trafia bezpośrednio do recordera i jednego sinka.

### 12.2 Abstrakcje uzasadnione

| Abstrakcja | Dlaczego istnieje |
|---|---|
| `AppLogRecorder` | buduje typowany event i izoluje biznes od awarii sinka |
| `SessionAuditRecorder` | buduje event audytu oraz eskaluje awarię audytu do application log |
| `BoundTurnAuditRecorder` | przechowuje niezmienny kontekst jednej tury bez globalnego stanu |
| dwa małe sink porty | umożliwiają zamianę local/BigQuery i łatwe testy black-box |
| adaptery local/BigQuery | izolują filesystem i klienta Google od core |
| `CandidatePolicyResult` | zachowuje decyzje odrzucone, których sama lista komend nie potrafi opisać |

### 12.3 Sygnały zbędnej lub przejściowej abstrakcji

1. `BoundTurnAuditRecorder.__getattr__` i `_EVENT_NAMES` tworzą dynamiczne
   metody zdarzeń. Produkcyjne wywołania korzystają z `record(event_type, data)`,
   więc warstwa dynamiczna jest nieużywana, osłabia autocomplete i może ukryć
   literówki.
2. Alias `BoundTurnAuditBuffer = BoundTurnAuditRecorder` jest nieużywaną
   pozostałością po pierwszej nazwie. Recorder nie jest buforem; bufor posiada
   adapter BigQuery.
3. `CandidateDisposition.DEFERRED` nie jest produkowane przez politykę.
4. Równoległe `emit()` i `record()` w bound recorderze wykonują to samo. Jeden
   stabilny publiczny czasownik wystarczyłby.
5. `CandidatePolicy.decide()` i `evaluate()` to celowa kompatybilność, lecz po
   migracji wszystkich klientów warto ocenić, czy widok command-only jest
   nadal potrzebny.

Są to małe sygnały długu, a nie rozbudowana nadarchitektura. Ich usunięcie nie
wymaga wprowadzenia nowej warstwy.

## 13. Zgodność z `architecture-guardials.md`

Ocena dotyczy bieżącego wdrożenia, a nie wyłącznie zamierzonego projektu.

| Zasada | Ocena | Uzasadnienie |
|---|---|---|
| §3 Warstwy | częściowo zgodne | infrastruktura jest w adapterach, a modele logów są poza domeną; jednak porty importują modele z application, podczas gdy recordery application importują porty, tworząc dwukierunkową zależność pakietów i naruszając deklarowany kierunek `APPLICATION -> PORTS` |
| §4 Niezależne serwisy | zgodne | ADCM i Forge nie importują się bezpośrednio; każdy ma własne modele i adaptery |
| §5 Publiczny kontrakt | zgodne | eventy i wyniki polityki są modelami Pydantic, sinki mają jawne porty |
| §6 Jeden właściciel | częściowo zgodne | recorder jest właścicielem koperty, emisji i reakcji na błąd sinka, lecz nazwy eventów i schematy payloadów należą faktycznie do orchestratora, stabilizera i recordera; `DocumentEngine` pozostaje wyłącznym właścicielem mutacji, a Forge interpretacji |
| §11 Pydantic między black boxami | częściowo zgodne | główne modele są typowane; `event_type` jest dowolnym `str`, `data` jest elastyczne, a `IntentResolution.unresolved` to `list[dict[str, Any]]` |
| §12 Rozszerzenie bez przebudowy | częściowo zgodne | moduł dodano osobno, ale integracja dotknęła wielu istniejących elementów przepływu |
| §13 Integracje fail-open | zgodne dla awarii sinków | wyjątki adapterów obu strumieni nie zatrzymują biznesu; walidacja koperty i serializacja payloadu pozostają poza ochronnym `try` |
| §14 Cienki orchestrator | ryzyko | orchestrator nadal deleguje biznes, lecz urósł o nazwy eventów i budowę dużych payloadów audytu |
| §15 Bez abstrakcji bez potrzeby | zgodne z drobnym długiem | brak busów, pipeline’ów i managerów; dynamiczny `__getattr__` oraz alias bufora są zbędne |
| §16 Minimalny wpływ zmiany | częściowo zgodne | wymagane punkty emisji dały szeroki blast radius; przyszłe eventy nie powinny dalej rozbudowywać core |
| §17 Rozszerzenie przed modyfikacją | zasadniczo zgodne | nowe recordery, porty i adaptery są osobnymi blokami; część mapowania pozostała w istniejących modułach |
| §18 Testowanie black box | częściowo zgodne | są testy recorderów, sinków, kolejności tury i korelacji; `test_turn_audit.py` używa `FakeForge`, a test adaptera izoluje adapter, więc brak pełnego `HTTP ADCM -> MCP transport -> Forge` |
| §19 Test architektury | zgodne w obecnym zakresie | test blokuje BigQuery i import Forge w `domain`, `application` i `ports`, a filesystem tylko w `domain` i `application`; nie wykrywa kierunku `ports -> application` ani rosnącego orchestratora |
| §24 Modularność | częściowo zgodne | adaptery i recordery można podmieniać; dodanie nowego typu eventu wymaga dziś zmian w emitującym module application |
| §25 Black box dla LLM | częściowo zgodne | modele kopert są jawne, ale kontrakty nazw i payloadów audytu są rozproszone między recorderem, orchestratorem i stabilizerem; zrozumienie modułu wymaga poznania więcej niż jego bezpośredniego kontraktu |
| §26 Niezmienniki | częściowo zgodne | zachowane są m.in. niezależność usług, brak ścieżek konkretnego kontraktu w ADCM i zakaz mutacji przez LLM; odstępstwa dotyczą kierunku warstw, jednego właściciela schematu audytu, cienkiego orchestratora i małego blast radius |

### 13.1 Najważniejsze ryzyka

1. Surowe stringi `event_type` są podatne na literówki i rozjazd schematów.
2. Mapowanie eventów w `TurnOrchestrator` i `StabilizationEngine` zwiększa ich
   rozmiar oraz blast radius kolejnych zmian telemetryki.
3. Porty zależą od modeli w `application/observability`, a recordery application
   zależą od portów. Nie powoduje to bezpośredniego runtime import cycle między
   tymi konkretnymi modułami, lecz tworzy dwukierunkową zależność pakietów
   warstw i narusza deklarowany kierunek `APPLICATION -> PORTS`.
4. BigQuery audit usuwa batch przed insertem i nie wykonuje retry.
5. Surowy `str(exc)` może ujawnić dane, których sanitizer heurystyczny nie zna.
6. `turn.completed` powstaje po udanym `sessions.save()`. Zgodnie z fail-open
   zapis stanu może więc być poprawny mimo braku terminalnego audytu.
7. Wygenerowane `repository-map.md` i `repository-inventory.json` nie zawierają
   jeszcze nowych plików obserwowalności i powinny zostać odświeżone przez
   właściwy generator dokumentacji repozytorium.
8. Audyt przechowuje surowe dane użytkownika i pełny dokument bez zdefiniowanej
   retencji, klasyfikacji PII oraz limitu rozmiaru.

### 13.2 Gdzie dokładnie nie są spełnione trzy wskazane guardrails

#### Cienki orchestrator

Problem występuje przede wszystkim w
`src/adcm/application/turn_orchestrator.py`, w `TurnOrchestrator.run_turn()`.
Orchestrator powinien ustalać kolejność use case, ale obecnie dodatkowo zna
kontrakt obserwowalności:

- wiąże techniczny recorder z turą,
- zawiera surowe nazwy `intent.resolved`, `candidate.*`,
  `external_checks.completed`, `response.composed`, `turn.completed` i
  `turn.failed`,
- serializuje `CandidateDecision` i dopisuje `reason` oraz `command_id`,
- mapuje `IntentResolution.unresolved` na `candidate.deferred`,
- serializuje każdy `MutationEvent`,
- buduje duży payload `turn.completed` z dokumentem, statusem Forge,
  brakującymi polami, diagnostyką, kontrolami zewnętrznymi, stabilizacją i
  odpowiedzią,
- buduje payload błędu oraz osobny application log,
- utrzymuje techniczne helpery `_audit()` i `_app_info()`.

Podobny problem, chociaż poza samym orchestratorem, występuje w
`src/adcm/application/stabilization_engine.py`. `StabilizationEngine` zna nazwy
wszystkich eventów rundy i Forge. Metody `_record_mutations()` oraz szczególnie
`_record_proposal_decisions()` są kodem mapowania audytu. Ta druga łączy
`ProposalDecision`, `Proposal`, aktualną wartość dokumentu i proweniencję tylko
po to, aby zbudować payload telemetryczny.

Samo wskazanie momentu zdarzenia przez orchestrator lub stabilizer jest
poprawne. Niespełniona część guardrail polega na tym, że moduły te znają także
nazwę eventu, dokładny kształt jego danych i sposób serializacji.

#### Jeden właściciel schematów audytu

`SessionAuditRecorder` jest właścicielem utworzenia koperty
`SessionAuditEvent`, wywołania sinka i obsługi jego błędu. Nie jest jednak
pełnym właścicielem kontraktu audytu:

| Część kontraktu | Faktyczny właściciel w bieżącym kodzie |
|---|---|
| koperta, identyfikatory i timestamp | `SessionAuditRecorder` |
| lista nazw eventów | surowe stringi w `TurnOrchestrator` i `StabilizationEngine` oraz osobna `_EVENT_NAMES` w recorderze |
| payload decyzji kandydatów | `TurnOrchestrator` |
| payload końca i błędu tury | `TurnOrchestrator` |
| payload analizy Forge i rund | `StabilizationEngine` |
| payload decyzji propozycji | `StabilizationEngine._record_proposal_decisions()` |
| serializacja wartości Pydantic | częściowo wywołujący moduł, częściowo `_dump()` w recorderze |

Skutkiem są co najmniej trzy źródła prawdy. `_EVENT_NAMES` wygląda jak katalog
eventów, ale produkcyjny kod go nie używa i przekazuje bezpośrednio dowolny
`str`. Zmiana schematu eventu wymaga więc odnalezienia jego call sites zamiast
zmiany w jednym module odpowiedzialnym za observability.

#### Minimalny blast radius

Pierwsze wdrożenie musiało dotknąć miejsc, które znają rzeczywisty czas
zdarzenia. Zasięg wykroczył jednak poza prostą integrację recordera:

- `TurnOrchestrator` otrzymał logikę mapowania wielu eventów,
- `StabilizationEngine` otrzymał `correlation_id`, recorder i trzy helpery
  audytowe,
- `CandidatePolicy` otrzymał nowy pełny typ wyniku,
- `ProposalReconciler` zaczął zachowywać dodatkowe decyzje przegrywających
  propozycji,
- `IntentResolution` otrzymał `unresolved`,
- port Forge, adapter MCP i serwer Forge otrzymały `correlation_id`,
- composition root, konfiguracja, zależności i runtime zostały rozszerzone o
  wybór sinków.

Część tych zmian jest uzasadniona: decyzje kandydatów i propozycji muszą zostać
zachowane, a korelacja musi przejść przez granicę usługi. Problem ujawnia się
przy kolejnych zmianach: dodanie lub zmiana eventu wymaga obecnie edycji
orchestratora albo stabilizera, recordera/testów, a czasem także modelu wyniku.

Docelowe kryterium jest prostsze: nowy event może wymagać jednej jawnej linii w
module, który zna moment zdarzenia, ale nazwa, payload, serializacja, redakcja i
polityka błędów powinny zmieniać się wyłącznie w observability. Porty, adaptery,
composition root i domena nie powinny zmieniać się przy dodawaniu typu eventu.

## 14. Rekomendowane uproszczenia

Poniższy plan nie został jeszcze wykonany w kodzie. Kolejność minimalizuje
ryzyko zmiany zachowania biznesowego.

### Etap 0 — testy charakteryzujące stan bieżący

Przed refaktoryzacją należy utrwalić:

- kolejność i liczbę eventów dla tury udanej oraz nieudanej,
- pełne payloady decyzji kandydata, propozycji, mutacji i `turn.completed`,
- batching BigQuery po evencie terminalnym,
- fail-open awarii sinka,
- identyczny wynik Forge dla różnych `correlation_id`.

Test architektury powinien dodatkowo wskazywać surowe nazwy eventów poza
observability. Po zakończeniu migracji ich wystąpienie w orchestratorze lub
stabilizerze ma powodować błąd testu.

### Etap 1 — usunięcie martwego API bez zmiany zachowania

W `application/observability/session_audit_recorder.py`:

1. Usunąć `BoundTurnAuditRecorder.__getattr__`.
2. Usunąć cały słownik `_EVENT_NAMES`.
3. Usunąć alias `BoundTurnAuditBuffer`.
4. Pozostawić jeden publiczny czasownik. Bieżące call sites używają
   `record()`, dlatego należy pozostawić `record()` i usunąć publiczne
   `emit()` z bound recordera. Wspólną implementację można zachować jako
   prywatną metodę.

W `application/candidate_policy.py` usunąć
`CandidateDisposition.DEFERRED`. `CandidatePolicy.evaluate()` produkuje tylko
`ACCEPTED` albo `REJECTED`; defer pochodzi z `IntentResolution.unresolved`, a
nie z polityki kandydatów.

Repozytoryjne wyszukiwanie potwierdza, że dynamiczne metody, alias i
`CandidateDisposition.DEFERRED` nie mają call sites. Przed usunięciem należy
jeszcze potwierdzić, że nie są publicznym API używanym przez zewnętrzny pakiet.

Kryterium zakończenia: identyczne eventy i wyniki biznesowe, brak wymienionych
symboli w kodzie oraz przejście testów ADCM.

### Etap 2 — jedno źródło nazw i schematów eventów

W observability należy wprowadzić statyczny, jawny kontrakt bez dynamicznego
dispatchu:

1. Dodać `SessionAuditEventType(StrEnum)` jako jedyne źródło nazw eventów.
   `SessionAuditEvent.event_type` powinien używać tego typu zamiast dowolnego
   `str`.
2. Dodać jawne metody semantyczne do `BoundTurnAuditRecorder`, np.
   `intent_resolved(resolution)`, `candidate_decision(decision)`,
   `mutation_applied(event)`, `proposal_decision(...)`,
   `turn_completed(outcome, revision)` i `turn_failed(...)`.
3. Metody recordera mają wybierać `event_type` i budować payload. Call site ma
   jedynie wskazać moment i przekazać typowane dane.
4. Dla prostych eventów wystarczą typowane sygnatury metod. Nie należy tworzyć
   osobnego modelu Pydantic dla każdego jedno- lub dwupolowego payloadu.
   Dedykowany model ma sens tylko dla złożonych kontraktów, np.
   `ProposalDecisionAuditData`, `TurnCompletedAuditData` i
   `TurnFailedAuditData`.
5. `IntentResolution.unresolved` zastąpić małym typowanym modelem, np.
   `UnresolvedIntent`, ponieważ jest rzeczywistym wynikiem resolwera, a nie
   modelem logowania.

Nie należy zastępować `_EVENT_NAMES` nowym registry, dispatcherem ani mapą
callbacków. Jawne metody mają być zwykłym, statycznie sprawdzalnym API.

### Etap 3 — odchudzenie orchestratora i stabilizera

W `TurnOrchestrator`:

- zastąpić ręczne `model_dump()`, `payload.update()` i surowe event strings
  wywołaniami semantycznymi recordera,
- przenieść budowę `turn.completed` i `turn.failed` do recordera,
- po migracji usunąć `_audit()`; pozostawić techniczne application logi tylko
  tam, gdzie wyznaczają granice use case,
- nie przenosić kolejności tury, wywołań Forge, resolvera, `DocumentEngine`,
  stabilizacji ani zapisu sesji do observability.

W `StabilizationEngine`:

- zastąpić surowe nazwy eventów metodami recordera,
- przenieść serializację analiz, rund i mutacji do recordera,
- przenieść mapowanie z `_record_proposal_decisions()` do semantycznej metody
  recordera, która przyjmuje `ContractState`, `Proposal` i
  `ProposalDecision`,
- usunąć `_record()`, `_record_mutations()` i
  `_record_proposal_decisions()` po migracji call sites,
- pozostawić w stabilizerze algorytm rund, analizę Forge, reconciliację i
  zastosowanie komend.

Po tym etapie orchestrator i stabilizer nadal wskazują, kiedy fakt wystąpił,
ale nie wiedzą, jak wygląda rekord audytowy.

### Etap 4 — naprawa kierunku zależności warstw

Obecnie porty sinków importują modele z `application/observability`, a
recordery application importują porty. Należy przenieść wyłącznie neutralne
koperty `AppLogEvent` i `SessionAuditEvent` do niezależnego, liściowego pakietu
kontraktów observability, który:

- nie importuje `domain`, `application`, `ports` ani `adapters`,
- może być importowany przez porty, recordery i adaptery,
- nie zawiera recorderów, sinków ani reguł biznesowych,
- jest objęty testem dozwolonego kierunku zależności.

Alternatywą jest umieszczenie kopert bezpośrednio przy portach. Preferowany jest
neutralny pakiet, ponieważ zachowuje ustaloną granicę „modele telemetryki poza
domeną” i nie miesza koperty danych z capability portem. Sama zmiana ścieżki
katalogu bez testu architektury nie rozwiązuje problemu.

Forge musi otrzymać analogiczną zmianę we własnym kodzie, bez współdzielonego
pakietu i bez importu z ADCM.

### Etap 5 — ograniczenie przyszłego blast radius

Po refaktoryzacji należy egzekwować następujący kontrakt:

- nowy event zmienia moduł observability, jedno miejsce emisji i testy,
- zmiana payloadu nie zmienia orchestratora ani stabilizera,
- adaptery local i BigQuery przyjmują tę samą stabilną kopertę i nie znają
  typów konkretnych eventów poza terminalnym warunkiem batchingu,
- dodanie eventu nie zmienia domeny, portów, composition root ani konfiguracji,
- event domenowy `MutationEvent` pozostaje źródłem `mutation.applied`.

Test architektury powinien blokować:

- surowe nazwy session-audit eventów poza observability,
- import `application.observability` z `ports`,
- import adapterów z domeny, application i portów,
- ponowne pojawienie się `__getattr__`, `_EVENT_NAMES` oraz aliasów
  kompatybilności bez udokumentowanego konsumenta.

### Etap 6 — osobne usprawnienia niezwiązane z odchudzaniem

Po powyższym refaktorze, w osobnych zmianach:

1. Zastąpić nieograniczony `str(exc)` bezpiecznym, ograniczonym kontraktem
   błędu.
2. Dodać test rzeczywistego połączenia ADCM -> MCP -> Forge, który sprawdzi
   propagację `correlation_id` po przewodzie oraz identyczność wyniku.
3. Ustalić klasyfikację danych, retencję i limity rozmiaru audytu.
4. Jeżeli wymagana będzie trwałość audytu, zaprojektować jawne retry lub trwałą
   kolejkę w adapterze. Nie dodawać tej odpowiedzialności do orchestratora.

### Zakres, którego plan nie zmienia

Plan zachowuje:

- `CandidateDecision` i `CandidatePolicyResult`, ponieważ reprezentują
  rzeczywisty wynik polityki, a nie abstrakcję logowania,
- `BoundTurnAuditRecorder`, ponieważ bezpiecznie wiąże niezmienny kontekst
  jednej tury,
- rozdział application log i session audit,
- batching BigQuery wewnątrz adaptera,
- niezależne implementacje observability w ADCM i Forge,
- techniczny charakter `correlation_id`.

Nie należy rozwiązywać tych punktów przez dodanie `EventBus`,
`EventDispatcher`, `AuditPipeline`, `AuditProcessor`, `LogFactory`,
`SinkManager` ani `TelemetryManager`. Obecne bezpośrednie połączenie
`emitujący moduł -> recorder -> port -> adapter` jest wystarczające.

## 15. Zasady dla kolejnych zmian

Przy dodawaniu eventu:

1. Ustal, kto jako pierwszy zna prawdziwy fakt lub zakończenie etapu.
2. Emituj zdarzenie w tym miejscu, ale mapowanie formatu utrzymuj w
   observability, jeżeli jest większe niż prosty `model_dump`.
3. Nie emituj `mutation.applied` przed uzyskaniem `MutationEvent` z
   `DocumentEngine`.
4. Nie przekazuj recordera do domeny i nie pozwalaj adapterowi mutować stanu.
5. Nie dodawaj `flush()` do orchestratora; batching pozostaje w adapterze.
6. Zachowaj `correlation_id` jako metadata techniczne.
7. Przetestuj ścieżkę sukcesu, błędu biznesowego i awarii sinka.
8. Sprawdź redakcję nowych pól zawierających dane użytkownika.
9. Jeżeli pojedynczy event wymaga zmian w wielu modułach biznesowych, zatrzymaj
   pracę i najpierw zmniejsz blast radius.

## 16. Testy będące specyfikacją zachowania

Najważniejsze testy ADCM:

- `tests/test_observability.py` — JSONL, redakcja, batching, izolacja i
  współbieżność buforów, błędy BigQuery i fallback,
- `tests/test_turn_audit.py` — kolejność zdarzeń tury, pełne payloady,
  propagacja korelacji oraz fail-open audytu,
- `tests/test_forge_mcp_adapter.py` — argument korelacji i mapowanie odpowiedzi
  MCP,
- `tests/test_document_engine.py` — związek realnej mutacji z
  `MutationEvent`,
- `tests/test_logging_architecture.py` — zakaz zależności infrastrukturalnych
  w core.

Najważniejsze testy Forge sprawdzają modele application log, sinki,
sanityzację i invariant, że `correlation_id` nie zmienia wyniku analizy.

## 17. Szybka diagnostyka

Gdy brakuje zdarzeń sesji:

1. Znajdź `correlation_id` w odpowiedzi HTTP.
2. Sprawdź application log ADCM pod kątem `session_audit_sink_failed`.
3. Dla backendu local sprawdź plik konkretnej sesji.
4. Dla BigQuery sprawdź, czy powstał `turn.completed` albo `turn.failed`;
   wcześniej adapter nie wykonuje inserta.
5. Użyj tego samego `correlation_id`, aby znaleźć `forge_call_*` w ADCM i
   `contract_analyze_*` lub `contract_describe_*` w Forge.
6. Jeżeli stan sesji został zapisany, ale brakuje `turn.completed`, pamiętaj o
   świadomej polityce fail-open i braku retry w adapterze BigQuery.

Dokument skrócony z konfiguracją i schematami tabel znajduje się w
`docs/logging-architecture.md`. Ten przewodnik jest źródłem szczegółów
implementacyjnych i oceny architektury.
