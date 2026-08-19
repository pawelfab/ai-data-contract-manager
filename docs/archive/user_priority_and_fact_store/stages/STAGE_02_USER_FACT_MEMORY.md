# STAGE 02 — prosta pamięć faktów użytkownika

## GOAL

ADCM ma pamiętać informacje podane wcześniej przez usera i **to ADCM ma rozstrzygać, która informacja USER dla danego path jest najnowsza**.

Nie budujemy rozbudowanego memory framework.

Ten stage jest właścicielem reguły:

```text
USER message nowsza > USER message starsza
```

Stage 01 / Forge nie analizuje historii rozmowy.

## RESPONSIBILITY

To jest **conversation state ADCM**, nie canonical contract state.

Forge nadal przechowuje contract.

## SIMPLE DATA MODEL

Dodaj do sesji ADCM prosty model, np.:

```python
class ExtractionMethod(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"

class UserFact(BaseModel):
    path: str
    value: Any
    message_sequence: int
    extraction_method: ExtractionMethod
    confidence: float = 1.0
    evidence: str | None = None
```

W `ConversationMemory`:

```python
messages: list[ChatMessage]
facts: dict[str, UserFact]
next_message_sequence: int
```

Można użyć innej prostej struktury, jeśli obecny kod lepiej do niej pasuje.

## IMPORTANT SEMANTICS

`facts[path]` ma reprezentować **najnowszy zaakceptowany fakt USER dla path**.

To jest jedyne miejsce, w którym rozstrzygamy recency kilku wypowiedzi usera.

Forge otrzymuje już wybrany przez ADCM aktualny USER candidate.

Nie potrzebujemy teraz pełnej historii faktów, ponieważ raw transcript już przechowuje wiadomości.

Jeżeli:
- message 1: owner=team_a
- message 5: owner=team_b

to:
```python
facts["metadata.owner"].value == "team_b"
```

## FACT CREATION

Fact powstaje dopiero, gdy ADCM potrafi powiązać wypowiedź z path wystawionym przez Forge.

Nie próbuj przy starcie samodzielnie mapować całej wiadomości na cały `contract.json`.

To zachowuje zasadę:
- Forge ujawnia aktualne pola;
- ADCM sprawdza, czy user już o nich mówił.

## TODO

1. Dodaj monotoniczny `message_sequence` dla wiadomości usera.
2. Dodaj `UserFact`.
3. Dodaj proste metody:
   - `remember_fact(...)`
   - `get_fact(path)`
   - opcjonalnie `forget/replace` tylko jeśli realnie potrzebne.
4. `remember_fact` ma zastępować fact dla path tylko wtedy, gdy incoming `message_sequence` jest nowsze lub równe.
   To jest główna reguła latest-user-wins; nie duplikuj jej w Forge.
5. Deterministyczny resolver po znalezieniu wartości powinien zapisać fact.
6. Semantic resolver będzie podłączony w późniejszym stage; teraz tylko przygotuj model.
7. Nie zapisuj partial/invalid contract values do Forge jako canonical contract.
8. Raw messages nadal zostają zachowane.

## NON-GOALS

Nie:
- parsuj wszystkich pól z wiadomości na starcie;
- skanuj `contract.json` w ADCM;
- twórz event sourcing;
- dodawaj Redis/DB;
- implementuj LLM;
- implementuj partial columns.

## TESTS

### T1
Dwie informacje dla tego samego path:
- wcześniejsza `team_a`
- późniejsza `team_b`

`get_fact(path)` zwraca `team_b`.

### T2
Starszy fakt nie nadpisuje nowszego.

### T3
Fact zawiera:
- path;
- value;
- sequence;
- extraction method.

### T4
Transcript nadal zawiera wszystkie wiadomości.

## DONE WHEN

ADCM posiada minimalny, deterministyczny latest-user-fact store i potrafi jednoznacznie wskazać najnowszy USER fact dla path.

Forge nie musi znać historii wiadomości, aby otrzymać aktualną intencję usera.

## STOP

Nie implementuj automatycznego wykorzystania wszystkich facts w stair-step loop; to Stage 03.
