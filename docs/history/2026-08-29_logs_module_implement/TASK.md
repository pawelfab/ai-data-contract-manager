# ADCM / Contract Forge — implementacja modułu logowania

## 1. Cel zadania

Dodaj do istniejącego monorepo moduł logowania zgodny z obecną architekturą ports/adapters i zasadą black box.

System składa się obecnie z niezależnych serwisów:

```text
/
├── docs/
├── ai-data-contract-manager/
└── mcp-servers/
    └── mcp-contract-forge/
```

Każdy serwis:

* jest osobnym procesem,
* ma własny `pyproject.toml`,
* ma własny `.venv`,
* ma własne dependencies,
* może być uruchamiany w osobnym kontenerze Docker,
* NIE importuje kodu Python z drugiego serwisu.

Nie twórz wspólnego pakietu Python dla logowania pomiędzy ADCM i Forge.

---

# 2. Najważniejsze granice architektury

Obowiązują istniejące zasady:

```text
ADCM
- właściciel rozmowy,
- właściciel sesji,
- właściciel ContractState,
- właściciel historii,
- właściciel mutacji,
- właściciel provenance,
- właściciel stabilizacji,
- właściciel audit trail sesji.

Contract Forge
- bezstanowy,
- nie zna rozmowy,
- nie zna session history,
- analizuje wyłącznie przekazany dokument,
- nie mutuje dokumentu.
```

Logowanie NIE może zmieniać tych granic.

W szczególności:

* logowanie nie może zawierać logiki biznesowej;
* logging adapter nie może zmieniać `ContractState`;
* domena nie może znać BigQuery, plików ani bibliotek Google;
* orchestrator nie może wykonywać bezpośrednio `open()`, `insert_rows_json()` itp.;
* awaria logowania sesji nie może uszkodzić stanu kontraktu;
* brak BigQuery nie może uniemożliwiać lokalnego uruchomienia aplikacji.

---

# 3. Dwa niezależne rodzaje logowania

System potrzebuje dwóch różnych strumieni.

## 3.1 Application Logging

Służy do diagnostyki technicznej serwisu.

Przykłady:

```text
service_started
service_stopped
configuration_loaded
forge_call_started
forge_call_completed
forge_call_failed
llm_call_started
llm_call_completed
unexpected_exception
http_request
http_response
```

Application log NIE jest historią biznesową sesji.

Powinien zawierać m.in.:

```text
timestamp
level
service
environment
component
event
message
correlation_id
session_id opcjonalnie
turn_no opcjonalnie
duration_ms opcjonalnie
structured_data
```

---

## 3.2 Session Audit Logging

Dotyczy tylko ADCM.

Jest to odtwarzalny zapis przebiegu rozmowy i decyzji systemu.

Musi pozwalać później odpowiedzieć:

```text
Co napisał użytkownik?
Co zrozumiał LLM?
Jakie MutationCandidate wygenerował?
Które candidate zostały przyjęte?
Które zostały odrzucone?
Co faktycznie zmieniło ContractState?
Co zaproponowały ux_rules?
Co zaproponował Forge?
Dlaczego proposal został zastosowany lub odrzucony?
Ile było rund fixed-point?
Jak wyglądał finalny dokument?
Jaką odpowiedź dostał użytkownik?
```

Session Audit jest szczególnie potrzebny do debugowania `IntentResolver`.

---

# 4. Porty

W ADCM utwórz dwa niezależne porty.

Przykładowa lokalizacja:

```text
ai-data-contract-manager/src/adcm/ports/
    app_log_sink.py
    session_audit_sink.py
```

## AppLogSinkPort

Przykładowy kontrakt:

```python
class AppLogSinkPort(Protocol):
    def emit(self, event: AppLogEvent) -> None:
        ...
```

## SessionAuditSinkPort

```python
class SessionAuditSinkPort(Protocol):
    def emit(self, event: SessionAuditEvent) -> None:
        ...
```

Dopuszczalne jest `async`, jeśli lepiej odpowiada istniejącej aplikacji.

Nie mieszaj obu portów w jeden `LoggerPort`.

Application logs i session audit mają różne znaczenie, lifecycle i strukturę.

---

# 5. Modele Pydantic

Modele danych powinny być zdefiniowane jako Pydantic `BaseModel`.

Przykładowa lokalizacja:

```text
adcm/domain/logging/
    app_log.py
    session_audit.py
```

## AppLogEvent

Minimalnie:

```python
class AppLogEvent(BaseModel):
    event_id: UUID
    timestamp: datetime

    level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]

    service: str
    environment: str

    component: str
    event: str
    message: str | None = None

    correlation_id: str | None = None
    session_id: str | None = None
    turn_no: int | None = None

    duration_ms: float | None = None

    data: dict[str, Any] = {}
```

Timestamp przechowuj w UTC.

---

## SessionAuditEvent

Minimalnie:

```python
class SessionAuditEvent(BaseModel):
    event_id: UUID
    timestamp: datetime

    session_id: str
    turn_no: int

    event_type: str

    correlation_id: str | None = None

    data: dict[str, Any]
```

Nie próbuj od razu tworzyć osobnej klasy Pydantic dla każdego możliwego audit event.

Najpierw stabilny envelope:

```text
SessionAuditEvent
    event_type
    data
```

Typowane modele konkretnych payloadów można dodawać później.

---

# 6. Event types sesji

W pierwszej implementacji obsłuż co najmniej:

```text
turn.started
user.message.received

intent.resolved

candidate.accepted
candidate.rejected
candidate.deferred

mutation.applied

forge.analysis.started
forge.analysis.completed

rule.proposal.generated
forge.proposal.received
proposal.decision

stabilization.round.started
stabilization.round.completed
stabilization.completed

external_checks.completed

response.composed
turn.completed

turn.failed
```

Najważniejszy obecnie event:

```text
intent.resolved
```

Powinien zapisywać SUROWY strukturalny wynik `IntentResolver`.

Np.:

```json
{
  "event_type": "intent.resolved",
  "data": {
    "candidates": [
      {
        "path": "/source/systemZrodlowy",
        "value": "sap",
        "confidence": 0.93
      }
    ],
    "unresolved": []
  }
}
```

Dzięki temu można zobaczyć błąd LLM jeszcze przed `CandidatePolicy` i `DocumentEngine`.

---

# 7. MutationEvent

Istniejący `MutationEvent` pozostaje modelem domenowym historii zmian kontraktu.

NIE zastępuj go `SessionAuditEvent`.

Relacja powinna wyglądać:

```text
DocumentEngine
      │
      ▼
MutationEvent
      │
      ├── zapis do historii SessionState
      │
      └── SessionAuditSinkPort
              event_type=mutation.applied
```

Czyli:

```text
MutationEvent
= fakt domenowy

SessionAuditEvent
= zapis tego faktu do systemu obserwowalności
```

Nie mieszaj tych pojęć.

---

# 8. Adapter lokalny

Dla lokalnego uruchomienia zapisuj logi do:

```text
logs/
```

Każdy serwis ma własny folder `logs`.

## ADCM

```text
ai-data-contract-manager/logs/
    app/
    sessions/
```

Application logs:

```text
logs/app/2026-08-29.jsonl
```

Session audit:

```text
logs/sessions/<session_id>.jsonl
```

Np.:

```text
logs/sessions/aaa.jsonl
```

Każda linia = jeden JSON.

Użyj JSONL, nie pojedynczego dużego JSON-a.

Powody:

* append jest prosty;
* crash procesu nie niszczy całego logu;
* łatwo grepować;
* łatwo później załadować do BigQuery;
* łatwo analizować przez LLM.

Nie używaj zwykłego tekstowego formattera dla session audit.

---

# 9. Contract Forge

Forge NIE posiada SessionAuditSinkPort.

Forge posiada tylko application logging.

Przykładowo:

```text
mcp-contract-forge/
    logs/
        app/
            2026-08-29.jsonl
```

Forge może logować:

```text
service_started
contract_definition_loaded
contract_analyze_started
contract_analyze_completed
contract_describe_started
contract_describe_completed
definition_load_failed
unexpected_exception
```

Nie zapisuj w Forge historii sesji ADCM.

Forge nie zna `turn_no` jako pojęcia biznesowego.

Może jedynie propagować `correlation_id`, jeżeli ADCM go przekaże.

---

# 10. Correlation ID

Każda tura ADCM powinna dostać unikalny:

```text
correlation_id
```

Np. UUID.

Ten sam correlation ID powinien być używany dla:

```text
ADCM application logs
Session Audit
ADCM -> Forge request
Forge application log
Forge -> ADCM response
```

Dzięki temu później można prześledzić:

```text
user request
→ ADCM
→ Forge
→ ADCM
→ response
```

przez wiele procesów.

Nie używaj `session_id` jako correlation ID.

Jedna sesja ma wiele tur.

---

# 11. Adapter BigQuery

Dla środowiska GCP dodaj osobne adaptery implementujące TE SAME porty.

Przykładowa struktura:

```text
adcm/adapters/logging/
    local_app_log_sink.py
    local_session_audit_sink.py

    bigquery_app_log_sink.py
    bigquery_session_audit_sink.py
```

Nie umieszczaj importów Google Cloud w `domain`, `application` ani `ports`.

Dependency:

```text
google-cloud-bigquery
```

powinna należeć wyłącznie do ADCM.

Forge, jeśli dostanie własny BigQuery logging adapter, ma mieć własną zależność w swoim `pyproject.toml`.

Nie współdziel pakietu między serwisami.

---

# 12. Tabele BigQuery

Na MVP załóż dwie logiczne tabele:

```text
app_logs
session_audit
```

## app_logs

Przykładowe kolumny:

```text
event_id STRING
timestamp TIMESTAMP
level STRING

service STRING
environment STRING
component STRING

event STRING
message STRING

correlation_id STRING
session_id STRING
turn_no INTEGER

duration_ms FLOAT

data JSON
```

## session_audit

```text
event_id STRING
timestamp TIMESTAMP

session_id STRING
turn_no INTEGER
correlation_id STRING

event_type STRING

data JSON
```

Nie normalizuj obecnie każdego event type do osobnej tabeli.

Najpierw zachowaj elastyczność.

---

# 13. Konfiguracja adaptera

Wybór adaptera ma być konfiguracyjny.

Np.:

```text
ADCM_LOG_BACKEND=local
```

lub:

```text
ADCM_LOG_BACKEND=bigquery
```

Dodatkowo:

```text
ADCM_LOG_DIR=logs

ADCM_BQ_PROJECT=...
ADCM_BQ_DATASET=...
ADCM_BQ_APP_LOG_TABLE=app_logs
ADCM_BQ_SESSION_AUDIT_TABLE=session_audit
```

Forge analogicznie:

```text
FORGE_LOG_BACKEND=local
```

Nie wykrywaj środowiska przez przypadkowe heurystyki typu:

```python
if os.getenv("GOOGLE_CLOUD_PROJECT"):
```

Backend ma być wybrany jawnie.

---

# 14. Composition root

Adapter wybieraj wyłącznie w composition root / bootstrap aplikacji.

Np.:

```text
app.py / main.py
       │
       ▼
configuration
       │
       ├── local
       │      ↓
       │ LocalSessionAuditSink
       │
       └── bigquery
              ↓
         BigQuerySessionAuditSink
```

`TurnOrchestrator` otrzymuje port przez dependency injection.

Nie może sam sprawdzać:

```python
if environment == "gcp":
```

---

# 15. Logging nie może blokować działania biznesowego

Dla zwykłych logów:

```text
logging failure
≠
business transaction failure
```

Jeżeli np. BigQuery chwilowo nie odpowiada:

```text
ContractState NIE może zostać cofnięty.
Tura NIE może zostać uznana za nieudaną tylko z tego powodu.
```

Adapter powinien obsłużyć błąd i przynajmniej użyć standardowego `logging`/stderr jako fallback techniczny.

Nie implementuj teraz skomplikowanego:

```text
Kafka
Pub/Sub
retry queue
dead letter queue
background worker
```

To jest poza zakresem MVP.

---

# 16. Nie loguj sekretów

Dodaj centralną funkcję sanitizacji danych.

Nigdy nie zapisuj:

```text
API keys
Authorization headers
credentials
passwords
service-account JSON
cookies
access tokens
```

Nie polegaj wyłącznie na tym, że wywołujący pamięta o sanitizacji.

Adapter/logging service powinien mieć ostatnią warstwę ochronną.

Przykładowe nazwy kluczy do redakcji:

```text
authorization
api_key
apikey
password
secret
token
access_token
refresh_token
credentials
```

Wartość zastępuj:

```text
***REDACTED***
```

---

# 17. Nie loguj bez potrzeby pełnych payloadów Forge do application logs

Application logs powinny być zwarte.

Np.:

```json
{
  "event": "forge_call_completed",
  "duration_ms": 31,
  "missing_count": 3,
  "diagnostics_count": 0,
  "proposal_count": 4
}
```

Natomiast Session Audit może zapisywać bardziej szczegółowy przebieg potrzebny do rekonstrukcji tury.

Nie duplikuj całego dokumentu kontraktu przy każdym małym event.

---

# 18. Snapshot tury

Na końcu każdej tury dodaj event:

```text
turn.completed
```

który może zawierać:

```text
final_document
forge_status
missing
diagnostics
external_checks_status
stabilization_rounds
converged
response
```

Dzięki temu do analizy typowej tury nie trzeba zawsze rekonstruować całej historii eventów.

Historia mutacji nadal pozostaje eventowa.

---

# 19. Integracja z TurnOrchestrator

Nie umieszczaj dziesiątek:

```python
logger.emit(...)
```

bezpośrednio w każdej metodzie orchestratora.

Preferuj mały application service / facade:

```text
SessionAuditRecorder
```

np.:

```python
audit.turn_started(...)
audit.intent_resolved(...)
audit.mutation_applied(...)
audit.proposal_decision(...)
audit.turn_completed(...)
```

Recorder tworzy `SessionAuditEvent` i wysyła go do portu.

Orchestrator zna semantyczne operacje auditowe, ale nie zna:

```text
JSONL
BigQuery
filesystem
Google SDK
```

---

# 20. Integracja z IntentResolver

Obecnie jest to szczególnie ważne.

Po wywołaniu:

```text
IntentResolverPort.resolve(...)
```

zapisz dokładny structured output resolvera PRZED:

```text
CandidatePolicy
ProposalReconciler
DocumentEngine
```

Potrzebujemy rozróżnić:

```text
LLM źle zinterpretował usera
```

od:

```text
CandidatePolicy źle odrzucił wartość
```

od:

```text
DocumentEngine źle zastosował mutation
```

Nie naprawiaj przy okazji samego `IntentResolver`.

To osobne zadanie.

---

# 21. Testy

Dodaj unit testy portów/adapterów.

Minimum:

### Local application logging

```text
emit event
→ tworzy plik
→ zapisuje jedną poprawną linię JSON
```

### Local session logging

```text
emit dwa eventy dla session aaa
→ logs/sessions/aaa.jsonl
→ dokładnie dwie linie
```

### Separate sessions

```text
session aaa
session bbb

→ osobne pliki
```

### Redaction

```text
data={"api_key": "secret"}
→ "***REDACTED***"
```

### BigQuery adapter

Nie używaj prawdziwego BigQuery w unit testach.

Wstrzyknij/mockuj klienta BigQuery.

Sprawdź:

```text
model
→ poprawny row
→ poprawna tabela
```

### Logging failure

```text
sink raises exception
→ business flow nie traci ContractState
```

### Session audit integration

Dla jednej tury sprawdź kolejność co najmniej:

```text
turn.started
intent.resolved
...
turn.completed
```

---

# 22. Test architektoniczny

Dodaj test lub prostą kontrolę, że w:

```text
adcm/domain/
adcm/application/
adcm/ports/
```

nie ma importów:

```text
google.cloud
pathlib/open w celu persystencji logów
BigQuery client
```

Infrastruktura należy do adapters.

---

# 23. Dokumentacja

Po implementacji zaktualizuj:

```text
docs/CURRENT_STATE.md
```

oraz dodaj:

```text
docs/logging-architecture.md
```

Dokument powinien opisać:

```text
AppLog
SessionAudit
porty
adapter local
adapter BigQuery
correlation_id
konfigurację
lokalizację plików
tabele BigQuery
```

Nie przepisuj całej architektury ADCM.

---

# 24. Czego NIE robić

Nie implementuj przy okazji:

```text
ExplicitSyntaxResolver
nowego IntentResolver
Schema Explorer MCP
ExternalCheck providers
nowych ux_rules
event sourcing całej aplikacji
Kafka
Pub/Sub
Cloud Logging
OpenTelemetry
distributed tracing framework
retry service
centralnego logging microservice
wspólnego Python package dla ADCM i Forge
```

Correlation ID wystarczy na obecny etap.

Nie refaktoryzuj istniejącego core poza minimalnymi punktami potrzebnymi do wstrzyknięcia portów logowania.

---

# 25. Oczekiwana struktura ADCM

Preferowany kierunek:

```text
ai-data-contract-manager/
│
├── src/adcm/
│   │
│   ├── domain/
│   │   └── logging/
│   │       ├── app_log.py
│   │       └── session_audit.py
│   │
│   ├── application/
│   │   └── logging/
│   │       └── session_audit_recorder.py
│   │
│   ├── ports/
│   │   ├── app_log_sink.py
│   │   └── session_audit_sink.py
│   │
│   └── adapters/
│       └── logging/
│           ├── local_app_log_sink.py
│           ├── local_session_audit_sink.py
│           ├── bigquery_app_log_sink.py
│           └── bigquery_session_audit_sink.py
│
└── logs/
    ├── app/
    └── sessions/
```

Nazwy można dostosować do istniejącego repo, ale zachowaj granice.

---

# 26. Oczekiwana struktura Forge

```text
mcp-contract-forge/
│
├── src/contract_forge/
│   ├── domain/
│   │   └── logging/
│   │
│   ├── ports/
│   │   └── app_log_sink.py
│   │
│   └── adapters/
│       └── logging/
│           ├── local_app_log_sink.py
│           └── bigquery_app_log_sink.py
│
└── logs/
    └── app/
```

Forge NIE dostaje session audit.

---

# 27. Kryteria akceptacji

Implementację uznaj za zakończoną tylko jeśli:

1. ADCM uruchamia się lokalnie bez BigQuery.
2. Forge uruchamia się lokalnie bez BigQuery.
3. Oba zapisują application logs do własnych `logs/`.
4. ADCM zapisuje osobny JSONL dla każdej sesji.
5. `intent.resolved` zawiera surowy structured output IntentResolver.
6. `mutation.applied` pozwala zobaczyć faktyczną zmianę dokumentu.
7. `proposal.decision` pokazuje dlaczego proposal został zastosowany lub odrzucony.
8. `turn.completed` zawiera finalny snapshot tury.
9. ADCM i Forge mogą używać BigQuery przez alternatywny adapter bez zmian w domain/application.
10. Awaria optional logging sink nie niszczy działania biznesowego.
11. Żaden sekret nie trafia do logów w jawnej postaci.
12. ADCM nie importuje kodu Forge.
13. Forge nie importuje kodu ADCM.
14. Wszystkie istniejące testy nadal przechodzą.
15. Nowe testy logowania przechodzą.
16. Nie zostały zmienione reguły biznesowe istniejącego core.

---

# 28. Sposób pracy

Najpierw przeczytaj istniejące:

```text
docs/
ai-data-contract-manager/src/
mcp-servers/mcp-contract-forge/src/
```

W szczególności ustal faktyczne:

```text
TurnOrchestrator
ContractState
MutationEvent
IntentResolverPort
StabilizationEngine
composition root
Forge entrypoint
```

Nie zakładaj nazw metod na podstawie tego dokumentu — dostosuj implementację do faktycznego kodu.

Przed implementacją wypisz krótko:

```text
- które istniejące pliki będą dotknięte,
- jakie nowe pliki powstaną,
- gdzie zostanie wykonany dependency injection,
- jakie nowe dependencies zostaną dodane do każdego serwisu.
```

Jeżeli implementacja wymaga dużego refaktoru core, zatrzymaj się i zgłoś problem zamiast tworzyć obejście.

---

# 29. Handoff po implementacji

Na końcu odpowiedz:

## Handoff

* goal:
* new_modules:
* changed_files:
* ports_added:
* adapters_added:
* configuration:
* app_log_flow:
* session_audit_flow:
* tests_added:
* tests_result:
* architectural_decisions:
* known_limitations:
* next_recommended_step:


# ADCM — przykładowy oczekiwany Session Audit JSONL

## Cel

Poniższy JSONL jest wzorcem oczekiwanego logowania jednej tury ADCM.

Przykładowa wiadomość użytkownika:

```text
sourceSystemGcpId = sap, dataFileId = sap_id
```

Zakładamy przykładowy stan przed turą:

```json
{
  "metadata": {
    "id": "sap_pipeline",
    "version": "1.0.0"
  }
}
```

Po poprawnym przetworzeniu wiadomości użytkownika oczekujemy co najmniej:

```text
/metadata/sourceSystemGcpId = sap
/metadata/dataFileId = sap_id
```

jako wartości `USER_EXPLICIT`.

Dalsze wartości mogą zostać wyprowadzone przez ADCM rules lub Forge.

---

# Zasady wzorca

Każda linia pliku jest osobnym poprawnym obiektem JSON.

Plik:

```text
logs/sessions/aaa.jsonl
```

Nie zapisuj JSON-a jako jednej tablicy.

Wzorzec pokazuje znaczenie eventów, a nie konkretne UUID/timestampy.

Dozwolone są dodatkowe eventy, jeżeli dostarczają użytecznej diagnostyki.

Nie wolno jednak pomijać kluczowych punktów:

```text
turn.started
user.message.received
intent.resolved
candidate.*
mutation.applied
forge.analysis.*
rule.proposal.generated
proposal.decision
stabilization.*
response.composed
turn.completed
```

---

# Przykładowy JSONL

```jsonl
{"event_id":"evt-001","timestamp":"2026-08-29T15:10:00.000Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"turn.started","data":{"contract_revision":2}}
{"event_id":"evt-002","timestamp":"2026-08-29T15:10:00.005Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"user.message.received","data":{"message":"sourceSystemGcpId = sap, dataFileId = sap_id"}}
{"event_id":"evt-003","timestamp":"2026-08-29T15:10:00.420Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"intent.resolved","data":{"resolver":"pydantic_ai","candidates":[{"candidate_id":"cand-001","operation":"add","path":"/metadata/sourceSystemGcpId","value":"sap","confidence":0.99,"evidence":"sourceSystemGcpId = sap"},{"candidate_id":"cand-002","operation":"add","path":"/metadata/dataFileId","value":"sap_id","confidence":0.99,"evidence":"dataFileId = sap_id"}],"unresolved":[]}}
{"event_id":"evt-004","timestamp":"2026-08-29T15:10:00.425Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"candidate.accepted","data":{"candidate_id":"cand-001","operation":"add","path":"/metadata/sourceSystemGcpId","value":"sap","source":"user_explicit","reason":"candidate accepted by policy"}}
{"event_id":"evt-005","timestamp":"2026-08-29T15:10:00.426Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"candidate.accepted","data":{"candidate_id":"cand-002","operation":"add","path":"/metadata/dataFileId","value":"sap_id","source":"user_explicit","reason":"candidate accepted by policy"}}
{"event_id":"evt-006","timestamp":"2026-08-29T15:10:00.430Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"mutation.applied","data":{"mutation_id":"mut-001","revision_before":2,"revision_after":3,"operation":"add","path":"/metadata/sourceSystemGcpId","old_exists":false,"old_value":null,"new_exists":true,"new_value":"sap","source":"user_explicit","producer_id":"cand-001","reason":"explicit user value"}}
{"event_id":"evt-007","timestamp":"2026-08-29T15:10:00.432Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"mutation.applied","data":{"mutation_id":"mut-002","revision_before":3,"revision_after":4,"operation":"add","path":"/metadata/dataFileId","old_exists":false,"old_value":null,"new_exists":true,"new_value":"sap_id","source":"user_explicit","producer_id":"cand-002","reason":"explicit user value"}}
{"event_id":"evt-008","timestamp":"2026-08-29T15:10:00.440Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.started","data":{"round":1,"contract_revision":4}}
{"event_id":"evt-009","timestamp":"2026-08-29T15:10:00.442Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"forge.analysis.started","data":{"round":1,"contract_revision":4}}
{"event_id":"evt-010","timestamp":"2026-08-29T15:10:00.465Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"forge.analysis.completed","data":{"round":1,"protocol_version":"1.0","definition_version":"baseline-1","status":{"valid":true,"complete":false,"clean":true},"missing":["/source/sourceType"],"diagnostics":[],"foreign":[],"proposals":[{"id":"default:/metadata/version","path":"/metadata/version","value":"1.0.0","origin":"default"},{"id":"global-or-forge-example","path":"/source/encoding","value":"UTF-8","origin":"enrichment"}],"duration_ms":23}}
{"event_id":"evt-011","timestamp":"2026-08-29T15:10:00.470Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"rule.proposal.generated","data":{"proposal_id":"rule:global.source_system.metadata_id","rule_id":"global.source_system.metadata_id","scope":"global","priority":100,"path":"/metadata/id","value":"sap","source":"app_rule","derived_from":["/metadata/sourceSystemGcpId"]}}
{"event_id":"evt-012","timestamp":"2026-08-29T15:10:00.471Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"rule.proposal.generated","data":{"proposal_id":"rule:sap.source_type","rule_id":"sap.source_type","scope":"system","system":"sap","priority":100,"path":"/source/sourceType","value":"csv","source":"app_rule","derived_from":["/metadata/sourceSystemGcpId"]}}
{"event_id":"evt-013","timestamp":"2026-08-29T15:10:00.472Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"rule.proposal.generated","data":{"proposal_id":"rule:global.source_system.source_metadata","rule_id":"global.source_system.source_metadata","scope":"global","priority":100,"path":"/source/systemZrodlowy","value":"sap","source":"app_rule","derived_from":["/metadata/sourceSystemGcpId"]}}
{"event_id":"evt-014","timestamp":"2026-08-29T15:10:00.474Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"proposal.decision","data":{"proposal_id":"rule:global.source_system.metadata_id","path":"/metadata/id","proposed_value":"sap","current_value":"sap_pipeline","current_source":"user_explicit","proposal_source":"app_rule","action":"keep_current","reason":"higher authority current value"}}
{"event_id":"evt-015","timestamp":"2026-08-29T15:10:00.475Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"proposal.decision","data":{"proposal_id":"rule:sap.source_type","path":"/source/sourceType","proposed_value":"csv","current_value":null,"current_source":null,"proposal_source":"app_rule","action":"apply","reason":"target has no current value"}}
{"event_id":"evt-016","timestamp":"2026-08-29T15:10:00.476Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"proposal.decision","data":{"proposal_id":"rule:global.source_system.source_metadata","path":"/source/systemZrodlowy","proposed_value":"sap","current_value":null,"current_source":null,"proposal_source":"app_rule","action":"apply","reason":"target has no current value"}}
{"event_id":"evt-017","timestamp":"2026-08-29T15:10:00.480Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"mutation.applied","data":{"mutation_id":"mut-003","revision_before":4,"revision_after":5,"operation":"add","path":"/source/sourceType","old_exists":false,"old_value":null,"new_exists":true,"new_value":"csv","source":"app_rule","producer_id":"sap.source_type","reason":"accepted rule proposal"}}
{"event_id":"evt-018","timestamp":"2026-08-29T15:10:00.481Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"mutation.applied","data":{"mutation_id":"mut-004","revision_before":5,"revision_after":6,"operation":"add","path":"/source/systemZrodlowy","old_exists":false,"old_value":null,"new_exists":true,"new_value":"sap","source":"app_rule","producer_id":"global.source_system.source_metadata","reason":"accepted rule proposal"}}
{"event_id":"evt-019","timestamp":"2026-08-29T15:10:00.485Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.completed","data":{"round":1,"changed":true,"revision_before":4,"revision_after":6}}
{"event_id":"evt-020","timestamp":"2026-08-29T15:10:00.490Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.started","data":{"round":2,"contract_revision":6}}
{"event_id":"evt-021","timestamp":"2026-08-29T15:10:00.492Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"forge.analysis.started","data":{"round":2,"contract_revision":6}}
{"event_id":"evt-022","timestamp":"2026-08-29T15:10:00.515Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"forge.analysis.completed","data":{"round":2,"protocol_version":"1.0","definition_version":"baseline-1","status":{"valid":true,"complete":true,"clean":true},"missing":[],"diagnostics":[],"foreign":[],"proposals":[{"id":"default:/metadata/version","path":"/metadata/version","value":"1.0.0","origin":"default"},{"id":"csv.default_encoding","path":"/source/encoding","value":"UTF-8","origin":"enrichment"}],"duration_ms":23}}
{"event_id":"evt-023","timestamp":"2026-08-29T15:10:00.520Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"proposal.decision","data":{"proposal_id":"forge:default:/metadata/version","path":"/metadata/version","proposed_value":"1.0.0","current_value":"1.0.0","current_source":"forge_default","proposal_source":"forge_default","action":"keep_current","reason":"already applied"}}
{"event_id":"evt-024","timestamp":"2026-08-29T15:10:00.521Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"proposal.decision","data":{"proposal_id":"forge:csv.default_encoding","path":"/source/encoding","proposed_value":"UTF-8","current_value":null,"current_source":null,"proposal_source":"forge_enrichment","action":"apply","reason":"target has no current value"}}
{"event_id":"evt-025","timestamp":"2026-08-29T15:10:00.525Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"mutation.applied","data":{"mutation_id":"mut-005","revision_before":6,"revision_after":7,"operation":"add","path":"/source/encoding","old_exists":false,"old_value":null,"new_exists":true,"new_value":"UTF-8","source":"forge_enrichment","producer_id":"csv.default_encoding","reason":"accepted Forge proposal"}}
{"event_id":"evt-026","timestamp":"2026-08-29T15:10:00.530Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.completed","data":{"round":2,"changed":true,"revision_before":6,"revision_after":7}}
{"event_id":"evt-027","timestamp":"2026-08-29T15:10:00.535Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.started","data":{"round":3,"contract_revision":7}}
{"event_id":"evt-028","timestamp":"2026-08-29T15:10:00.560Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"forge.analysis.completed","data":{"round":3,"protocol_version":"1.0","definition_version":"baseline-1","status":{"valid":true,"complete":true,"clean":true},"missing":[],"diagnostics":[],"foreign":[],"proposal_count":2}}
{"event_id":"evt-029","timestamp":"2026-08-29T15:10:00.565Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.round.completed","data":{"round":3,"changed":false,"revision_before":7,"revision_after":7}}
{"event_id":"evt-030","timestamp":"2026-08-29T15:10:00.566Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"stabilization.completed","data":{"rounds":3,"converged":true,"final_revision":7}}
{"event_id":"evt-031","timestamp":"2026-08-29T15:10:00.570Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"external_checks.completed","data":{"performed":[],"skipped":[],"failed":[],"degraded":false}}
{"event_id":"evt-032","timestamp":"2026-08-29T15:10:00.590Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"response.composed","data":{"message":"valid=True, complete=True, clean=True"}}
{"event_id":"evt-033","timestamp":"2026-08-29T15:10:00.595Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"turn.completed","data":{"contract_revision":7,"final_document":{"metadata":{"sourceSystemGcpId":"sap","id":"sap_pipeline","version":"1.0.0","dataFileId":"sap_id"},"source":{"sourceType":"csv","systemZrodlowy":"sap","encoding":"UTF-8"}},"forge_status":{"valid":true,"complete":true,"clean":true},"missing":[],"diagnostics":[],"external_checks":{"performed":[],"skipped":[],"failed":[],"degraded":false},"stabilization":{"rounds":3,"converged":true},"response":"valid=True, complete=True, clean=True"}}
```

# Ważne znaczenie diagnostyczne

Dla wiadomości:

```text
sourceSystemGcpId = sap, dataFileId = sap_id
```

najważniejsza jest linia:

```text
intent.resolved
```

Poprawny wynik zawiera dwa candidates:

```text
/metadata/sourceSystemGcpId = sap
/metadata/dataFileId = sap_id
```

Niepoprawnym wynikiem byłoby przykładowo:

```json
{
  "path": "/source/systemZrodlowy",
  "value": "sap"
}
```

jeżeli użytkownik jawnie podał `sourceSystemGcpId`.

Log musi pozwalać ustalić, że błąd powstał już w `IntentResolver`, zanim wartość została zapisana do `ContractState`.

---

# Rozróżnienie proposal i mutation

Log musi pokazywać osobno:

```text
rule.proposal.generated
proposal.decision
mutation.applied
```

Przykład:

```text
ux_rule:
metadata.id = sap

ale:

aktualne metadata.id = sap_pipeline
source = USER_EXPLICIT
```

W logu oczekujemy:

```text
rule.proposal.generated
    ↓
proposal.decision = keep_current
```

i NIE oczekujemy:

```text
mutation.applied
```

dla `/metadata/id`.

Proposal nie oznacza mutacji.

---

# Rozróżnienie provenance

Każda faktyczna mutacja powinna umożliwiać identyfikację źródła.

Oczekiwane źródła:

```text
user_explicit
user_rule
app_rule
forge_enrichment
forge_default
```

Przykład:

```text
/metadata/dataFileId
source=user_explicit
```

versus:

```text
/source/sourceType
source=app_rule
producer_id=sap.source_type
```

versus:

```text
/source/encoding
source=forge_enrichment
producer_id=csv.default_encoding
```

---

# Candidate rejected

Jeżeli candidate zostanie odrzucony, nie może po prostu zniknąć.

Przykład:

```jsonl
{"event_id":"evt-example","timestamp":"2026-08-29T15:10:00.000Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"candidate.rejected","data":{"candidate_id":"cand-009","path":"/unknown/value","value":"abc","confidence":0.72,"reason":"path not writable in current contract shape"}}
```

---

# Candidate deferred

Analogicznie:

```jsonl
{"event_id":"evt-example","timestamp":"2026-08-29T15:10:00.000Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"candidate.deferred","data":{"candidate_id":"cand-010","value":"separator=;","confidence":0.88,"reason":"target path cannot yet be resolved before source type is known"}}
```

Taki event będzie ważny dla późniejszej obsługi danych podanych przez użytkownika przed ustaleniem wariantu kontraktu.

---

# Turn failure

W przypadku błędu tura powinna zakończyć się np.:

```jsonl
{"event_id":"evt-fail","timestamp":"2026-08-29T15:10:00.000Z","session_id":"aaa","turn_no":2,"correlation_id":"turn-aaa-2","event_type":"turn.failed","data":{"error_type":"ForgeUnavailable","component":"stabilization","message":"Contract Forge unavailable","contract_revision":4}}
```

Nie zapisuj:

```text
API key
Authorization header
pełnego stack trace zawierającego sekrety
credentials
```

Stack trace może być zapisany w application log po sanitizacji.

---

# Wymagania implementacyjne wynikające ze wzorca

Nie implementuj logowania tak, aby cały `SessionAuditEvent.data` był generowany dopiero na końcu tury.

Event ma powstawać w momencie wystąpienia zdarzenia.

W szczególności:

```text
intent.resolved
```

musi zostać zapisane bezpośrednio po `IntentResolver.resolve()` i przed CandidatePolicy.

```text
proposal.decision
```

musi powstać bezpośrednio po decyzji ProposalReconciler.

```text
mutation.applied
```

powstaje tylko wtedy, gdy `DocumentEngine` rzeczywiście zmienił stan.

`turn.completed` jest snapshotem końcowym i nie zastępuje wcześniejszych eventów.

---

# Kryterium diagnostyczne

Po odczytaniu jednego `<session_id>.jsonl` programista lub LLM powinien móc bez uruchamiania aplikacji ustalić:

1. co napisał użytkownik;
2. jak wiadomość zinterpretował LLM;
3. jakie candidate powstały;
4. które candidate zostały zaakceptowane/odrzucone;
5. jakie mutacje rzeczywiście wykonano;
6. z jakiego źródła pochodzi każda automatyczna wartość;
7. jakie proposals wygenerowały Forge i ADCM rules;
8. dlaczego proposal wygrał lub przegrał;
9. jakie dokumenty przechodziły przez kolejne rundy stabilizacji;
10. dlaczego fixed point się zakończył;
11. jaki był finalny stan kontraktu;
12. jaką odpowiedź dostał użytkownik.

Jeżeli któregoś z tych pytań nie można rozstrzygnąć na podstawie Session Audit, logowanie jest niewystarczające.
