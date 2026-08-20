# Dokumentacja usługi MCP Contract Forge

## Odpowiedzialność

- kanoniczny stan kontraktu;
- wybór aktywnego wariantu źródła;
- systemowy i generyczny enrichment;
- stosowanie domyślnych wartości JSON Schema;
- wykrywanie brakujących wymagań;
- wykonywanie reguł biznesowych `x-contract-rules`;
- wystawianie listy pól edytowalnych (`get_editable_fields`);
- przeliczanie wartości pochodnych po zmianie ich źródła;
- walidacja kandydatów i gotowego kontraktu;
- udostępnienie operacji przez MCP Streamable HTTP.

## Edycja gotowego kontraktu

`complete` opisuje kontrakt, nie sesję. Forge rozróżnia trzy powierzchnie:

| Pojęcie | Znaczenie |
|---|---|
| `pending` | czego brakuje |
| `overridable` | wartości pochodne warte konfrontacji z faktami użytkownika |
| `editable` | co użytkownik może świadomie zmienić, niezależnie od origin |

`editable` jest wystawiane osobnym narzędziem `get_editable_fields(session_id)`, żeby
zwykła pętla nie nosiła całego katalogu. Tablica jest jedną atomową jednostką edycji —
`source.columns`, nigdy `source.columns.0.name`.

Zapis użytkownika może trafić w dowolną ścieżkę rozwiązywalną w aktywnym schemacie, także
w sekcję, której jeszcze nie ma. Zmiana wejścia unieważnia wartości z niego wyliczone
(zależności biorą się z `source_path` w regułach enrichmentu), a zmiana
`metadata.sourceSystemGcpId` uruchamia pełne przeliczenie. Wartości podane przez
użytkownika są zachowywane; to, co faktycznie przepadło, trafia do `ForgeState.discarded`.

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
