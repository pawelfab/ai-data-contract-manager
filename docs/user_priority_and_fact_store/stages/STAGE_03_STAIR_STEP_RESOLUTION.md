# STAGE 03 — automatyczny stair-step resolution z historią i override

## GOAL

Doprowadzić główny loop ADCM do docelowego zachowania:

Forge odkrywa requirement -> ADCM próbuje rozwiązać go bez usera -> submit -> Forge odkrywa kolejny -> repeat.

User jest pytany dopiero, gdy ADCM nie ma wystarczającej informacji.

Dodatkowo ADCM ma wykrywać USER override dla wartości wypełnionych enrichment/defaultem.

## REQUIRED INPUT FROM FORGE

Forge state powinien wystawiać dwa logiczne zbiory:

### 1. `pending`
Brakujące requirementy.

### 2. `overridable`
Pola już posiadające wartość z:
- SYSTEM_ENRICHMENT;
- GENERIC_ENRICHMENT;
- SCHEMA_DEFAULT;

które user może nadpisać.

Nie muszą to być dwa osobne endpointy. Ważna jest semantyka.

Przykładowy model:

```python
class ResolvableField(BaseModel):
    path: str
    value_schema: dict[str, Any]
    question: str | None = None
    current_value: Any | None = None
    current_origin: ValueOrigin | None = None
    status: Literal["pending", "overridable"]
```

Użyj obecnych modeli, jeśli można je lekko rozszerzyć.

## BOUNDARY

Forge decyduje:
- jakie path są legalne;
- które są pending;
- które mogą zostać nadpisane;
- czy candidate jest poprawny.

ADCM tylko próbuje dopasować user history/facts do tych pól.

## LOOP ORDER

Dla każdego auto-step:

1. pobierz aktualny Forge state;
2. zbierz `pending`;
3. zbierz `overridable`;
4. najpierw sprawdź `UserFact store`;
5. potem deterministycznie przeskanuj wiadomości od najnowszej do najstarszej;
6. jeśli znajdziesz kilka USER values dla tego samego path:
   - ADCM wybiera najnowszą na podstawie `message_sequence`;
   - zapisuje ją jako aktualny `UserFact`;
   - do Forge wysyła tylko aktualny USER candidate;
7. jeśli znaleziono candidate:
   - zapisz/update UserFact;
   - submit do Forge;
   - `continue`;
8. jeśli nie znaleziono deterministycznie:
   - w tym stage **nie używaj jeszcze LLM**;
9. jeśli nie ma kandydata:
   - przerwij auto-loop;
   - pokaż userowi pierwsze `pending`;
10. jeśli nie ma pending i Forge complete:
   - zakończ;
11. zachowaj `max_auto_steps` i ochronę przed loopem.

## IMPORTANT — OVERRIDE

Jeżeli Forge ma:

```text
orchestration.schedule
current_origin=SYSTEM_ENRICHMENT
```

a najnowsza wiadomość usera jednoznacznie zawiera schedule, ADCM może wysłać USER candidate nawet jeśli pole nie jest `pending`.

Forge z Stage 01 rozstrzygnie precedence **originów**.

ADCM rozstrzyga tylko, który USER fact jest najnowszy. Forge nie porównuje message sequence.

## IMPORTANT — NO HARD-CODED PATH WHITELIST

Nie buduj listy:
```python
["metadata.owner", "metadata.id", "orchestration.schedule", ...]
```

Legalne ścieżki pochodzą z Forge state.

Heurystyka może nadal mieć obecne specjalizowane parsery jako fallback, ale orchestrator nie może ograniczać się do stałej listy pathów.

## ANTI-LOOP

Przerwij auto-loop, jeśli:
- Forge state nie zmienił się po submit;
- ten sam candidate został odrzucony drugi raz;
- osiągnięto `max_auto_steps`.

Zwróć użytkownikowi zrozumiałą informację, zamiast powtarzać identyczne pytanie bez komentarza.

## TESTS

### T1 — pełna informacja wcześniej
User w jednej wiadomości podaje:
- source system;
- pipeline id;
- owner;
- uri.

Forge odkrywa je po kolei.

ADCM rozwiązuje wszystkie bez kolejnych pytań aż do pierwszego naprawdę brakującego pola.

### T2 — latest wins
User wcześniej podał owner A, później owner B.

Gdy Forge odkryje `metadata.owner`, ADCM wysyła B.

### T3 — override enrichment
Forge ma schedule z system enrichment.

User podał własny schedule w rozmowie.

ADCM wysyła USER override mimo braku `pending` dla schedule.

### T4
Brak informacji -> user dostaje jedno precyzyjne pytanie.

### T5
Rejected candidate nie powoduje nieskończonego loopu.

## NON-GOALS

Nie implementuj:
- LLM fallback;
- generic parsera array/object;
- nowych JSON Schema konstrukcji;
- web UI;
- persistent sessions.

## DONE WHEN

Deterministyczny stair-step loop wykorzystuje wcześniejsze fakty i user override bez angażowania usera w każde kolejne requirement.

## STOP

LLM pozostaje wyłączony w tym stage.
