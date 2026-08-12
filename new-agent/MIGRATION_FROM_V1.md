# Migracja z pierwszej wersji pakietu

## Najbezpieczniejsza metoda

1. Utwórz branch:

```bash
git checkout -b chore/update-agent-workflow
```

2. Zrób kopię własnych zmian w:

- `.github/copilot-instructions.md`,
- `scripts/agent/config.json`,
- `docs/architecture/`.

3. Nałóż zawartość nowego ZIP-a na katalog główny repozytorium.

4. Nie nadpisuj własnego `scripts/agent/config.json`. Porównaj go z nowym `config.example.json` i dodaj nowe klucze:

- `documentation_evidence_patterns`,
- `documentation_non_evidence_patterns`,
- `documentation_map`,
- `documentation_impact_report`,
- `session_state_dir`,
- `session_state_max_age_hours`,
- `require_freshness_marker_for_staged_relevant_code`.

5. Zachowaj repozytoryjne informacje z dotychczasowego `.github/copilot-instructions.md`, ale dodaj sekcję nowych komend.

6. Uruchom:

```bash
python scripts/agent/validate_setup.py
python -m compileall scripts/agent
python scripts/agent/repo_inventory.py
python scripts/agent/doc_freshness.py --check
```

7. Ponieważ format znacznika zmienił się z wersji 1 na 2, po sprawdzeniu aktualnej dokumentacji uruchom:

```bash
python scripts/agent/doc_freshness.py --mark-current --reason "migrated workflow and verified current architecture documentation"
```

8. Ponownie zainstaluj hooki Git, jeżeli były używane:

```bash
python scripts/agent/install_git_hooks.py
```

9. W VS Code uruchom `Developer: Reload Window`.

## Nowe komendy

Dotychczasowe ciężkie komendy zostały rozdzielone:

| Stara komenda | Nowe domyślne zachowanie | Pełny odpowiednik |
|---|---|---|
| `/plan-change` | szybki plan bez subagentów | `/plan-change-reviewed` |
| `/implement-change` | szybka implementacja bez subagentów | `/implement-change-reviewed` |

Dodano:

- `/plan-change-preview`,
- `/review-current-change`.

## Pliki, które trzeba nadpisać

- `AGENTS.md`
- `.github/agents/feature-coordinator.agent.md`
- `.github/prompts/plan-change.prompt.md`
- `.github/prompts/implement-change.prompt.md`
- `.github/copilot-instructions.md` po ręcznym połączeniu własnych danych
- `scripts/agent/common.py`
- `scripts/agent/doc_freshness.py`
- `scripts/agent/session_context.py`
- `scripts/agent/stop_gate.py`
- `scripts/agent/config.example.json`
- `.vscode/tasks.json`
- `.gitignore.template`

## Nowe pliki

- `.github/agents/planner-fast.agent.md`
- `.github/agents/feature-fast.agent.md`
- `.github/prompts/plan-change-preview.prompt.md`
- `.github/prompts/plan-change-reviewed.prompt.md`
- `.github/prompts/implement-change-reviewed.prompt.md`
- `.github/prompts/review-current-change.prompt.md`
- `scripts/agent/doc_impact.py`
- `scripts/agent/validate_setup.py`
- `scripts/agent/setup_workflow.py`
