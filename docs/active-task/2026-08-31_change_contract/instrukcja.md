# Zadanie: dostosowanie ADCM / Contract Forge do rozszerzonego `contract.json`

Pracujesz na istniejącym systemie ADCM + Contract Forge.

Dostaniesz:

1. pełny nowy `contract.json`;
2. aktualne repozytorium ADCM i Contract Forge;
3. istniejące testy;
4. dokumentację architektury i business behavior.

Twoim zadaniem jest **przeanalizować kompatybilność nowego kontraktu z aktualnym systemem, a następnie wprowadzić minimalne konieczne zmiany**, zachowując modularność, black-box architecture i istniejący podział odpowiedzialności.

Nie zakładaj, że nowy kontrakt wymaga dużego refaktoru.

---

# 1. Najważniejsza zasada architektoniczna

Obowiązuje:

```text
ADCM understands the user.
Contract Forge understands the contract.
```

## ADCM odpowiada za

* rozmowę z użytkownikiem;
* interpretację intencji;
* `IntentResolution`;
* session state;
* provenance i authority;
* `ContractState`;
* mutation commands;
* fixed-point orchestration;
* application rules / UX conventions;
* odpowiedź dla użytkownika;
* external checks.

## Contract Forge odpowiada za

* strukturę `contract.json`;
* parsowanie schema;
* wymagane pola;
* dozwolone wartości;
* typy;
* defaults;
* formalne zależności;
* `x-contract-rules`;
* formalne proposals;
* diagnostics;
* `valid / complete / clean`;
* opis możliwości kontraktu dla ADCM.

## Contract Forge NIE zna

* conversation history;
* user intent;
* LLM;
* provenance ADCM;
* USER_EXPLICIT;
* session state.

## ADCM NIE może znać konkretnych ścieżek nowego kontraktu

Nie dodawaj do ADCM kodu typu:

```python
if path == "/bronze/table/project":
    ...

if "bronze" in document:
    ...

if source_type == "csv":
    ...
```

chyba że jest to jawna reguła UX/application convention zapisana w konfiguracji, a nie hardcoded business logic.

Dodanie np.:

```text
bronze
silver
gold
```

nie powinno wymagać zmian w `ContractState`, `DocumentEngine`, `CandidatePolicy`, `ProposalReconciler`, API ani orchestratorze.

---

# 2. `contract.json` jest zewnętrznie własnością innego systemu

Nie zmieniaj `contract.json` tylko po to, żeby aktualny Forge potrafił go obsłużyć.

Jeśli znajdziesz błąd lub niespójność kontraktu:

1. zgłoś ją;
2. pokaż dokładne miejsce;
3. sklasyfikuj jako:

```text
CONTRACT_ERROR
CONTRACT_AMBIGUITY
UNSUPPORTED_SCHEMA_FEATURE
UNSUPPORTED_RULE_FEATURE
APPLICATION_CONFIGURATION_REQUIRED
```

4. nie ukrywaj problemu przez specjalny kod w ADCM/Forge.

Dopuszczalne jest przygotowanie poprawionej wersji kontraktu jako **propozycji diagnostycznej**, ale nie traktuj jej jako rozwiązania implementacyjnego bez jawnej decyzji.

---

# 3. Najpierw sprawdź kontrakt sam w sobie

Zanim zmienisz kod aplikacji, przeanalizuj cały nowy `contract.json`.

Sprawdź:

## JSON

* poprawność składni JSON;
* brak duplicate keys;
* poprawne escaping;
* poprawne typy wartości.

## JSON Schema

Sprawdź:

```text
$schema
$defs
$ref
properties
required
additionalProperties
type
enum
const
default
oneOf
anyOf
allOf
not
items
minItems
maxItems
pattern
format
```

oraz inne użyte keywords.

Zweryfikuj wszystkie `$ref`.

Wskaż nieużywane lub błędne `$defs`.

---

# 4. Sprawdź spójność ścieżek

To jest szczególnie ważne.

W dostarczonym wcześniej fragmencie występował przykład:

Schema:

```text
destPartition
source.sourceType
```

a `x-contract-rules` używało m.in.:

```text
dest_partition
source.source_type
source.fixed_width
```

Nie zakładaj, że pełny nowy kontrakt nadal ma te błędy.

Sprawdź go faktycznie.

Dla każdego `x-contract-rule` zweryfikuj:

```text
path
condition.path
assertion.path
derived_from
```

względem faktycznego schema tree.

Jeżeli rule wskazuje ścieżkę, która nie istnieje w schema:

```text
→ CONTRACT_ERROR
```

Nie implementuj aliasów w Forge typu:

```text
source_type → sourceType
dest_partition → destPartition
```

bez wyraźnej decyzji architektonicznej.

---

# 5. Zbuduj najpierw Capability Matrix

Przed kodowaniem utwórz tabelę wszystkich istotnych konstrukcji użytych przez nowy kontrakt.

Przykład:

| Feature                 | Used by contract | Forge support | Action         |
| ----------------------- | ---------------: | ------------: | -------------- |
| `$ref`                  |              yes |           yes | none           |
| nested object           |              yes |           yes | none           |
| optional section        |              yes |           yes | none           |
| array of objects        |              yes |           yes | none           |
| `enum`                  |              yes |           yes | none           |
| `const`                 |              yes |             ? | verify         |
| `default`               |              yes |           yes | none           |
| nullable `anyOf`        |              yes |             ? | verify         |
| `oneOf`                 |              yes |       partial | inspect        |
| `discriminator`         |              yes |             ? | inspect        |
| `conditional_required`  |              yes |             ? | implement/flag |
| `conditional_forbidden` |              yes |             ? | implement/flag |
| `at_least_one`          |              yes |             ? | implement/flag |

Nie koduj przed wykonaniem tej analizy.

---

# 6. Rozróżniaj trzy typy zmian

## A. Nowa struktura danych

Przykład:

```text
/bronze
/bronze/table/project
/bronze/table/dataset
/bronze/table/table
```

Jeżeli istniejące generyczne schema traversal potrafi to odczytać:

```text
→ ZERO CODE CHANGES
```

To jest oczekiwany wynik.

---

## B. Nowa konfiguracja biznesowa

Przykład:

```text
dla systemu SAP:
aktywuj bronze
ustaw source config
wygeneruj konkretny template
```

To powinno trafić do:

```text
ux_rules / application configuration
```

a nie do hardcoded ADCM Python.

---

## C. Nowy rodzaj semantyki kontraktu

Przykład:

```text
at least one of A/B
A required when B=X
A forbidden when B!=X
value must equal another path
cross-field dependency
```

To może wymagać rozszerzenia:

```text
Contract Forge
```

ale powinno zostać zaimplementowane **generycznie jako operator/reguła**, a nie pod konkretną ścieżkę.

Dobre:

```python
evaluate_conditional_required(rule, document)
```

Złe:

```python
if rule.id == "converter.fixed_width.required_for_fixed_width_source":
    ...
```

---

# 7. Bronze nie jest specjalnym przypadkiem

Jeżeli nowy kontrakt dodaje:

```text
bronze
```

obok:

```text
silver
gold
```

nie twórz:

```text
BronzeEngine
BronzeHandler
BronzeService
```

jeśli nie istnieje rzeczywiście odrębna semantyka.

Bronze jest po prostu kolejną częścią dynamicznego dokumentu kontraktu.

ADCM nadal powinien operować na:

```python
dict[str, Any]
JSON Pointer
```

---

# 8. Nie twórz modeli Pydantic odwzorowujących cały contract.json w ADCM

ADCM nie powinien otrzymać:

```python
class BronzeConfig(...)
class SilverConfig(...)
class GoldConfig(...)
```

tylko dlatego, że sekcje pojawiły się w kontrakcie.

To złamałoby dynamiczny charakter systemu.

ADCM:

```python
ContractState.document: dict[str, Any]
```

pozostaje bez zmian.

---

# 9. Contract Definition boundary

Obecny kierunek powinien pozostać:

```text
contract.json
      ↓
ContractDefinitionPort
      ↓
FileContractDefinitionAdapter
      ↓
ContractDefinitionNormalizer
      ↓
normalized internal representation
      ↓
Forge Analyzer
```

Przeanalizuj przede wszystkim:

```text
ContractDefinitionNormalizer
schema traversal
$ref resolver
oneOf handling
required discovery
proposal generation
x-contract-rules parsing
rule evaluation
```

Nie omijaj normalizera specjalnymi wyjątkami.

---

# 10. `discriminator`

Nowy kontrakt może używać konstrukcji typu:

```json
{
  "discriminator": {
    "propertyName": "sourceType",
    "mapping": {
      "csv": "#/$defs/CsvSourceConfig",
      "jdbc": "#/$defs/JdbcSourceConfig"
    }
  },
  "oneOf": [...]
}
```

Najpierw sprawdź, jak aktualny Forge wybiera branch `oneOf`.

Nie zakładaj, że `discriminator` automatycznie działa.

Jeżeli Forge musi go obsługiwać:

* zaimplementuj generyczną interpretację;
* nie hardcoduj `sourceType`;
* `propertyName` musi pochodzić z kontraktu;
* mapping musi pochodzić z kontraktu.

Jeżeli istniejący mechanizm potrafi jednoznacznie wybrać branch bez `discriminator`, nie dodawaj drugiego równoległego mechanizmu bez potrzeby.

---

# 11. Nullable `anyOf`

Kontrakt może zawierać:

```json
"anyOf": [
  {"$ref": "..."},
  {"type": "null"}
]
```

Sprawdź, czy Forge poprawnie rozumie:

```text
optional property
vs
property present with null
```

Nie traktuj:

```text
missing
```

i:

```text
null
```

jako tego samego, jeśli schema rozróżnia te przypadki.

---

# 12. `default`

Default z JSON Schema powinien nadal być propozycją:

```text
FORGE_DEFAULT
```

a nie bezpośrednią mutacją.

Flow pozostaje:

```text
Forge
→ Proposal
→ ProposalReconciler
→ MutationCommand
→ DocumentEngine
```

Forge nie modyfikuje dokumentu.

---

# 13. `const`

Jeżeli kontrakt zawiera np.:

```json
"algorithm": {
  "const": "fingerprint",
  "default": "fingerprint"
}
```

sprawdź dwa niezależne zachowania:

1. wartość inna niż `fingerprint` powinna być formalnie niedopuszczalna;
2. brak wartości może wygenerować default proposal.

Nie utożsamiaj `const` z `default`.

---

# 14. Arrays

Nowy kontrakt prawdopodobnie będzie intensywniej używał arrays:

```text
columns[]
tables[]
files[]
business key columns[]
```

Zweryfikuj:

```text
items
required w elementach
minItems
nested $ref
writable paths typu /*
```

Nie hardcoduj indeksów.

Forge powinien opisywać array generically np.:

```text
/tables/*
/tables/*/name
```

ADCM mutation layer nadal używa konkretnych JSON Pointerów:

```text
/tables/0/name
```

---

# 15. `x-contract-rules`

To prawdopodobnie najważniejszy obszar zmian.

Zrób inventory wszystkich:

```text
kind
assertion operators
condition operators
path forms
severity
```

w nowym kontrakcie.

Dla każdego podaj:

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
INVALID
```

Nie zakładaj, że tekst:

```text
message
description
source.pydantic_validator
```

jest wykonywalną regułą.

Formalna logika musi wynikać z maszynowo interpretowalnej struktury.

---

# 16. Nie próbuj programować opisów tekstowych

Jeśli kontrakt ma:

```json
"description": "..."
"message": "..."
"source": {
  "pydantic_validator": "..."
}
```

a brakuje formalnego assertion/condition, nie twórz parsera języka naturalnego.

Nie:

```text
message → LLM → business validation
```

Forge musi pozostać deterministyczny.

Taki przypadek oznacz jako:

```text
UNSUPPORTED_NON_PROGRAMMATIC_RULE
```

---

# 17. Progressive requirements

Nowy kontrakt może mieć dużo więcej pól, ale ADCM nie powinien od razu pytać użytkownika o wszystko.

Forge powinien raportować formalne requirements zgodnie z aktualnie aktywnym branch/schema.

ADCM odpowiada za:

```text
question ordering
conversation UX
```

Nie przenoś question ordering do Forge.

---

# 18. Opcjonalne sekcje

Sekcje takie jak:

```text
bronze
silver
gold
checksum
preparator
converter
```

mogą być opcjonalne.

Rozróżniaj:

```text
schema allows section
```

od:

```text
section currently active
```

Nie uznawaj wszystkich pól opcjonalnej sekcji za missing tylko dlatego, że istnieją w `$defs`.

---

# 19. Application rules nadal są proposals

Jeżeli nowy `ux_rules` będzie aktywował Bronze:

```text
source system X
    ↓
activate /bronze
```

reguła tworzy:

```text
Proposal(mode=ENSURE_PRESENT)
```

Nie modyfikuje dokumentu bezpośrednio.

---

# 20. Activation semantics

Pamiętaj o istniejącym założeniu:

```text
ENSURE_PRESENT
```

dla pustych:

```text
{}
[]
```

nie oznacza:

```text
SET EXACT VALUE
```

Aktywacja sekcji:

```text
/bronze = {}
```

nie może później wyczyścić:

```text
/bronze/table/...
```

---

# 21. Stale derived values

Przy zmianie upstream values, np.:

```text
sourceSystemGcpId:
sap → rocket
```

wszystkie derived values zależne od starego systemu muszą zostać:

```text
recomputed
lub
retracted
```

zgodnie z provenance i producer lifecycle.

Nie usuwaj USER_EXPLICIT values.

---

# 22. Bezpieczeństwo subtree retraction

Jeżeli auto-aktywowana sekcja zawiera user-owned child:

```text
/bronze                  APP_RULE
/bronze/table/project    USER_EXPLICIT
```

dezaktywacja producenta `/bronze` nie może bezmyślnie usunąć wartości użytkownika.

Jeżeli obecny kod tego nie potrafi obsłużyć, zgłoś jako:

```text
KNOWN_ARCHITECTURAL_GAP
```

Nie implementuj dużego rozwiązania bez potwierdzenia, jeśli nowy kontrakt faktycznie nie wymusza tego przypadku.

---

# 23. Authority pozostaje bez zmian

Priorytet:

```text
USER_EXPLICIT
>
USER_RULE
>
APP_RULE
>
FORGE_ENRICHMENT
>
FORGE_DEFAULT
```

Nowy kontrakt nie może zmieniać tych zasad.

---

# 24. Forge jest stateless

Każde:

```text
analyze(document)
```

musi zależeć tylko od:

```text
contract definition
+
current document
```

Nie dodawaj cache'u biznesowego zależnego od poprzednich tur.

Techniczny cache definicji contract schema jest dopuszczalny.

---

# 25. Fixed point pozostaje generyczny

Nie zmieniaj algorytmu:

```text
Forge analyze
    ↓
Forge proposals
+
ADCM rule proposals
    ↓
ProposalReconciler
    ↓
MutationCommands
    ↓
DocumentEngine
    ↓
repeat until stable
```

chyba że analiza nowego kontraktu udowodni realny problem w tym mechanizmie.

Większa liczba zależności może oznaczać więcej rund.

To samo w sobie nie jest błędem.

---

# 26. Nie optymalizuj liczby rund przed poprawnością

Jeżeli bardziej rozbudowany kontrakt stabilizuje się np. w:

```text
5–7 rounds
```

ale każda runda wprowadza logiczną nową warstwę zależności, najpierw potwierdź poprawność.

Nie dodawaj batchowania lub niejawnego shortcut logic tylko po to, żeby zmniejszyć liczbę rund.

---

# 27. IntentResolver powinien korzystać z opisu kontraktu

Nowe ścieżki:

```text
/bronze/...
/converter/output/...
/checksum/...
```

powinny trafić do resolvera poprzez:

```text
ForgeDescription
```

Nie dopisuj nazw pól do promptu PydanticAI na sztywno.

Jeżeli ForgeDescription nie dostarcza wystarczającej informacji, popraw **opis capability boundary**, a nie prompt z konkretnymi ścieżkami.

---

# 28. Knowledge queries

Pytania typu:

```text
jakie opcje ma converter?
jakie pola ma bronze?
jakie wartości są dostępne dla sourceType?
```

powinny być obsługiwane jako:

```text
IntentKind.KNOWLEDGE
```

i nie mogą mutować kontraktu.

Nowy kontrakt nie powinien wymagać hardcoded obsługi tych pytań.

---

# 29. REST API

Nie zmieniaj publicznego REST API tylko dlatego, że kontrakt ma nowe sekcje.

API zwraca dynamiczny:

```text
document
```

więc Bronze/Silver/Gold powinny pojawić się automatycznie.

Jeżeli API wymaga zmian tylko po to, żeby znać `/bronze`, jest to sygnał złej abstrakcji.

---

# 30. Contract status

Nowy kontrakt nadal musi dawać:

```text
valid
complete
clean
missing
diagnostics
```

Nie zmieniaj znaczenia tych pól.

---

# 31. External checks

Jeżeli nowy kontrakt będzie zawierał wymagania typu:

```text
table exists
column exists
dataset exists
```

nie implementuj ich w Forge.

To jest:

```text
ExternalCheckCoordinator
→ SchemaExplorerPort
```

Forge może znać deklarację capability, ale nie wykonuje zewnętrznych zapytań.

---

# 32. Jak implementować brakujące features

Każdy nowy feature implementuj jako mały black box.

Przykład:

```text
RuleConditionEvaluator
Input:
    condition
    document

Output:
    bool
```

lub:

```text
SchemaBranchResolver
Input:
    normalized schema node
    document fragment

Output:
    selected branch / ambiguous / none
```

Nie twórz dużego:

```text
ContractProcessor
```

z dziesiątkami odpowiedzialności.

---

# 33. Preferuj istniejące moduły

Zanim utworzysz nową klasę:

1. sprawdź, kto obecnie jest właścicielem tej odpowiedzialności;
2. rozszerz istniejący black box, jeśli nowa funkcja naturalnie do niego należy;
3. nowy moduł twórz tylko wtedy, gdy odpowiedzialność jest rzeczywiście nowa.

Nie twórz:

```text
BronzeManager
AdvancedContractManager
ComplexRulesEngine
ContractV2Service
```

---

# 34. Nie twórz kodu pod konkretny contract version

Złe:

```python
if definition_version == "2.0":
    ...
```

Dobre:

```text
Forge wykrywa capabilities schematu na podstawie jego struktury.
```

---

# 35. Test-first dla każdego unsupported feature

Dla każdej wykrytej luki najpierw dodaj minimalny test.

Przykład:

```text
contract fragment:
conditional_required

document:
sourceType = fixed_width

expected:
missing /...

```

Dopiero potem implementacja.

---

# 36. Contract compatibility tests

Dodaj test:

```text
load actual contract
      ↓
normalize
      ↓
describe
      ↓
analyze minimal documents
```

Powinien potwierdzać przynajmniej:

```text
wszystkie $refs resolvable
brak crash
brak unsupported silently ignored
writable paths poprawne
required paths poprawne
defaults poprawne
rule inventory poprawne
```

---

# 37. Unsupported features muszą failować jawnie

Najgorszy stan:

```text
Forge nie rozumie rule
ale po prostu ją ignoruje
i zwraca valid=true
```

To jest niedopuszczalne.

Jeżeli feature jest formalnie wymagany przez kontrakt, ale nieobsługiwany:

```text
contract load / normalization
→ explicit unsupported diagnostic/error
```

Nie udawaj, że kontrakt został poprawnie przeanalizowany.

---

# 38. Rozróżnij startup compatibility od document diagnostics

Problem typu:

```text
Forge does not support schema keyword used by contract
```

jest błędem kompatybilności definicji.

Nie powinien być zwykłym:

```text
document diagnostic
```

dla użytkownika.

To problem deployment/configuration.

---

# 39. Performance

Dopiero po poprawności zmierz:

```text
contract load time
Forge analyze duration
writable count
rule count
fixed-point rounds
```

Nie optymalizuj przed pomiarem.

---

# 40. Zakaz dużego refaktoru bez dowodu

Jeżeli nowy kontrakt ujawnia jedną nieobsługiwaną konstrukcję:

```text
conditional_required
```

nie przebudowuj całego Forge.

Dodaj najmniejszy generyczny element potrzebny do obsługi tej semantyki.

---

# 41. Oczekiwany proces pracy

## Etap A — inspection

Bez zmian kodu.

Przeczytaj:

```text
AGENTS.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
docs/architecture.md
docs/architecture-guardrails.md
docs/KNOWN_ISSUES.md
business_behavior
```

oraz aktualny kod Forge/ADCM.

---

## Etap B — contract validation

Sprawdź pełny nowy `contract.json`.

Wynik:

```text
syntax errors
schema errors
broken refs
invalid rule paths
ambiguities
```

---

## Etap C — capability gap analysis

Podziel wszystko na:

```text
ALREADY_SUPPORTED
CONFIG_ONLY
CONTRACT_ERROR
FORGE_EXTENSION
ADCM_EXTENSION
EXTERNAL_CHECK
DEFERRED
```

Preferowany wynik:

```text
ADCM_EXTENSION = jak najmniej
```

---

## Etap D — implementation plan

Dla każdej zmiany podaj:

```text
owner
input
output
files
tests
blast radius
why existing abstraction is insufficient
```

---

## Etap E — test first

Dodaj failing test dla każdego potwierdzonego gapu.

---

## Etap F — minimal implementation

Implementuj po jednej capability.

Po każdej:

```text
focused tests
Forge regression
ADCM regression
```

---

## Etap G — actual contract test

Na końcu załaduj pełny rzeczywisty kontrakt.

Nie kończ na synthetic fixtures.

---

## Etap H — live behavior regression

Uruchom istotne scenariusze business behavior przez ADCM API.

---

# 42. Przed implementacją przygotuj raport

## Contract overview

Podaj:

```text
root sections
optional sections
required sections
$defs count
oneOf count
anyOf count
arrays
defaults
enums
consts
x-contract-rules count
```

## New paths

Pokaż główne nowe obszary, np.:

```text
/bronze
/converter/...
/checksum/...
...
```

Nie wypisuj tysięcy leaf paths, jeśli nie jest to potrzebne.

## Unsupported matrix

Tabela:

```text
feature
contract location
current behavior
desired behavior
owner
action
```

## Contract issues

Osobno:

```text
invalid paths
broken refs
invalid semantics
ambiguous rules
```

## Architecture impact

Osobno:

```text
ADCM
Forge
ux_rules
API
external checks
tests
```

---

# 43. Stop conditions

Zatrzymaj implementację i zgłoś problem, jeśli:

### A.

Pełny kontrakt jest wewnętrznie niespójny i nie da się jednoznacznie ustalić oczekiwanej semantyki.

### B.

Dostosowanie wymaga hardcoded ścieżek kontraktu w ADCM core.

### C.

Implementacja nowego operatora rule wymaga dużego frameworka, mimo że kontrakt używa go tylko w jednym niejasnym miejscu.

### D.

Musiałbyś zacząć interpretować `message`/`description` jako wykonywalny kod.

### E.

Jedna zmiana wymaga przekroczenia granicy odpowiedzialności między ADCM i Forge.

Wtedy najpierw przedstaw prostsze opcje.

---

# 44. Czego NIE robić

Nie:

* przepisuj aplikacji od nowa;
* twórz modeli ADCM odpowiadających całemu contract schema;
* hardcoduj Bronze/Silver/Gold w core;
* hardcoduj konkretne rule IDs;
* hardcoduj `sourceType`;
* dodawaj ścieżek `/bronze/...` do orchestratora;
* pozwalaj Forge modyfikować dokument;
* pozwalaj LLM walidować formalne reguły;
* interpretuj tekstowych descriptions jako reguły;
* zmieniaj authority precedence;
* omijaj ProposalReconciler;
* omijaj DocumentEngine;
* przenoś external checks do Forge;
* rozszerzaj REST DTO o każde nowe pole kontraktu;
* ignoruj nieobsługiwanych schema/rule features;
* poprawiaj błędnego kontraktu po cichu;
* dodawaj compatibility aliases bez decyzji;
* optymalizuj przed pomiarem;
* naprawiaj testu specjalnym przypadkiem.

---

# 45. Zasada decyzyjna

Przy każdej potrzebnej zmianie zadaj kolejno:

### 1.

Czy jest to tylko nowa ścieżka/sekcja?

```text
YES → powinno działać bez code change.
```

### 2.

Czy jest to konwencja aplikacyjna?

```text
YES → ux_rules/config.
```

### 3.

Czy jest to formalna semantyka kontraktu?

```text
YES → Forge.
```

### 4.

Czy wymaga zewnętrznej wiedzy?

```text
YES → ExternalCheckCoordinator / Context MCP.
```

### 5.

Czy dotyczy interpretacji języka użytkownika?

```text
YES → IntentResolver.
```

Dopiero wtedy wybieraj moduł.

---

# 46. Kryteria akceptacji

Zmiana jest zakończona, gdy:

1. pełny nowy kontrakt przechodzi formalną kontrolę kompatybilności;
2. wszystkie `$ref` są poprawnie obsługiwane;
3. nowe sekcje są odkrywane bez hardcodingu ADCM;
4. Forge poprawnie odkrywa writable/missing;
5. defaults pozostają proposals;
6. unsupported formal rules nie są ignorowane;
7. nowe obsługiwane rules mają testy;
8. `oneOf`/`discriminator` działa zgodnie z kontraktem;
9. optional sections nie powodują fałszywego missing;
10. arrays działają generycznie;
11. ADCM nadal używa dynamicznego `ContractState`;
12. authority/provenance są bez zmian;
13. fixed-point nadal converges;
14. API nie wymaga znajomości Bronze/Silver/Gold;
15. istniejące testy regresyjne przechodzą;
16. nowe contract compatibility tests przechodzą;
17. kluczowe business behavior live tests przechodzą;
18. nie dodano special-case paths do ADCM core.

---

# 47. Oczekiwany finalny handoff

Na końcu odpowiedz:

## Handoff

* contract_valid:
* contract_errors:
* contract_ambiguities:
* new_major_sections:
* already_supported_features:
* unsupported_features_found:
* forge_changes:
* adcm_changes:
* ux_rules_changes:
* external_check_gaps:
* files_changed:
* new_modules:
* tests_added:
* contract_compatibility_tests:
* regression_tests:
* live_tests:
* remaining_unsupported_features:
* known_contract_issues:
* architecture_deviations:
* performance_observations:
* recommended_next_step:

## Capability matrix

Tabela:

| Capability | Status | Owner | Implementation |
| ---------- | ------ | ----- | -------------- |

## Most important conclusion

Odpowiedz wprost:

```text
Czy nowy contract.json został obsłużony przez rozszerzenie generycznych capabilities,
czy aplikacja zaczęła zawierać specjalne przypadki związane z konkretnym kontraktem?
```

Jeśli odpowiedź brzmi, że wymagane były special cases w ADCM core, traktuj to jako sygnał problemu architektonicznego i wyjaśnij dlaczego.
