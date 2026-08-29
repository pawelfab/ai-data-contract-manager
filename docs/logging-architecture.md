# Logging i obserwowalność

Szczegółowy opis przepływu, integracji poza modułem observability, audytu
overengineeringu i zgodności z guardrails znajduje się w
[`logging-implementation-guide.md`](logging-implementation-guide.md).

## Zakres

ADCM i Contract Forge mają niezależne implementacje obserwowalności. Modele
`AppLogEvent` i `SessionAuditEvent` znajdują się w `application/observability`,
poza `domain/`. Domena pozostaje właścicielem `ContractState`, `MutationEvent`
i `ValueProvenance`; zdarzenia audytowe są mapowaniem faktów domenowych na
format obserwowalności.

## AppLog i SessionAudit

Application log opisuje działanie procesu: startup, HTTP, resolver/LLM,
wywołania Forge i błędy. Jest dostępny w obu usługach.

Session audit istnieje tylko w ADCM i opisuje przebieg tury sesji: resolution,
decyzje kandydatów, rundy stabilizacji, propozycje, mutacje, kontrole
zewnętrzne oraz odpowiedź. `MutationEvent` jest emitowany jako
`mutation.applied` tylko po rzeczywistym zastosowaniu zmiany.

## Audyt jako widok modeli domenowych

Session audit nie jest kopią 1:1 modeli core. Mapowanie
`ForgeAnalysis`/`TurnOutcome` na payload audytowy należy do
`application/observability/audit_views.py`; modele domenowe pozostają pełne.

Obowiązują dwie zasady. Dane mające własny dedykowany event nie są powtarzane
w evencie zbiorczym: propozycje pozostają w `forge.proposal.received` oraz
`rule.proposal.generated`, a decyzje w `proposal.decision`, dlatego
`forge.analysis.completed` podaje tylko `proposal_count`, a `turn.completed`
tylko `{rounds, converged}` zamiast całej historii `proposal_decisions[]`. Dane
niezmienne między rundami fixed-point nie są zapisywane w każdej rundzie:
`forge.analysis.completed` podaje `writable_count` zamiast `writable[]` oraz
listę ścieżek zamiast pełnych obiektów `MissingRequirement`.

`turn.completed` pozostaje pełnym snapshotem końcowym tury: dokument, status
Forge, brakujące wymagania, diagnostyka, kontrole zewnętrzne i odpowiedź. Numery
rund i rewizje (`round`, `contract_revision`, `revision_before`,
`revision_after`) oraz envelope eventu pozostają nienaruszone.

`ADCM_AUDIT_LEVEL=debug` przywraca pełny `ForgeAnalysis` w
`forge.analysis.completed` i pełne `MissingRequirement` w `turn.completed`.

## Porty i adaptery

Recordery w warstwie application korzystają z portów sinków. Adaptery
zapewniają local JSONL i BigQuery. Kod domenowy nie zna sinków, systemu plików
ani klienta Google.

Local application log zapisuje do `logs/app/YYYY-MM-DD.jsonl`. ADCM zapisuje
audit do `logs/sessions/<bezpieczny-session-id>.jsonl`. Każdy serwis posiada
własny katalog `logs/`; Docker Compose montuje go jako `/app/logs` danego
kontenera.

## BigQuery i batching

Application events są zapisywane do tabeli `app_logs`. ADCM session audit
trafia do tabeli `session_audit`. Konfiguracja określa projekt, dataset i nazwy
tabel przez `*_BQ_PROJECT`, `*_BQ_DATASET`, `*_BQ_APP_LOG_TABLE` oraz
`ADCM_BQ_SESSION_AUDIT_TABLE`.

BigQuery session-audit sink buforuje eventy per `(session_id, turn_no,
correlation_id)`. Eventy powstają natychmiast w miejscu zdarzenia, ale jeden
batch jest wysyłany dopiero przy `turn.completed` albo `turn.failed`. Logika
batchowania należy do adaptera, nie do orchestratora.

Bufor jest procesowy. Nagłe zakończenie procesu przed eventem terminalnym może
utracić nieopróżnione eventy; trwała kolejka i retry są poza zakresem MVP.

## Polityka błędów i redakcja

Awaria application sinka jest ignorowana po zgłoszeniu na `stderr`. Awaria
session audit nie zatrzymuje przepływu biznesowego, ale recorder próbuje
zapisać application error `session_audit_sink_failed` z sesją, turą, korelacją,
typem niezapisanego eventu oraz liczbą eventów zagrożonego batcha. Jeżeli ten
zapis również się nie powiedzie, pozostaje `stderr`.

Przed zapisem wykonywana jest rekurencyjna, case-insensitive redakcja sekretów,
nagłówków autoryzacji, cookies, credentials i typowych tokenów zapisanych w
tekście.

## Correlation ID

`correlation_id` jest wyłącznie technicznym metadanym transportu i
obserwowalności. ADCM przekazuje go w wywołaniu MCP do Forge, aby połączyć logi.
Nie jest wejściem biznesowym Forge, nie należy do analizy ani opisu kontraktu i
nigdy nie wpływa na wynik: dla tego samego dokumentu różne identyfikatory
korelacji muszą dawać identyczne `ForgeAnalysis` i `ForgeDescription`.

## Konfiguracja

Obie usługi domyślnie używają backendu `local`.

ADCM:

- `ADCM_LOG_BACKEND`, `ADCM_LOG_DIR`, `ADCM_ENVIRONMENT`,
- `ADCM_AUDIT_LEVEL` (`normal` domyślnie, `debug` = pełny `ForgeAnalysis`),
- `ADCM_BQ_PROJECT`, `ADCM_BQ_DATASET`,
- `ADCM_BQ_APP_LOG_TABLE`, `ADCM_BQ_SESSION_AUDIT_TABLE`.

Forge:

- `FORGE_LOG_BACKEND`, `FORGE_LOG_DIR`, `FORGE_ENVIRONMENT`,
- `FORGE_BQ_PROJECT`, `FORGE_BQ_DATASET`, `FORGE_BQ_APP_LOG_TABLE`.

Backend BigQuery wymaga opcjonalnej instalacji `requirements-bigquery.txt` lub
extra `bigquery`. Backend nie jest wykrywany heurystycznie.

## Schematy tabel

`app_logs` zawiera: `event_id`, `timestamp`, `level`, `service`, `environment`,
`component`, `event`, opcjonalne `message`, `correlation_id`, `session_id`,
`turn_no`, `duration_ms` i strukturalne `data`.

`session_audit` zawiera: `event_id`, `timestamp`, `session_id`, `turn_no`,
`event_type`, `correlation_id` i strukturalne `data`.
