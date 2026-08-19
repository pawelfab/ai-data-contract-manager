# STAGE 05 — LLM jako kontrolowany semantic fallback

## GOAL

Włączyć LLM tak, aby wykorzystywał całą potrzebną historię rozmowy i potrafił dopasować wcześniejsze wypowiedzi usera do aktualnych pól wystawionych przez Forge.

LLM ma być fallbackiem, nie orchestrator-em.

## REQUIRED ORDER

Dla każdego pola:

1. UserFact store;
2. deterministic resolver;
3. partial fact merge;
4. LLM;
5. jeśli nadal brak -> pytanie usera.

## INPUT TO LLM

LLM powinien otrzymać:

- aktualne `pending`;
- aktualne `overridable`;
- schema fragment tych pól;
- ich pytanie/description/examples/enum, jeśli dostępne;
- current value + origin dla overridable;
- transcript użytkownika potrzebny do ekstrakcji;
- istniejące UserFacts;
- jasne ograniczenie, że może zwrócić tylko path z dostarczonej listy.

Nie przekazuj LLM całego `contract.json`, jeśli nie jest to konieczne.

## OUTPUT MODEL

Użyj Pydantic structured output, np.:

```python
class ExtractedCandidate(BaseModel):
    path: str
    value: Any
    confidence: float
    evidence: str | None = None
```

Następnie ADCM zamienia to na USER fact/candidate:

```text
origin = USER
extraction_method = LLM
message_sequence = sequence wiadomości, z której pochodzi evidence
```

`message_sequence` służy ADCM do latest-user-wins.

Forge może zachować go jako metadata audytowe, ale **nie używa go do precedence originów**.

Jeśli nie da się pewnie określić sequence, resolver nie powinien arbitralnie zastępować nowszego istniejącego UserFact. Preferuj:
- zachowanie istniejącego nowszego UserFact;
- albo clarification do usera przy niejednoznaczności.

## IMPORTANT

Nie twórz osobnego biznesowego precedence:
```text
LLM > enrichment
```

LLM jedynie wydobywa fakt usera.

Precedence jest:
```text
USER > enrichment...
```

## STRICT BOUNDARY

LLM:
- nie może zwrócić path spoza listy Forge;
- nie może sam tworzyć nowej sekcji kontraktu;
- nie może uznać kontraktu za valid;
- nie może uruchamiać dowolnych MCP calls;
- nie może interpretować nieznanych `x-contract-rules` jako kodu;
- nie może wymyślać wartości, których user nie podał.

## HISTORY

Nie polegaj docelowo wyłącznie na `messages[-20:]`.

W minimalnej wersji:
- UserFacts są pamięcią strukturalną;
- raw transcript można przekazać w rozsądnym oknie;
- jeśli fakt został już wyekstrahowany do UserFact, nie musi zależeć od tego, czy stara wiadomość nadal mieści się w prompt window.

Nie buduj teraz summarization service ani vector DB.

## CONFIGURATION

Zachowaj prosty provider abstraction.

Nie wiąż orchestratora z OpenAI/Vertex.

Dopuszczalne:

```text
SemanticResolver protocol
  -> NoopSemanticResolver
  -> PydanticAISemanticResolver
```

Provider/model jest konfiguracją implementacji resolvera.

Jeśli obecne `ADCM_LLM_MODE=pydantic` działa, nie musisz w tym stage robić osobnego refactoru settings, chyba że jest niezbędny do testów.

## TODO

1. Rozszerz semantic resolver input o pending + overridable.
2. Ogranicz allowable output paths.
3. Zwracaj structured candidates.
4. Po akceptacji kandydata zapisz UserFact z `extraction_method=LLM`.
5. LLM uruchamiaj dopiero po deterministic failure.
6. Jeśli confidence jest poniżej prostego progu:
   - nie submituj;
   - zapytaj usera.
7. Ustaw próg w jednym miejscu konfiguracji, bez rozbudowanego scoring engine.
8. Dodaj debug logging:
   - czy deterministic czy LLM rozwiązał pole;
   - path;
   - confidence;
   bez logowania sekretów i całych wrażliwych payloadów.

## TESTS

Testy SemanticResolver mogą używać fake/stub LLM.

### T1
Deterministic resolver znajduje wartość -> LLM nie jest wołany.

### T2
Deterministic nie znajduje, LLM znajduje wcześniejszą wartość -> submit.

### T3
LLM próbuje zwrócić nielegalny path -> ADCM odrzuca.

### T4
LLM wydobywa USER fact, ADCM zapisuje go z właściwym `message_sequence`, a Forge pozwala mu nadpisać enrichment dzięki `origin=USER`.

Recency pomiędzy dwoma USER facts pozostaje odpowiedzialnością ADCM.

### T5
Niska confidence -> pytanie do usera, brak submitu.

### T6
UserFacts pozwalają zachować wcześniej wydobyte informacje bez polegania na pełnym transcript.

## NON-GOALS

Nie:
- daj LLM autonomii agentowej;
- nie twórz tool-calling loop sterowanego przez LLM;
- nie dodawaj RAG/vector store;
- nie implementuj nowych providerów „na zapas”.

## DONE WHEN

LLM pełni wyłącznie rolę semantic fallback i potrafi wykorzystać wcześniejsze wypowiedzi do aktualnie ujawnionych pól bez przejmowania sterowania.
