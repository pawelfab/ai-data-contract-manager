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
15. `correlation_id` jest wyłącznie technicznym metadanym transportu i obserwowalności. Nie jest wejściem biznesowym Forge i nigdy nie wpływa na `ForgeAnalysis` ani `ForgeDescription` dla tego samego dokumentu.
