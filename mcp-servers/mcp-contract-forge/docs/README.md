# Dokumentacja usługi MCP Contract Forge

## Odpowiedzialność

- kanoniczny stan kontraktu;
- wybór aktywnego wariantu źródła;
- systemowy i generyczny enrichment;
- stosowanie domyślnych wartości JSON Schema;
- wykrywanie brakujących wymagań;
- wykonywanie reguł biznesowych `x-contract-rules`;
- walidacja kandydatów i gotowego kontraktu;
- udostępnienie operacji przez MCP Streamable HTTP.

`config/contract.json` oraz pozostałe pliki `config/` są własnością tej usługi. ADCM
zna jedynie DTO odpowiedzi MCP.

## Źródło definicji kontraktu

Wczytanie i sparsowanie kontraktu jest za portem `ContractSourcePort`
(`contract_forge/contracts/`). Forge nie wie, czy kontrakt przyszedł z pliku, HTTP,
object storage czy bazy — adapter odpowiada za I/O, Forge za interpretację. W komplecie
są `JsonFileContractAdapter` i `InMemoryContractAdapter`.

Definicja jest kompilowana (`compile_contract()`) zanim powstanie jakakolwiek sesja.
Kontrakt z regułą, której Forge nie umie wykonać, w ogóle nie zostaje dopuszczony do
działania — patrz [CONTRACT_RULES.md](CONTRACT_RULES.md).

Dokumentacja przekrojowa znajduje się w głównym `docs/` monorepo.
