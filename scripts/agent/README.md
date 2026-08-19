# Agent support scripts

Copy `config.example.json` to `config.json` and adapt it.

## Commands

```bash
python scripts/agent/repo_inventory.py
python scripts/agent/doc_freshness.py --check
python scripts/agent/doc_freshness.py --check-staged
python scripts/agent/doc_freshness.py --mark-current --reason "docs updated after feature X"
python scripts/agent/quality_gate.py --profile pre-commit
python scripts/agent/quality_gate.py --profile pre-push
python scripts/agent/install_git_hooks.py
```

## Configuration notes

- Keep quality commands deterministic and non-interactive.
- Use the same canonical commands as CI.
- Make documentation patterns narrower when minor internal edits should not require architecture updates.
- `strict_stop_gate` jest w tym repozytorium włączony (`true`); szablon `config.example.json` pozostawia go domyślnie wyłączonego (`false`).
- The security guard is a template, not a complete security boundary.
