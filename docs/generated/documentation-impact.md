# Generated documentation impact

Source snapshot: `070963b3c76eb9f343e2bfc013ec9fe18550efa3eab32e433471c02adce49f2f`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `docs/active-task/2026-08-23_freshness-eol/IMPLEMENTATION.md`
- `docs/active-task/2026-08-23_freshness-eol/TASK.md`
- `docs/documentation-automation.md`
- `scripts/agent/common.py`
- `scripts/agent/repo_inventory.py`

## Curated documentation to review

- `AGENTS.md`
- `docs/documentation-automation.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
