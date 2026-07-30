# VS Code Copilot Multi-Agent Workflow Template

Szablon organizuje pracę GitHub Copilot w VS Code wokół jednego koordynatora i wyspecjalizowanych subagentów.

## Dlaczego koordynator zamiast łańcucha agent → agent → agent

Tylko koordynator deleguje pracę. Agenci roboczy nie wywołują kolejnych agentów. Ogranicza to:
- zapętlenia,
- niekontrolowany wzrost kosztu i kontekstu,
- przekazywanie całej historii między rolami,
- przypadkowe uruchomienie implementacji podczas zwykłego pytania.

Koordynator klasyfikuje żądanie do jednego z trybów:

| Tryb | Kiedy | Uruchamiani agenci |
|---|---|---|
| `EXPLAIN` | pytanie „jak to działa?”, „gdzie jest?”, „dlaczego?” | Repository Guide; opcjonalnie Code Verifier |
| `PLAN` | prośba o plan/specyfikację bez implementacji | Repository Guide → Code Verifier → Solution Architect → Contract Reviewer → Contract Finalizer |
| `IMPLEMENT` | jawna prośba o zmianę kodu | pełny `PLAN` → Implementer → Implementation Reviewer → ewentualna poprawka → Docs Updater |
| `DOC_SYNC` | aktualizacja dokumentacji do bieżącego kodu | Code Verifier → Docs Updater |
| `BOOTSTRAP_DOCS` | pierwsze zbudowanie wiedzy o repozytorium | inwentaryzacja → równoległe analizy modułów → Docs Updater |

## Struktura

```text
.github/
  agents/                  profile agentów
  prompts/                 komendy /explain-current, /plan-change itd.
  hooks/                   deterministyczne hooki Copilota
  skills/repository-knowledge/
                            zasady i szablony dokumentacji
docs/architecture/
  modules/                 odpowiedzialności modułów
  flows/                   przepływy wykonania
  symbols/                 katalog klas, metod i funkcji
  contracts/               zatwierdzone kontrakty zmian
  reviews/                 raporty przeglądów
  generated/               inwentaryzacja generowana skryptem
scripts/agent/              skrypty wspierające
githooks/                   opcjonalne hooki Git
```

## Uruchomienie

1. Skopiuj zawartość szablonu do katalogu głównego repozytorium.
2. Dostosuj:
   - `.github/copilot-instructions.md`,
   - `scripts/agent/config.example.json`, zapisując kopię jako `scripts/agent/config.json`,
   - polecenia jakości w konfiguracji.
3. Sprawdź identyfikatory narzędzi w widoku **Configure Tools**. Szablon używa standardowych zestawów: `agent`, `read`, `search`, `edit`, `execute`.
4. Wygeneruj mechaniczną inwentaryzację:

   ```bash
   python scripts/agent/repo_inventory.py
   ```

5. W VS Code uruchom:

   ```text
   /bootstrap-repository-knowledge
   ```

6. Po zaakceptowaniu wygenerowanej dokumentacji oznacz ją jako aktualną:

   ```bash
   python scripts/agent/doc_freshness.py --mark-current --reason "initial documentation"
   ```

7. Opcjonalnie zainstaluj hooki Git:

   ```bash
   python scripts/agent/install_git_hooks.py
   ```

## Codzienne użycie

### Odpowiedź bez modyfikowania kodu

```text
/explain-current Jak działa import zamówień i gdzie walidowany jest plik?
```

Agent najpierw czyta `docs/architecture`. Kod analizuje tylko wtedy, gdy dokumentacja jest brakująca, przeterminowana lub nie potwierdza konkretnego symbolu.

### Plan i kontrakt

```text
/plan-change Dodaj możliwość ponawiania nieudanych importów.
```

Wynikiem jest plik `docs/architecture/contracts/<slug>.md`. Kod nie jest modyfikowany.

### Implementacja

```text
/implement-change Dodaj możliwość ponawiania nieudanych importów.
```

Koordynator tworzy lub odświeża kontrakt, zleca implementację, niezależny przegląd i na końcu aktualizację dokumentacji.

## Zasada aktualności dokumentacji

Dokumentacja nie jest automatycznie uznawana za prawdziwą. Skrypt przechowuje skróty plików źródłowych w `docs/architecture/.freshness.json`.

- `repo_inventory.py` generuje mapę repozytorium.
- `doc_freshness.py --check` wykrywa kod zmieniony od ostatniej synchronizacji dokumentacji.
- `doc_freshness.py --mark-current` może wykonać wyłącznie Docs Updater po sprawdzeniu zmian.
- hook `Stop` ostrzega o nieaktualnej dokumentacji.
- hook `pre-commit` może zablokować commit kodu bez aktualizacji dokumentacji.

Hook nie powinien sam generować dokumentacji przez LLM. Deterministyczny hook ma jedynie wykryć problem; aktualizację wykonuje agent na podstawie kodu i diffu.

## Ważne ograniczenia

- Hooki VS Code są funkcją Preview; format może się zmieniać.
- Nazwy narzędzi zależą od wersji VS Code i rozszerzeń. Niedostępne narzędzie może zostać pominięte.
- Proste ekstraktory symboli w `repo_inventory.py` są heurystyczne poza Pythonem. Są indeksem nawigacyjnym, nie źródłem prawdy.
- Nie włączaj zagnieżdżonych subagentów bez konkretnej potrzeby.
- Nie zezwalaj agentowi na automatyczne edytowanie hooków, skryptów bezpieczeństwa i instrukcji sterujących.
