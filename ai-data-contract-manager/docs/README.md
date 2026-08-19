# Dokumentacja usługi AI Data Contract Manager

## Odpowiedzialność

- prowadzenie rozmowy i przechowywanie historii sesji;
- deterministyczna normalizacja wejścia przed LLM;
- opcjonalna ekstrakcja semantyczna przez Pydantic AI;
- kontrolowane wywołania Contract Forge przez MCP;
- API i CLI dla użytkownika.

ADCM nie posiada `contract.json`, reguł enrichmentu ani implementacji Forge.
Modele w `adcm.models` są DTO klienta dla odpowiedzi MCP, a nie współdzielonym
pakietem Pythona między usługami.

Dokumentacja przekrojowa i decyzje architektoniczne pozostają w głównym katalogu
`docs/` monorepo.
