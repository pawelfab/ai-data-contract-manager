# Plan wykonania mcp-contract-forge

## Cel

`mcp-contract-forge` jest jedynym wykonawcą kontraktu. Czyta pełny JSON Schema,
ale zwraca ACDM tylko aktywny katalog dla jednego typu source i wybranych
warstw target.

Serwer nie używa LLM. Wszystkie operacje są deterministyczne.

## Publiczne narzędzia MCP

| Narzędzie | Wejście | Wynik |
|---|---|---|
| `list_contract_options` | brak | typy source, kolejność targetów, fingerprint schema |
| `get_onboarding_requirements` | `source_type`, `target_layers` | wymagane i opcjonalne pola, opisy, przykłady, pytania |
| `validate_contract` | pełny draft | wynik, błędy z opisami, fingerprint |
| `generate_contract_yaml` | poprawny draft | YAML i fingerprint |

## Etap 1 — kompletne źródło prawdy

Status: wykonany w MVP.

Plik `contracts/data-contract.schema.json`:

- używa JSON Schema Draft 2020-12;
- ma zamknięte obiekty (`additionalProperties: false`);
- definiuje source: CSV, fixed-width, JSON, TXT i JDBC;
- definiuje targety BigQuery: Bronze, Silver i Gold;
- wymusza Bronze oraz zależność Gold → Silver;
- zawiera semantyczne `description`, przykłady, wartości domyślne i enumy;
- oznacza sekcje wymagające osobnej decyzji opcjonalnej przez
  `x-acdm-optional-decision`.

Kryterium ukończenia:

- schema przechodzi `Draft202012Validator.check_schema`;
- przykłady CSV/Bronze i fixed-width/Bronze/Silver/Gold są poprawne.

## Etap 2 — aktywny katalog wymagań

Status: wykonany w MVP.

Przebieg:

1. MCP normalizuje nazwę source.
2. Waliduje ciąg targetów.
3. Rozwiązuje wyłącznie właściwy wariant `oneOf`.
4. Rekurencyjnie zbiera pola wspólne, aktywne source, aktywne targety
   i opcjonalną orkiestrację.
5. Dla tablic obiektów zwraca `item_required` i `item_properties`.
6. Generuje osobny fingerprint aktywnego katalogu.

Kryterium ukończenia:

- katalog CSV nie zawiera pól fixed-width;
- katalog fixed-width zachowuje strukturę elementu `columns`;
- pola opcjonalne nie trafiają do `required_paths`;
- ACDM może zwalidować cały payload jako model Pydantic.

## Etap 3 — strict validation

Status: wykonany w MVP.

Walidacja obejmuje:

- wszystkie reguły JSON Schema;
- formaty dat i ograniczenia wartości;
- unikalność nazw kolumn w każdej sekcji;
- poprawne i nienakładające się zakresy fixed-width;
- zgodność `recordLength` z końcem ostatniej kolumny;
- poprawność `sourcePath` względem source lub bezpośrednio poprzedniej warstwy;
- zależności warstw medallion.

Każdy błąd ma:

- `path`;
- stabilny kod;
- komunikat techniczny;
- semantyczny opis pola;
- odrzuconą wartość, jeśli jest dostępna.

Kryterium ukończenia:

- ten sam walidator jest używany przez MCP i testy;
- niepoprawny kontrakt nigdy nie trafia do generatora YAML.

## Etap 4 — deterministyczny YAML

Status: wykonany w MVP.

Zakres:

- YAML jest serializacją zwalidowanego kontraktu;
- zachowuje kolejność source → targets → orchestration;
- obsługuje polskie znaki;
- nie sortuje kluczy;
- zwraca fingerprint dokładnie tej wersji kontraktu.

Kryterium ukończenia:

- ponowne wygenerowanie z tego samego obiektu jest stabilne;
- wynik po ponownym wczytaniu odpowiada wejściowemu obiektowi.

## Etap 5 — transport i cykl życia

Status: prosty wariant stdio wykonany.

MVP uruchamia serwer przez:

```powershell
.\.venv\Scripts\mcp-contract-forge.exe
```

ADCM może uruchamiać serwer stdio dla wywołania. Jest to proste i izoluje
procesy, ale nie jest optymalne wydajnościowo.

Następny krok:

- jeden długo żyjący proces MCP;
- rekomendowany Streamable HTTP;
- health check;
- timeouty i kontrolowane ponowienia błędów transportowych;
- zamknięcie cyklu życia klienta wraz z aplikacją webową.

## Etap 6 — wersjonowanie schema

Status: planowany.

Zakres:

- jawne `schemaVersion`;
- kilka wersji schema w katalogu;
- kompatybilność wsteczna;
- migracja draftu tylko przez jawne, testowane funkcje;
- unieważnienie katalogu sesji po zmianie `schema_fingerprint`;
- opcjonalny reload bez restartu procesu.

## Etap 7 — rozszerzanie domeny

Status: planowany.

Nowy wariant source lub nowa opcja targetu powinna wymagać:

1. zmiany JSON Schema;
2. przykładowego poprawnego kontraktu;
3. testu katalogu aktywnego wariantu;
4. testu poprawnej i niepoprawnej walidacji;
5. bez zmian w promptach ACDM, jeśli semantyczne opisy schema są wystarczające.

To kryterium chroni projekt przed narastaniem warunków typu
`if source_type == "fixed_width"` po stronie ACDM.

## Źródła API

- [Pydantic AI — MCP overview](https://pydantic.dev/docs/ai/mcp/overview/)
- [Pydantic AI — MCP client](https://pydantic.dev/docs/ai/mcp/client/)
- [Pydantic AI — MCP server](https://pydantic.dev/docs/ai/mcp/server/)
