# STAGE 01 — precedence źródeł wartości w Contract Forge

## GOAL

Wprowadzić prosty, deterministyczny mechanizm rozstrzygania **źródeł wartości** w Forge.

Dla tego samego path ma obowiązywać:

`USER > SYSTEM_ENRICHMENT > GENERIC_ENRICHMENT > SCHEMA_DEFAULT`

Ten stage **nie rozstrzyga kolejności kilku wypowiedzi usera**. Recency usera należy do ADCM i będzie implementowane w Stage 02.

## ARCHITECTURAL BOUNDARY

**Precedence źródeł wartości należy do Contract Forge**, bo Forge jest właścicielem:
- canonical contract;
- enrichmentów;
- schema defaults;
- provenance;
- końcowej walidacji zapisywanej wartości.

ADCM może powiedzieć:
- path;
- value;
- `origin=USER`;
- opcjonalnie metadata audytowe, np. `message_sequence`;
- metodę ekstrakcji (`deterministic` / `llm`).

ADCM nie może sam nadpisywać contract dict.

### Ważne rozdzielenie odpowiedzialności

ADCM odpowiada za:

```text
USER message #9 > USER message #3
```

Forge odpowiada za:

```text
USER > SYSTEM_ENRICHMENT > GENERIC_ENRICHMENT > SCHEMA_DEFAULT
```

Forge nie analizuje transcriptu i nie ustala, która wiadomość usera jest nowsza.

## SIMPLE MODEL

Nie buduj rozbudowanego event sourcing.

Wystarczy prosty model np.:

```python
class ValueOrigin(str, Enum):
    USER = "user"
    SYSTEM_ENRICHMENT = "system_enrichment"
    GENERIC_ENRICHMENT = "generic_enrichment"
    SCHEMA_DEFAULT = "schema_default"
    STRUCTURAL = "structural"
```

oraz provenance przy zapisanej wartości:

```python
class ValueProvenance(BaseModel):
    origin: ValueOrigin
    rule_id: str | None = None

    # Pole opcjonalne, wyłącznie do audytu/debugowania.
    # Forge nie używa go do ustalania recency usera.
    message_sequence: int | None = None
```

Jeśli repo ma już podobne modele, wykorzystaj je zamiast duplikować.

## PRECEDENCE RULE

Użyj jednej centralnej funkcji, np.:

```python
can_replace(current, candidate) -> bool
```

Reguła między różnymi origin:

1. brak current -> przyjmij;
2. wyższy origin priority -> przyjmij;
3. niższy origin priority -> odrzuć.

Dla tego samego origin:
- `USER -> USER`: przyjmij nowy poprawny submit. ADCM ma obowiązek wysłać najnowszy fakt użytkownika;
- enrichment/default -> ten sam origin: zachowaj obecne deterministyczne zachowanie silnika i nie dodawaj mechanizmu recency wiadomości.

Nie implementuj w Forge:
```python
if candidate.message_sequence > current.message_sequence:
```
jako reguły wyboru między wypowiedziami usera.

To należy do ADCM.

## IMPORTANT

Informacja wydobyta z usera przez LLM ma:

```text
origin=USER
extraction_method=LLM
```

`extraction_method` nie uczestniczy w precedence Forge.

## TODO

1. Znajdź obecny model origin/provenance i `ORIGIN_PRIORITY`.
2. Jeśli `ORIGIN_PRIORITY` istnieje, zacznij go faktycznie używać.
3. Wprowadź centralną funkcję precedence dla **originów**.
4. Zmień zapisy wykonywane przez:
   - system enrichment;
   - generic enrichment;
   - schema default;
   - candidate USER;
   tak, aby przechodziły przez ten sam mechanizm zapisu/provenance.
5. Pozwól Forge przyjąć USER candidate również wtedy, gdy path ma już wartość z:
   - system enrichment;
   - generic enrichment;
   - schema default.
6. Pozwól poprawnemu nowemu USER candidate zastąpić aktualny USER value.
   - Forge traktuje późniejszy submit jako nową intencję klienta.
   - Forge nie analizuje transcriptu ani message recency.
7. Nie pozwalaj USER candidate pisać do path, którego Forge/schema nie zna.
8. Walidacja schema nadal obowiązuje przed zapisaniem USER override.
9. Zachowaj provenance wartości po wygraniu kandydata.
10. Jeśli USER candidate jest niepoprawny względem schema:
    - nie usuwaj poprawnego enrichment/default/current USER value;
    - zwróć rejection/validation issue.

## NON-GOALS

Nie implementuj:
- skanowania historii rozmowy;
- latest-user-fact resolution;
- UserFact store;
- LLM;
- `pending + overridable` w orchestratorze;
- nowych parserów;
- arbitrary schema support.

## TESTS

### T1 — USER nadpisuje system enrichment

Current:
```text
schedule = "0 0 * * *"
origin = SYSTEM_ENRICHMENT
```

Incoming:
```text
schedule = "0 6 * * *"
origin = USER
```

Expected:
```text
"0 6 * * *"
origin = USER
```

### T2 — enrichment nie nadpisuje USER

Current:
```text
origin = USER
```

Incoming:
```text
origin = GENERIC_ENRICHMENT
```

USER pozostaje.

### T3 — SYSTEM enrichment kontra GENERIC enrichment

SYSTEM wygrywa.

### T4 — GENERIC enrichment kontra SCHEMA_DEFAULT

GENERIC wygrywa.

### T5 — USER może poprawić wcześniejszy USER value

Forge ma:
```text
owner = team_a
origin = USER
```

Klient wysyła później:
```text
owner = team_b
origin = USER
```

Expected:
```text
owner = team_b
origin = USER
```

Ten test nie sprawdza `message_sequence`.
Zakładamy, że klient/ADCM wysyła aktualną intencję usera.

### T6 — invalid USER override nie niszczy current value

Current value pozostaje bez zmian.

## DONE WHEN

Forge ma jeden spójny mechanizm precedence originów:

`USER > SYSTEM_ENRICHMENT > GENERIC_ENRICHMENT > SCHEMA_DEFAULT`

i nie przejmuje odpowiedzialności za ustalanie, która wypowiedź usera była najnowsza.

## STOP

Nie implementuj Stage 02 ani dalszych.
