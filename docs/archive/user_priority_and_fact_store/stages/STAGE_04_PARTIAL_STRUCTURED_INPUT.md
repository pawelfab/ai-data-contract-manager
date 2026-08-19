# STAGE 04 — partial structured input bez powtarzania całego pytania

## GOAL

Naprawić przypadek takich danych:

```text
data_d, sap1, sap2, sap3
```

gdy Forge wymaga np. `array<object>` i pełny obiekt wymaga jeszcze `dataType`.

ADCM ma:
- zachować użyteczną część informacji;
- określić, czego brakuje;
- dopytać tylko o brak;
- nie zapisywać invalid partial structure do canonical contract.

## IMPORTANT

Nie implementuj tego jako specjalnego `if path == "source.columns"` jeśli można oprzeć się na `value_schema` requirementu.

Dopuszczalny jest mały adapter/heurystyka dla typowego `array<object>`, ale nazwa konkretnego path nie powinna być warunkiem działania.

## REQUIRED SCHEMA INFO

Requirement dla złożonego pola powinien udostępniać przynajmniej:

```text
type=array
items.type=object
items.properties
items.required
```

Jeżeli obecny Forge tego nie zwraca, rozszerz publiczny fragment schema tylko o elementy niezbędne do tego stage'u.

Nie buduj pełnego uniwersalnego JSON Schema engine.

## SIMPLE PARTIAL MODEL

Może być np.:

```python
class PartialFact(BaseModel):
    path: str
    value: Any
    missing: list[str]
    message_sequence: int
```

Albo prostsza struktura w ConversationMemory.

Nie potrzebujemy teraz generalnego systemu dependency graph.

## EXPECTED FLOW

Forge:
```text
source.columns -> array<object>
required item fields: name, dataType
```

User:
```text
data_d, sap1, sap2, sap3
```

ADCM rozpoznaje:
```json
[
  {"name": "data_d"},
  {"name": "sap1"},
  {"name": "sap2"},
  {"name": "sap3"}
]
```

ADCM NIE wysyła tego do Forge jako kompletnego candidate.

ADCM pyta np.:

```text
Rozpoznałem 4 kolumny, ale brakuje ich typów danych.
Podaj typy, np.:
data_d DATE
sap1 STRING
sap2 STRING
sap3 NUMERIC
```

Po odpowiedzi scala dane i dopiero wtedy submituje pełną wartość.

## DETERMINISTIC FIRST

Obsłuż deterministycznie przynajmniej:
- JSON array of objects;
- `name TYPE`;
- multiline `name TYPE`;
- comma/newline-separated same names;
- typy już zgodne z enum ze schema.

Nie zgaduj typów, jeśli user ich nie podał.

## OPTIONAL NORMALIZATION

Możesz mapować oczywiste reprezentacje tylko wtedy, gdy istnieje jawna bezpieczna reguła, np.:
- lowercase `date` -> enum `DATE`;
- case-insensitive enum matching.

Nie mapuj arbitralnie Oracle `NUMBER(15,2)` -> `NUMERIC` w tym stage, jeśli wymaga to semantycznej decyzji. To może zrobić później LLM lub osobna deterministyczna tabela typów, jeśli zostanie uzgodniona.

## TODO

1. Rozszerz requirement schema fragment o minimalne `items/properties/required`.
2. Dodaj partial storage.
3. Dodaj generic `array<object>` deterministic parser.
4. Przy incomplete input:
   - zachowaj partial;
   - wygeneruj narrower clarification;
   - nie powtarzaj oryginalnego pytania bez wyjaśnienia.
5. Po kolejnej wiadomości spróbuj scalić partial z nową informacją.
6. Po uzyskaniu kompletnej wartości submit do Forge.
7. Po akceptacji usuń partial dla path.

## TESTS

### T1
`data_d, sap1,sap2,sap3` -> partial, brak submitu do Forge.

### T2
Kolejna wiadomość z typami -> poprawny complete candidate.

### T3
`data_d DATE\nsap1 STRING` -> bez partial, jeśli wszystkie required item fields są obecne.

### T4
Invalid datatype -> nie zgaduj; pokaż clarification.

### T5
Parser działa na testowym `array<object>` path o innej nazwie niż `source.columns`.

To jest ważny test przeciw hardkodowaniu path.

## NON-GOALS

Nie implementuj:
- dowolnej zagnieżdżonej struktury JSON Schema;
- LLM;
- automatycznych typów Oracle/DB2/SQL Server;
- UI widgetów.

## DONE WHEN

Incomplete structured input jest zachowywany i doprecyzowywany zamiast powodować powtarzanie tego samego pytania.
