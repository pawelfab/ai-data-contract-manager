# Agent support scripts

Copy `config.example.json` to `config.json` and adapt it.

## Commands

```bash
python scripts/agent/repo_inventory.py
python scripts/agent/documentation_update.py
python scripts/agent/documentation_update.py --staged
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
- `doc_freshness.py --check` and `--check-staged` answer different questions; `--check` reporting `CURRENT` does not mean a commit will pass. `--check` only compares working-tree source hashes with the `docs/.freshness.json` marker. `githooks/pre-commit` runs `--check-staged`, which reads the Git index and requires both a curated document and a task document (`docs/active-task/YYYY-MM-DD_name/IMPLEMENTATION.md` or the `docs/history/` equivalent) beside documentation-relevant staged code. A staged `TASK.md` satisfies the curated requirement but never the task-document requirement.
- `documentation_update.py` regenerates the repository inventory and a documentation-impact report, then records the source snapshot. It does not invent or overwrite curated architecture/service prose.
- `githooks/pre-commit` invokes the generator with `--staged` only for documentation-relevant staged source. It reads the Git index and stages the deterministic output into the same commit; there is no post-commit generator.
- `githooks/pre-commit` requires at least one configured curated document beside documentation-relevant code. Generated files under `docs/generated/` are review aids and do not satisfy that check.
- Make documentation patterns narrower when minor internal edits should not require architecture updates.
- `strict_stop_gate` jest w tym repozytorium włączony (`true`); szablon `config.example.json` pozostawia go domyślnie wyłączonego (`false`).
- The security guard is a template, not a complete security boundary.
