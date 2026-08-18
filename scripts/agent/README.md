# Agent workflow support scripts

`config.example.json` contains the reviewed ADCM defaults. `setup_workflow.py` creates the ignored local `config.json` when it is absent, validates the workflow, and generates the repository inventory.

## Commands

```bash
python scripts/agent/setup_workflow.py
python scripts/agent/validate_setup.py
python scripts/agent/repo_inventory.py
python scripts/agent/doc_impact.py --working-tree --write
python scripts/agent/doc_freshness.py --check
python scripts/agent/doc_freshness.py --check --json
python scripts/agent/doc_freshness.py --check-staged
python scripts/agent/doc_freshness.py --mark-current --reason "docs updated after feature X"
python scripts/agent/doc_freshness.py --mark-current --allow-no-doc-change --reason "no documentation impact: <specific verified rationale>"
python scripts/agent/quality_gate.py --profile pre-commit
python scripts/agent/quality_gate.py --profile pre-push
python scripts/agent/install_git_hooks.py
```

## Configuration notes

- Keep quality commands deterministic and non-interactive. The current configured gate is `python -m pytest -q`; Ruff is intentionally absent because it is not installed by project dependencies.
- `source_roots` covers `src`, `contracts`, `examples/contract-rules.json`, and `pyproject.toml`. Test-only edits do not make architecture freshness stale.
- `strict_stop_gate` is enabled, but `stop_quality_stages` is empty; Stop blocks source changes with stale docs without rerunning the full test suite.
- `doc_impact.py` is a navigation hint. Verify callers, flows, contracts, and tests before editing curated documentation.
- `install_git_hooks.py` changes repository Git configuration. Run it only when the repository owner wants `core.hooksPath=githooks`.
- The security guard adds repository policy but is not a complete operating-system security boundary.
