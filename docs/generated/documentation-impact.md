# Generated documentation impact

Source snapshot: `84b8c2c9e24046d41bd3fb821514ca3313225690b381180785de555adb7f5042`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `docs/documentation-automation.md`
- `githooks/post-commit`
- `githooks/pre-commit`
- `scripts/agent/README.md`
- `scripts/agent/common.py`
- `scripts/agent/config.example.json`
- `scripts/agent/config.json`
- `scripts/agent/doc_freshness.py`
- `scripts/agent/documentation_update.py`
- `scripts/agent/repo_inventory.py`
- `scripts/agent/tests/test_documentation_update.py`

## Curated documentation to review

- No configured documentation mapping matched.

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
