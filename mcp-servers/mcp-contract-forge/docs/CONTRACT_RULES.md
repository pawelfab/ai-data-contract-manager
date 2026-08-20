# `x-contract-rules` — zasady implementacji

Contract Forge wykonuje wyłącznie te reguły `x-contract-rules`, których logika jest
jednoznacznie i strukturalnie zapisana w `condition` oraz `assertion`.

## Zasada nadrzędna

> Logika biznesowa wykonywana przez Forge musi być odczytywalna wyłącznie z danych
> strukturalnych kontraktu, bez interpretacji tekstu naturalnego.

Konsekwencje:

- Nie interpretujemy logiki z `message`, `notes` ani `source.pydantic_validator`.
- `message` służy wyłącznie jako tekst diagnostyczny dla użytkownika.
- Nieznany operator nie może zostać odgadnięty na podstawie `message`.
- Nie implementujemy `VALIDATION_REGISTRY`, `RegistryPort` ani mapowania `rule.id → registry`.

## Dwa rozłączne światy błędów

Forge rozdziela błąd **definicji kontraktu** od błędu **sesji użytkownika**:

```text
USER CONTRACT ──┬─ missing   → waiting_for_user
                ├─ invalid   → user correction
                └─ valid     → complete

CONTRACT DEFINITION ── nieznany kind/operator → configuration error (serwer nie startuje)
```

Nieznany `kind` albo nieznany operator to `ContractDefinitionError` rzucany przy ładowaniu
kontraktu, a nie `invalid` w trakcie rozmowy. Reguły są walidowane nawet wtedy, gdy ich
`condition` nie jest jeszcze aktywne — użytkownik nie może przejść piętnastu kroków
rozmowy, żeby dopiero wtedy usłyszeć, że Forge nie obsługuje tego kontraktu.

## Potok ładowania

```text
ContractSourcePort
      ↓  load_contract()
compile_contract()
      ├── standard JSON Schema OK?
      ├── wszystkie rule kind znane?
      ├── wszystkie operatory znane?
      ├── reguły parsowalne, id unikalne?
      └── ścieżki rozwiązywalne?  → diagnostyka warning, nie błąd
      ↓
CompiledContract
      ↓
ContractForge sessions  ──→  ContractRuleEngine
```

`ContractRuleEngine` pracuje wyłącznie na zaakceptowanym `CompiledContract`, więc w
runtime nie istnieje ścieżka „nieznana reguła”.

## Odpowiedzialność `kind`

`kind` **nie definiuje logiki** reguły. Logika wynika z `condition` i `assertion`.
`kind` określa wyłącznie skutek naruszenia:

| `kind` | skutek naruszenia |
|---|---|
| `conditional_required` | `missing` |
| `at_least_one` | `missing` |
| `conditional_forbidden` | `forbidden` |
| `cross_field` | `invalid` |
| `computed_consistency` | `invalid` |
| `reference_integrity` | `invalid` |
| `required`, `dependency`, `registry_lookup` | `skipped_non_executable` |

`required` i `dependency` powielają standardowy JSON Schema i są delegowane do
`Draft202012Validator`. `registry_lookup` w obecnej postaci nazywa swój rejestr tylko
w `message`, więc nie jest wykonywalny.

## Statusy w `ForgeState.contract_rule_issues`

| status | znaczenie | blokuje `complete`? |
|---|---|---|
| `missing` | brakuje wartości; staje się `Requirement` z `reason="contract_rule"` | nie (najpierw `needs_input`) |
| `invalid` | wartość istnieje, ale relacja jest zła | tak |
| `forbidden` | obecna jest niedozwolona sekcja/kombinacja | tak |
| `skipped_non_executable` | reguły nie da się wykonać strukturalnie; `detail` mówi dlaczego | **nie** |

Reguła o statusie `missing`, której ścieżka nie istnieje w aktywnym schemacie, również
kończy jako `skipped_non_executable` — nie da się poprosić ADCM o wypełnienie pola,
którego schemat nie zna.

## Ścieżki

Ścieżki wewnątrz `path`, `condition` i `assertion` są **relatywne do węzła schematu**,
przy którym reguła jest zadeklarowana. Reguła przy `$defs/UnpackConfig` widzi `enabled`
i `format`, nie `preparator.operations.unpack.format`. Segment `[*]` rozwija listę.

Nie ma prefiksu ścieżki absolutnej. Reguła między sekcjami kontraktu wymagałaby
rozszerzenia DSL, a nie obejścia w kodzie.

## Operatory

`anyOf`, `exists`, `equals`, `notEquals`, `gtPath`, `gtePath`, `notIn`, `existsIn`,
`equalsPath`, `formula` + `equalsPath`.

`formula` przyjmuje wyłącznie literały liczbowe, nazwy ścieżek oraz `+ - * /`.

Lista żyje w `SUPPORTED_OPERATORS` w `contract_forge/compiler.py` i jest jedynym
źródłem prawdy zarówno dla walidatora definicji, jak i dla ewaluatora.

## Przykład reguły wykonywalnej

```json
{
  "id": "preparator.decrypt.spec_required_when_enabled",
  "kind": "conditional_required",
  "path": "spec",
  "condition": { "path": "enabled", "equals": true },
  "assertion": { "path": "spec", "exists": true },
  "severity": "error",
  "message": "spec is required when decrypt.enabled is true."
}
```

## Przykład reguły obecnie niewykonywalnej

```json
{
  "id": "record_validation.macro.registered",
  "kind": "registry_lookup",
  "path": "macro",
  "message": "macro must exist in VALIDATION_REGISTRY."
}
```

Informacja o rejestrze istnieje wyłącznie w `message`, więc reguła jest raportowana jako
`skipped_non_executable`: nie tworzy `Requirement`, nie ustawia `invalid` i nie blokuje
`complete`. Gdy kontrakt dostarczy strukturalną postać, np.

```json
{ "assertion": { "path": "macro", "existsInRegistry": "VALIDATION_REGISTRY" } }
```

reguła stanie się wykonywalna po dodaniu operatora i portu rejestru.

## Dodanie nowego `kind` albo operatora

1. Dopisz `kind` do `KIND_VIOLATION_STATUS` albo operator do `SUPPORTED_OPERATORS`
   w `contract_forge/compiler.py`.
2. Dodaj deterministyczny handler w `ContractRuleEngine._eval_expression`.
3. Dodaj test w `tests/test_contract_rules.py` oraz test odrzucenia
   w `tests/test_contract_definition.py`.

Bez punktu 1 kontrakt używający nowej konstrukcji zostanie odrzucony przy starcie —
i tak ma być.
