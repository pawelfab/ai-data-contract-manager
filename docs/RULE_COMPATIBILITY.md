# Zgodność `ux_rules_new.json` z `contract.json`

## Wniosek

Załączone pliki nie są obecnie jednym spójnym kontraktem wykonawczym. `ux_rules_new.json` reprezentuje wcześniejszy model danych, a `contract.json` nowszy.

Dlatego aplikacja zawiera dwa pliki:

- `config/ux_rules_original.json` — oryginał, bez zmian;
- `config/ux_rules_contract_v1.json` — minimalny, jawnie zmigrowany zestaw do obecnego schema.

Nie ma runtime'owego „zgadywania”, że stara ścieżka ma oznaczać nową. Takie zgadywanie w ADCM łamałoby własność kontraktu po stronie MCP.

## Najważniejsze rozjazdy

### 1. Bronze

Rules:

```text
bronzeTable.table.*
```

Schema:

```text
targets.bronze.table.*
```

W migrated rules użyto `targets.bronze`.

### 2. Silver

Rules zakłada:

```text
silver.tables[]
```

Schema ma:

```text
targets.silver
```

czyli singleton, nie listę tabel. `ensure_list_item` i `enrich_list` nie mogą zostać przemapowane 1:1.

### 3. Gold

Rules zakłada:

```text
gold.enabled
gold.entries[]
```

Schema ma:

```text
targets.gold
```

bez `enabled` i bez listy `entries`.

### 4. Converter

Rules zawiera m.in.:

```text
converter.source.*
converter.source.fixedWidth.*
converter.destPartition.*
```

Schema `ConverterConfig` zawiera tylko:

```text
converter.enabled
converter.output.format
```

Część ustawień parsera znajduje się teraz pod `source.options.*`, natomiast `destPartition` nie ma odpowiednika.

### 5. `rawData`

Rules używa:

```text
rawData.gcsBucketPath
```

Root schema nie zawiera `rawData`.

### 6. `metadata.dataFileId`

Rules kopiuje wartość z:

```text
metadata.dataFileId
```

Schema nie ma tego pola. W migrated rules nazwa tabeli Bronze jest wyprowadzana z `metadata.id`.

### 7. Harmonogram

Rules dla Rocket/SAP ustawia:

```text
@daily
```

Schema wymaga dokładnie pięciu pól cron przez regex. `@daily` jest więc niepoprawne dla obecnego kontraktu.

Do demo jawnie zmieniono to na:

```text
0 0 * * *
```

Jeśli biznesowo ma być inna godzina, ta wartość musi być ustalona w rules.

### 8. Fixed width `length`

`FixedWidthColumn` opisuje zakres półotwarty:

```text
[start, end)
```

czyli długość to:

```text
end - start
```

Natomiast `x-contract-rules` w `FixedWidthColumnConfig` mówi o:

```text
length = end - start + 1
```

Dodatkowo pole `length` w ogóle nie istnieje w `FixedWidthColumn`, a `additionalProperties=false`.

Tego rule nie da się spełnić w obecnym schema. W v0 nie jest wykonywany.

### 9. Stare, nieużywane defs

W schema istnieją `x-contract-rules` pod m.in.:

```text
RecordValidationConfig
SilverTableConfig
TransformedColumn
```

ale te definicje nie są referencjonowane przez aktywny root kontraktu.

### 10. `x-contract-rules` nie mają jednolitej semantyki maszynowej

Przykład:

```json
{
  "kind": "conditional_required",
  "path": "spec",
  "message": "spec is required when decrypt.enabled is true."
}
```

Nie ma jawnego pola `condition`. Warunek znajduje się tylko w `message`/`id` i wiedzy o kontekście definicji.

Dynamiczny Forge nie powinien parsować semantyki z tekstu komunikatu. Docelowy format powinien ponownie mieć strukturę w rodzaju:

```json
{
  "condition": {"path": "enabled", "equals": true},
  "assertion": {"path": "spec", "exists": true}
}
```

albo całość powinna być wyrażona standardowym JSON Schema (`if/then`, `dependentRequired`, `oneOf`, itp.).

## Co zostało świadomie dodane do migrated rules

### Generic Bronze columns from source

Dodano akcję:

```text
derive_target_columns
```

Dla każdego source column tworzy:

- `name`;
- `dataType`;
- `mode` z `nullable`;
- `sourcePath`.

To jest reguła wspólna, nie część ADCM. Jeśli nie jest pożądana biznesowo, usuwa się ją z rules i Forge zacznie pytać o `targets.bronze.columns`.

### `orchestration.dagId` z `metadata.id`

Dodano generic copy rule, bo jest bezpiecznym enrichmentem wspólnym i eliminuje powtórne pytanie o tę samą identyfikację.

## Rekomendacja

Przed dalszą rozbudową warto ustalić **jedną wersję contract DSL** i wersjonować razem:

```text
contract schema version
rules schema version
supported action/kind registry version
```

Forge powinien odrzucać niekompatybilny zestaw na starcie zamiast częściowo wykonywać reguły.

### 11. `metadata.sourceSystemGcpId` jest opcjonalne w JSON Schema, ale obowiązkowe w workflow ADCM

W `Metadata.required` są tylko `id`, `version`, `owner`, natomiast wybór systemu źródłowego jest potrzebny przed enrichmentem. V0 traktuje więc `metadata.sourceSystemGcpId` jako **jawny workflow gate Contract Forge**, mimo że samo JSON Schema go nie wymaga.

To jest celowy wyjątek zgodny z wymaganiem UX „najpierw system źródłowy”, ale docelowo warto formalnie opisać go w kontrakcie/rules, np. przez osobną metadeklarację workflow albo dodanie pola do `required`, jeżeli zawsze jest obowiązkowe biznesowo.
