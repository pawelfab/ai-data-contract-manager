# Raport wykonania — ADCM Minimal v0.1

## Status

Rdzeń aplikacji jest rozdzielony na dwie niezależnie instalowane usługi. ADCM oraz
MCP Contract Forge mają własne manifesty, środowiska i testy. Transport MCP
Streamable HTTP został uruchomiony i zweryfikowany pełnym przepływem Rocket pomiędzy
dwoma procesami.

## Zrealizowane wymagania

- Pierwszy gate rozmowy: system źródłowy.
- Fuzzy matching systemu, np. `roket` -> `rocket`.
- Automatyczny `sourceType`, gdy system ma jeden typ; jawny kolejny wybór, gdy system ma ich wiele.
- Kolejność Forge: system enrichment -> generic enrichment -> JSON Schema defaults -> missing required discovery -> final JSON Schema validation.
- Kanoniczny kontrakt jest mutowany wyłącznie w Contract Forge.
- ADCM przekazuje wyłącznie kandydaty dla ścieżek aktualnie zwróconych przez Forge jako `pending`.
- Stair-step loop z ponownym wykorzystaniem informacji z historii rozmowy.
- Deterministyczne parsowanie kolumn oraz opcjonalny semantic resolver Pydantic AI.
- Dynamiczne odkrywanie nowych required fields bez zmian w ADCM.
- CLI terminalowe.
- FastAPI pod przyszły web UI.
- Referencyjny Contract Forge MCP i klient MCP po Streamable HTTP.
- Jawne raportowanie niekompatybilnych enrichment rules; bez runtime'owego zgadywania mapowania starych ścieżek na nowe.

## Testy

Wykonano:

```text
ai-data-contract-manager\.venv\Scripts\python.exe -m pytest ai-data-contract-manager\tests -q
mcp-servers\mcp-contract-forge\.venv\Scripts\python.exe -m pytest mcp-servers\mcp-contract-forge\tests -q
# po uruchomieniu contract-forge-mcp:
ai-data-contract-manager\.venv\Scripts\python.exe ai-data-contract-manager\scripts\smoke_demo.py
```

Wynik:

```text
ADCM: 12 passed
Contract Forge: 8 passed
MCP smoke: complete Rocket contract
```

Testy obejmują m.in. Rocket happy path, SAP enrichment, typo matching, oba formaty kolumn, stair-step loop, FastAPI, zmianę JSON Schema, wielowariantowy sourceType oraz wykrycie starych niepasujących rules.

## Świadome decyzje migracyjne

`ux_rules_new.json` i `contract.json` nie używają tego samego modelu ścieżek. Dlatego oryginalny plik został zachowany, a demo korzysta z `ux_rules_contract_v1.json`, który zawiera tylko mapowania uznane za jednoznaczne.

Nie przeniesiono automatycznej aktywacji legacy `silver.tables[]` / `gold.entries[]` do `targets.silver` / `targets.gold`, ponieważ zmieniłaby się kardynalność i semantyka. To wymaga decyzji właściciela Contract Forge/DSL, nie ADCM.

`@daily` zmieniono w demo na `0 0 * * *`, ponieważ bieżące JSON Schema wymaga dokładnie pięciopolowego crona.

Dodano generic enrichment `targets.bronze.columns` z `source.columns` oraz `orchestration.dagId` z `metadata.id`. Obie decyzje są jawne w migrated rules i można je usunąć bez zmiany ADCM.

## Następny bezpieczny krok

Przed rozbudową UI warto ustabilizować wersjonowanie pary `contract.json` + enrichment rules i dodać compatibility gate na starcie MCP. Następnie można dodać trwały session store, optional decisions i Schema Explorer MCP bez zmiany podstawowego podziału odpowiedzialności.
