# STAGE 06 — ograniczenie hardkodowania przez schema-driven Requirement

## GOAL

Usunąć z ADCM te zależności od konkretnych pathów, które można zastąpić metadanymi wystawianymi przez Forge.

Nie próbujemy obsłużyć dowolnego możliwego JSON Schema.

## CURRENT PROBLEM TO LOOK FOR

W obecnych heurystykach mogą istnieć konstrukcje typu:

```python
if path == "metadata.id":
...
if path == "metadata.owner":
...
if path == "source.columns":
...
```

Część specjalizowanych parserów może pozostać, ale preferowany wybór powinien wynikać z `Requirement.value_schema` i metadanych.

## MINIMAL REQUIREMENT CONTRACT

Forge powinien wystawiać dla requirementu tylko tyle, ile ADCM potrzebuje:

```python
class Requirement(BaseModel):
    path: str
    question: str | None
    description: str | None
    value_schema: dict[str, Any]
    examples: list[Any] = []
```

`value_schema` w minimalnym wspieranym zakresie powinno umieć przekazać:
- `type`;
- `enum`;
- `const`;
- `pattern`;
- `format`;
- `minLength` / `maxLength`;
- `minimum` / `maximum`;
- `items`;
- `properties`;
- `required`;
- podstawowe nested `$ref` rozwiązane przez Forge do potrzebnego fragmentu.

Jeśli obecny model ma inne nazwy, nie twórz duplikatu bez potrzeby.

## GENERIC DETERMINISTIC RESOLVERS

Preferuj heurystyki według schema:

### enum/const
- case-insensitive exact match;
- bezpieczny fuzzy match tylko przy wysokiej pewności i jednoznacznym wyniku.

### boolean
- `tak/nie`, `true/false`, itp.

### integer/number
- parse bez semantycznego zgadywania.

### string + pattern
- waliduj/normalizuj tylko reprezentację;
- nie wymyślaj biznesowej wartości.

### format URI/date
- parsuj standardowe formy.

### array<object>
- użyj mechanizmu Stage 04.

### generic string
- jeśli user odpowiada bezpośrednio na aktualne pytanie, może być candidate po schema validation.

## PATH-SPECIFIC HEURISTICS

Dopuszczalne tylko gdy:
- rozwiązują realny problem UX;
- nie da się tego wyrazić poprzez schema metadata;
- są izolowane jako optional specialized resolver, a nie core orchestrator logic.

Przykład:
- parser wklejonych kolumn może być specjalizowany przez **shape** `array<object>`, nie przez `source.columns`.

## PRECEDENCE / RECENCY BOUNDARY

Ten stage nie zmienia odpowiedzialności z wcześniejszych etapów:

- schema-driven `Requirement` mówi ADCM **jakiego rodzaju wartości Forge oczekuje**;
- ADCM nadal wybiera najnowszy UserFact;
- Forge nadal rozstrzyga `USER > SYSTEM_ENRICHMENT > GENERIC_ENRICHMENT > SCHEMA_DEFAULT`.

Nie przenoś precedence do generic resolvera ani do schema metadata.

## FUTURE COMPATIBILITY

Projektuj interfejs tak, aby w przyszłości można było rozszerzyć `value_schema`, ale teraz NIE implementuj:

- remote `$ref`;
- pełnego recursive arbitrary schema;
- `allOf`;
- dowolnego `anyOf`;
- conditional schema evaluation po stronie ADCM;
- custom business rule execution po stronie ADCM.

Jeśli schema staje się bardziej złożone, Forge nadal ma być warstwą, która je interpretuje i upraszcza do Requirement dla ADCM.

## TODO

1. Zidentyfikuj path-specific warunki w ADCM.
2. Dla każdego zdecyduj:
   - replace by schema-driven logic;
   - keep as isolated specialization z uzasadnieniem.
3. Rozszerz `Requirement.value_schema` tylko o brakujące informacje.
4. Zrefaktoruj deterministic resolver do małych handlerów typu:
   - enum;
   - boolean;
   - number;
   - string;
   - array/object.
5. Orchestrator ma operować na `Requirement`, nie na wiedzy o polach kontraktu.
6. Dodaj test z nowym wymaganym polem w testowym contract schema, którego nazwa nie istnieje w kodzie.
7. Potwierdź, że ADCM potrafi:
   - zobaczyć nowe required string/enum;
   - zapytać usera;
   - przyjąć wartość;
   bez modyfikacji orchestratora.

## TESTS

### T1
Do testowego contract dodaj:
```text
metadata.businessDomain
```
jako required string.

ADCM ma obsłużyć bez nowego `if path == ...`.

### T2
Nowe enum field jest dopasowane case-insensitive.

### T3
Array/object parser działa dla innego path.

### T4
Nieznana skomplikowana schema konstrukcja:
- nie powoduje zgadywania;
- Forge/ADCM zwraca unsupported/clarification w kontrolowany sposób.

## NON-GOALS

Nie buduj uniwersalnego schema compiler w ADCM.

## DONE WHEN

Core ADCM nie zna biznesowych nazw najważniejszych pól, gdy ich obsługę można wyprowadzić z Forge Requirement metadata.

## STOP

Nie rozszerzaj zakresu schema poza potrzeby obecnego kontraktu i testów forward-compatibility.
