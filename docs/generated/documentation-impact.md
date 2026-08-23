# Generated documentation impact

Generated: `2026-08-23T14:05:14.552640+00:00`
Commit: `4039ad5ae83cf8ef66a73ad572205e34d5524e62`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `docs/.freshness.json`
- `docs/CONSOLIDATED_ANALYSIS.md`
- `docs/CURRENT_STATE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/documentation-automation.md`
- `docs/generated/documentation-impact.md`
- `docs/generated/repository-inventory.json`
- `docs/generated/repository-map.md`
- `githooks/post-commit`
- `mcp-servers/mcp-contract-forge/docs/contract-repair-note.md`
- `readme.md`
- `scripts/agent/README.md`
- `scripts/agent/config.example.json`
- `scripts/agent/config.json`
- `scripts/agent/doc_freshness.py`
- `scripts/agent/documentation_update.py`

## Curated documentation to review

- No configured documentation mapping matched.

## Commit workflow

The pre-commit hook requires curated documentation with documentation-relevant code. The post-commit hook regenerates this report and the repository inventory, then records the source snapshot. Generated files are left unstaged for review and a subsequent commit.
