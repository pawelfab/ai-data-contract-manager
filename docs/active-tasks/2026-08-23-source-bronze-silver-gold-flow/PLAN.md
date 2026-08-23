# Source → Bronze → Silver/Gold

## Cel

Zapewnić deterministyczny przepływ konfiguracji warstw:

```text
wymagane pola Source
    ↓
automatyczne Bronze
    ↓
automatyczna aktywacja Silver i Gold
    ↓
pytania o pozostałe wymagania Silver
```

## Oczekiwane zachowanie

- Wszystkie formalnie wymagane pola wybranej gałęzi `/source` muszą zostać uzupełnione przed aktywacją Bronze.
- Bronze jest aktywowane i wypełniane globalnymi regułami, niezależnie od systemu i technicznego typu źródła.
- Dla `sourceSystemGcpId = sap` Bronze otrzymuje:
  - `project = sap_bronze`;
  - `dataset = sap_bronze`;
  - `table = sap_bronze`;
  - `columns = []`, oznaczające brak jawnych nadpisań kolumn w przepływie 1:1.
- Dopiero kompletne Bronze aktywuje Silver i Gold.
- Silver otrzymuje automatycznie:
  - `project`, `dataset`, `table` = `{sourceSystemGcpId}_silver`;
  - `source = {sourceSystemGcpId}_bronze`.
- `/silver/tables/0/pk` i całe `/silver/tables/0/columns` pozostają wymaganiami użytkownika.
- Gold otrzymuje automatycznie `project`, `dataset`, `table` = `{sourceSystemGcpId}_gold`.
- Szablony używają wartości `/metadata/sourceSystemGcpId` bez dodatkowej normalizacji.
- Zmiana systemu źródłowego przelicza wszystkie wartości pochodne i usuwa stare nazwy.

## Źródło obecnego zachowania

- Aktywacja `/silver/enabled=true` i `/gold/enabled=true` pochodzi obecnie z `ux_rules.json`.
- Wymagania pól wewnątrz Silver i Gold pochodzą z `contract.json` oraz mechanizmu `x-requirement-expand-items`.
- LLM jedynie prezentuje wymagania i proponuje evidence-backed `Candidate`; nie decyduje, które warstwy są obowiązkowe.
- Reguła `sap.silver_dataset`, ustawiająca `silver_sap`, musi zostać zastąpiona globalną konwencją `{system}_silver`.

## Ownership i granice

```text
Owning service: MCP Contract Forge
Owning boundary: EnrichmentRule / EnrichmentResolver / EvaluateContract / ux_rules.json
Main invariant: ADCM understands the user. Contract Forge understands the contract.
```

Nie zmieniać:

- `mcp-servers/mcp-contract-forge/resources/contract.json`;
- `mcp-servers/mcp-contract-forge/resources/discovery_rules.json`;
- ADCM i jego stabilizacji;
- Pydantic AI;
- Forge API;
- obsługi union/discriminator.

Nie dodawać nazw systemów ani typów źródeł do kodu Python. Reguły mają być globalne i działać dla `jdbc`, `json`, `txt` oraz `fixed_width`.

## Kryteria akceptacji

1. Niekompletne Source nie generuje sugestii Bronze, Silver ani Gold.
2. Kompletne Source uruchamia automatyczne Bronze.
3. Bronze zawiera trzy nazwy `{system}_bronze` i `columns=[]`.
4. Kompletne Bronze aktywuje Silver i Gold.
5. Nazwy Silver i Gold są globalnie wyliczane według nowych konwencji.
6. Silver nadal wymaga `pk` oraz atomowej tablicy `columns`.
7. Zachowanie działa dla wszystkich czterech typów źródła.
8. `contract.json` pozostaje bez zmian.

## Poza zakresem

- błędne wywnioskowanie `dataFileId=sap` z komunikatu „system SAP”;
- ostrzeżenia nieuwzględniające najnowszej korekty;
- możliwe problemy kodowania polskich znaków;
- polityka `NEEDS_USER_DECISION`.

`csv` nie jest dozwolonym `sourceType` według kontraktu i jego odrzucenie nie jest błędem.
