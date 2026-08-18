---
name: repository-knowledge
description: Read, verify, create, and maintain architecture documentation for this repository. Use when explaining current behavior, planning changes, checking documentation freshness, or updating module, flow, and symbol catalogs.
---

# Repository knowledge skill

## Read order

1. `docs/architecture/.freshness.json`
2. `docs/architecture/README.md`
3. relevant curated files
4. `docs/architecture/generated/repository-map.md`
5. bounded code and test verification

## Commands

```bash
python scripts/agent/repo_inventory.py
python scripts/agent/doc_impact.py --working-tree --write
python scripts/agent/doc_freshness.py --check
python scripts/agent/doc_freshness.py --check --json
python scripts/agent/doc_freshness.py --mark-current --reason "..."
# Only for verified no-impact changes:
python scripts/agent/doc_freshness.py --mark-current --allow-no-doc-change --reason "no documentation impact: ..."
```

## Templates

- [Module](./templates/module.md)
- [Flow](./templates/flow.md)
- [Symbol catalog](./templates/symbol-catalog.md)
- [Change contract](./templates/change-contract.md)
- [Review report](./templates/review-report.md)

## Rules

- Code and tests override documentation.
- A generated inventory is navigation assistance, not semantic truth.
- Each statement should be traceable to paths and symbols.
- Split documentation by cohesive module or flow rather than creating one huge file.
- Keep historical decisions in ADRs or contracts; keep current docs focused on current behavior.
- Update links and freshness state after verified changes.
- Do not satisfy the documentation gate by changing only contracts, reviews, or generated files.
- Use the no-impact exception only with a concrete verified rationale.
