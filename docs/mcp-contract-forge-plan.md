# Status i roadmapa mcp-contract-forge

Aktualny protokół, odpowiedzialności i przykłady znajdują się w
`mcp-contract-forge.md`.

## Wykonane

- kanoniczny JSON Schema Draft 2020-12;
- źródła CSV, fixed-width, JSON, TXT i JDBC;
- targety BigQuery Bronze, Silver i Gold;
- aktywny katalog wymagań zależny od source i warstw;
- wymagane `metadata.id`, `metadata.version`, `metadata.owner`,
  `orchestration.dagId` i pięciopolowy Linux cron;
- strict validation JSON Schema i reguły semantyczne;
- filtrowanie błędów `oneOf` do aktywnego wariantu discriminatora;
- opisy błędów dla właściwości elementów tablic;
- deterministyczne generowanie YAML;
- serwer uruchamiany przez:

```powershell
.\.venv\Scripts\python.exe -m mcp_contract_forge.server
```

- jeden długowieczny proces stdio i sesja MCP po stronie ACDM.

## Następne etapy

- jawne wersjonowanie schematu kontraktu;
- migracje draftów pomiędzy wersjami;
- testy wszystkich poprawnych przykładów JSON, TXT i JDBC;
- opcjonalny reload schematu;
- transport Streamable HTTP i health check MCP;
- stabilna polityka kompatybilności protokołu.

Dodanie nowego wariantu source powinno wymagać zmiany JSON Schema, poprawnego
przykładu oraz testów katalogu i walidacji. Nie powinno wymagać warunków
`if source_type == ...` w ACDM.
