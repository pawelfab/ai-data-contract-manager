# Core invariants

1. ADCM rozumie użytkownika; Contract Forge rozumie kontrakt.
2. ADCM i każdy MCP są osobnymi usługami i mają osobne zależności/venv/obrazy Docker.
3. Brak bezpośrednich importów Pythona pomiędzy usługami.
4. ADCM nie ma klas odpowiadających konkretnej strukturze `contract.json`; dokument jest generycznym JSON-em.
5. `contract.json` jest własnością zewnętrzną. ADCM go nie parsuje i go nie modyfikuje.
6. Forge jest bezstanowy, nie zna rozmowy i nie wywołuje LLM.
7. LLM nigdy nie mutuje `ContractState` bezpośrednio. Generuje tylko kandydatów.
8. Jedynym modułem zmieniającym dokument jest `DocumentEngine` przez generyczne mutacje JSON Pointer.
9. Automatyczne źródła (`APP_RULE`, Forge enrichment/default) tworzą propozycje; `ProposalReconciler` rozstrzyga autorytet.
10. Jawna wartość użytkownika ma wyższy autorytet niż automatyczne propozycje.
11. Forge jest obowiązkowym, deterministycznym krokiem stabilizacji.
12. `ExternalCheckCoordinator` jest rozszerzeniem ADCM. Opcjonalne Context MCP mogą być wyłączone bez zatrzymania podstawowego workflow.
13. Wynik Forge i wynik external checks są osobnymi rodzajami prawdy.
14. Core nie może zawierać warunków na konkretne ścieżki typu `/silver/...`, nazwy systemów ani typy źródeł.
15. `correlation_id` jest wyłącznie technicznym metadanym transportu i obserwowalności. Nie jest wejściem biznesowym Forge i nigdy nie wpływa na `ForgeAnalysis` ani `ForgeDescription` dla tego samego dokumentu. Nie jest też identyfikatorem sesji.
16. HTTP jest szczegółem adaptera. `domain`, `application` i `ports` nie importują `fastapi`, `starlette` ani `HTTPException`.
17. API nie zawiera logiki domenowej. Nie modyfikuje `ContractState`, nie interpretuje wiadomości użytkownika, nie wykonuje reguł, nie wywołuje Forge poza orchestratorem, nie zna struktury kontraktu, nie rozstrzyga autorytetu i nie implementuje fixed-point.
18. Modele domenowe nie są publicznym kontraktem API. Kontrakt publiczny jest zdefiniowany jawnie w `adapters/api/models.py`, a zakres ujawnianych danych rozstrzyga `adapters/api/mappers.py`.
19. Cykl życia sesji należy do warstwy application. API nie przechowuje sesji we własnym stanie i nie ustala formatu identyfikatora sesji.
20. Odpowiedź błędu nie ujawnia internals. Stack trace, adres Forge, szczegóły MCP i dane dostawców pozostają w application logu i nigdy nie trafiają do odpowiedzi HTTP.
