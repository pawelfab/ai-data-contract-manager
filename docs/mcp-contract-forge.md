# mcp-contract-forge

## Odpowiedzialność

Serwer jest deterministycznym autorytetem struktury i poprawności kontraktu.
Nie używa LLM. Kanonicznym źródłem jest:

```text
contracts/data-contract.schema.json
```

Plik `examples/legacy-contract.partial.json` jest historycznym, uciętym
przykładem i nie jest ładowany.

## Narzędzia MCP

### `list_contract_options`

Wejście: brak.

Wynik zawiera:

- `schemaFingerprint`;
- `sourceTypes`;
- `targetLayers`;
- opis reguł kolejności targetów.

### `get_onboarding_requirements`

Przykładowe wejście:

```json
{
  "source_type": "csv",
  "target_layers": ["bronze"]
}
```

Wynik jest walidowany jako `RequirementsCatalogue` i zawiera:

- fingerprint schematu i aktywnego katalogu;
- znormalizowany source i targety;
- `required_paths`, `optional_paths` i `allowed_paths`;
- pytania dla pól wymaganych;
- decyzje o sekcjach opcjonalnych;
- `field_catalog` z opisami, przykładami i strukturą elementów tablic.

Alias `fixed-with` jest normalizowany do `fixed_width`.

### `validate_contract`

Wejście:

```json
{
  "contract": {
    "...": "pełny draft"
  }
}
```

Wynik zawiera `valid`, fingerprinty, `normalized_contract` i listę `issues`.
Każdy problem ma:

- `path`;
- `code`;
- komunikat techniczny;
- semantyczny `description`;
- odrzuconą wartość, jeśli jest dostępna.

Dla `oneOf` lub `anyOf` z discriminatorem raportowane są błędy tylko aktywnego
wariantu. Dla ścieżek takich jak `source.columns.0.name` opis pochodzi z
`item_properties.name`, a nie z ogólnego komunikatu.

Poza JSON Schema wykonywane są reguły:

- unikalność nazw kolumn;
- poprawność i brak nakładania zakresów fixed-width;
- zgodność `recordLength`;
- poprawność `sourcePath`;
- kolejność warstw medallion.

Format `orchestration.schedule` jest pięciopolowym Linux cronem i jest
walidowany przez JSON Schema.

### `generate_contract_yaml`

Przyjmuje pełny kontrakt. Najpierw wykonuje tę samą walidację. Dla
niepoprawnego obiektu zgłasza błąd; dla poprawnego zwraca YAML oraz fingerprint.
Klucze nie są sortowane.

## Uruchomienie samodzielne

```powershell
.\.venv\Scripts\python.exe -m mcp_contract_forge.server
```

W normalnym trybie nie trzeba uruchamiać serwera ręcznie. ACDM przy
`ACDM_CONTRACT_TRANSPORT=stdio` zarządza procesem i sesją MCP w lifecycle
aplikacji webowej.
