---
name: ux-rules-analysis
description: Analizuje kontrakty YAML i pomaga projektować ux_rules.json na podstawie powtarzalnych wzorców oraz opisów użytkownika.
---

# UX Rules Analysis

Użyj tego skill, gdy zadanie dotyczy:
- analizy wielu kontraktów YAML,
- wykrywania podobieństw między kontraktami,
- projektowania `ux_rules.json`,
- dodawania reguł na podstawie opisu,
- oceny, czy wzorzec powinien być globalnym defaultem czy regułą systemową.

## Pliki wejściowe

Najpierw zlokalizuj:
- `contract.json`
- `ux_rules.json`
- `config/ux_rule_actions.yaml`
- katalog z istniejącymi kontraktami YAML.

Jeżeli nazwy/ścieżki są inne, wyszukaj właściwe pliki w repozytorium.

## Analiza przykładów

Uruchom:

```bash
python scripts/ux_rules_analyzer.py \
  --contracts-dir <katalog> \
  --source-system <system> \
  --output .tmp/ux-analysis.json
```

Jeżeli pole identyfikujące system jest inne:

```bash
python scripts/ux_rules_analyzer.py \
  --contracts-dir <katalog> \
  --source-system <system> \
  --source-system-path metadata.sourceSystemGcpId \
  --output .tmp/ux-analysis.json
```

Interpretuj raport jako materiał dowodowy, nie jako automatycznie obowiązującą specyfikację.

## Mapowanie wzorców na DSL

Preferuj:

- stała wartość -> `set_default`
- wartość równa innemu polu -> `copy_value`
- wartość wyprowadzana z innego pola przez stabilny format -> `format_value`
- aktywacja sekcji -> `activate_root_section`

Nie wymyślaj nowych nazw `action`.

## Global vs system-specific

Reguła może trafić do `defaults`, jeżeli:
- jest prawdziwa dla wszystkich lub praktycznie wszystkich analizowanych systemów,
- nie opisuje cechy charakterystycznej pojedynczego źródła,
- jej semantyka jest organizacyjnym defaultem.

Reguła powinna być system-specific, jeżeli:
- zależy od protokołu/formatu/nazewnictwa konkretnego systemu,
- różni się między źródłami,
- nadpisuje globalny default.

## Bezpieczeństwo zmian

Przed zapisem:
1. zweryfikuj `path`,
2. zweryfikuj `action`,
3. wykryj duplikaty `id`,
4. wykryj konflikt target path,
5. zachowaj istniejącą strukturę JSON,
6. nie usuwaj reguł niezwiązanych z zadaniem.

Jeżeli wzorzec nie jest jednoznaczny, przedstaw go jako sugestię zamiast dodawać go automatycznie.
