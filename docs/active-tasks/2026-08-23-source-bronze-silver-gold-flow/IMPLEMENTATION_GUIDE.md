# Implementation Guide: Source → Bronze → Silver/Gold

## 1. Problem

Po ustawieniu `/source/sourceType` aktualne globalne enrichmenty natychmiast aktywują Silver i Gold. Bronze nie jest aktywowane, dlatego wypowiedź użytkownika dotycząca Bronze może zostać semantycznie dopasowana do aktualnie widocznych ścieżek Silver.

`contract.json` jest zewnętrznym źródłem i nie wolno go zmieniać. Rozwiązanie należy do deterministycznego enrichmentu Contract Forge.

## 2. Docelowy dokument

Dla `sourceSystemGcpId = sap` stan pochodny powinien zmierzać do:

```yaml
bronzeTable:
  table:
    project: sap_bronze
    dataset: sap_bronze
    table: sap_bronze
  columns: []

silver:
  enabled: true
  tables:
    - table:
        project: sap_silver
        dataset: sap_silver
        table: sap_silver
      source: sap_bronze
      # pk i columns dostarcza użytkownik

gold:
  enabled: true
  entries:
    - table:
        project: sap_gold
        dataset: sap_gold
        table: sap_gold
```

## 3. Nowy warunek enrichment

Rozszerzyć `EnrichmentCondition` o alias JSON `requirementsComplete`:

```python
class EnrichmentCondition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    path: str
    equals: Any | None = None
    exists: bool | None = None
    requirements_complete: bool | None = Field(
        default=None,
        alias="requirementsComplete",
    )
```

Przykład reguły:

```json
{
  "path": "/source",
  "requirementsComplete": true
}
```

Semantyka: warunek jest prawdziwy, jeżeli nie istnieje aktualne formalne `Requirement`, którego ścieżka jest równa prefiksowi lub leży pod nim.

Pseudokod:

```python
def requirement_is_under(prefix: str, path: str) -> bool:
    normalized = prefix.rstrip("/")
    return path == normalized or path.startswith(normalized + "/")


def requirements_complete(prefix: str, open_paths: set[str]) -> bool:
    return not any(requirement_is_under(prefix, path) for path in open_paths)
```

`resolve_enrichment` powinien otrzymać `open_requirement_paths`. `EvaluateContract` buduje je z pełnych `formal_requirements`, przed filtrowaniem discovery:

```python
open_requirement_paths = {requirement.path for requirement in formal_requirements}
```

Nie opierać kompletności na wymaganiach widocznych ani na kolejności pytań.

## 4. Reguły Bronze

Podnieść wersję `ux_rules.json` i dodać przejściowy scaffold:

```json
{
  "id": "global.activate_bronze",
  "scope": "global",
  "path": "/bronzeTable",
  "value": {},
  "when": [
    {"path": "/source/sourceType", "exists": true},
    {"path": "/source", "requirementsComplete": true},
    {"path": "/bronzeTable", "exists": false}
  ],
  "priority": 50
}
```

`exists=false` jest obowiązkowe. Scaffold ma aktywować opcjonalną gałąź tylko raz i nie może później zastępować jej dzieci pustym obiektem.

Po aktywacji dodać trwałe reguły:

```text
/bronzeTable/table/project = "{/metadata/sourceSystemGcpId}_bronze"
/bronzeTable/table/dataset = "{/metadata/sourceSystemGcpId}_bronze"
/bronzeTable/table/table   = "{/metadata/sourceSystemGcpId}_bronze"
/bronzeTable/columns       = []
```

Każda reguła wymaga istniejącego `sourceType` oraz kompletnego `/source`.

`columns=[]` jest świadomie całym atomowym array. Nie tworzyć `/bronzeTable/columns/0` ani definicji kolumn.

## 5. Reguły Silver i Gold

Aktywację obu warstw uzależnić od:

```json
[
  {"path": "/source", "requirementsComplete": true},
  {"path": "/bronzeTable", "exists": true},
  {"path": "/bronzeTable", "requirementsComplete": true}
]
```

Silver:

```text
/silver/tables/0/table/project = "{/metadata/sourceSystemGcpId}_silver"
/silver/tables/0/table/dataset = "{/metadata/sourceSystemGcpId}_silver"
/silver/tables/0/table/table   = "{/metadata/sourceSystemGcpId}_silver"
/silver/tables/0/source        = "{/metadata/sourceSystemGcpId}_bronze"
```

Reguły pól wymagają również `/silver/enabled=true`. Nie dodawać enrichmentu dla:

```text
/silver/tables/0/pk
/silver/tables/0/columns
```

Gold:

```text
/gold/entries/0/table/project = "{/metadata/sourceSystemGcpId}_gold"
/gold/entries/0/table/dataset = "{/metadata/sourceSystemGcpId}_gold"
/gold/entries/0/table/table   = "{/metadata/sourceSystemGcpId}_gold"
```

Reguły wymagają `/gold/enabled=true`, kompletnego Source oraz Bronze.

Usunąć `sap.silver_dataset`. Pozostawić bez zmian SAP-owe reguły Converter i Preparator.

## 6. Oczekiwany fixed-point

```text
1. Source niekompletne
   → brak Bronze/Silver/Gold suggestions

2. Source kompletne
   → /bronzeTable = {}

3. Kolejna ewaluacja
   → Forge odkrywa wymagania Bronze
   → enrichment dostarcza table.* i columns=[]

4. Bronze kompletne
   → Silver/Gold enabled=true

5. Warstwy aktywne
   → enrichment dostarcza identyfikatory tabel i Silver source

6. Stały punkt
   → użytkownik jest pytany m.in. o Silver pk i columns
```

Postęp stabilizacji nadal musi zależeć wyłącznie od rzeczywistej zmiany stanu.

## 7. Oczekiwany change surface

Kod i konfiguracja:

- `mcp-servers/mcp-contract-forge/resources/ux_rules.json`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/enrichment/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/enrichment_resolver.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/use_cases/evaluate_contract.py`

Testy:

- `mcp-servers/mcp-contract-forge/tests/unit/test_enrichment_repository.py`
- `mcp-servers/mcp-contract-forge/tests/unit/test_evaluate_contract.py`

Dokumentacja po implementacji:

- `docs/CURRENT_STATE.md`
- `docs/DECISIONS.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- generowane artefakty freshness.

## 8. Testy

Test `requirementsComplete` powinien pokryć:

```text
/source/encoding otwarte     → complete(/source) == false
brak wymagań pod /source     → complete(/source) == true
otwarte /silver/...          → complete(/source) == true
```

Dodać parametryzowane scenariusze dla `jdbc`, `json`, `txt`, `fixed_width`:

1. Niekompletne Source nie aktywuje warstw.
2. Kompletne Source aktywuje i wypełnia Bronze.
3. Kompletne Bronze aktywuje Silver/Gold.
4. Identyfikatory warstw używają właściwego suffixu.
5. Silver source wskazuje Bronze.
6. Silver `pk` i `columns` pozostają wymaganiami.
7. Zmiana systemu przelicza wszystkie derived values.
8. Scaffold `{}` nie zastępuje dzieci Bronze.
9. Użytkownik może nadpisać enrichment silniejszą wartością.

## 9. Boundary checklist

- ADCM pozostaje nieświadomy formatu kontraktu.
- Forge nie otrzymuje conversation/session state.
- Brak nowych importów między usługami.
- Formalna walidacja pozostaje niezależna od discovery.
- `contract.json` i `discovery_rules.json` pozostają bez zmian.
- Bronze columns jest świadomie atomowym array.
- Union/discriminator pozostaje generyczny.
- Zmiana source system recomputuje stare nazwy.
- Identyczna zaakceptowana sugestia nie raportuje postępu.

## 10. Weryfikacja po przyszłej implementacji

```powershell
cd mcp-servers/mcp-contract-forge
$env:PYTHONPATH='src'
..\..\ai-data-contract-manager\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Następnie uruchomić pełne testy ADCM oraz:

```powershell
python scripts/agent/documentation_update.py
python scripts/agent/doc_freshness.py --check
```

## 11. Odłożone problemy

Nie naprawiać w tym zadaniu:

- `dataFileId=sap` wywnioskowane z „system SAP”;
- ostrzeżenia nieuwzględniające najnowszej korekty;
- możliwe podwójne kodowanie polskich znaków;
- polityka konfliktów `NEEDS_USER_DECISION`.

Odrzucenie `csv` jako `sourceType` jest zgodne z kontraktem.
