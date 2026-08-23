# Documentation automation

`docs/architecture-guardrails.md` is the authoritative architecture contract. This automation helps keep supporting documentation traceable to source changes; it never rewrites the guardrails or curated service documentation from code alone.

## What runs

`scripts/agent/documentation_update.py` regenerates:

- `docs/generated/repository-inventory.json` — machine-readable source inventory;
- `docs/generated/repository-map.md` — navigable symbol map;
- `docs/generated/documentation-impact.md` — changed source paths and configured documents to review;
- `docs/.freshness.json` — the source snapshot corresponding to the generated material.

When documentation-relevant source files are staged (including this automation
and its hooks), the `pre-commit` hook runs
the script with `--staged`. It reads the Git index rather than the working tree
and stages the four generated artifacts in the same commit. The generator uses
a content-derived source snapshot instead of a timestamp or the future commit
hash, so identical staged input has identical output.

There is no `post-commit` generator. A successful commit therefore leaves no
new generated-documentation changes in the working tree.

## Guardrails for curated documentation

The `pre-commit` hook checks staged documentation-relevant code. It requires a curated matching document (root architecture/current-state documentation or service documentation). Files below `docs/generated/` intentionally do not satisfy this condition.

This split preserves the repository rule that architecture changes need human/agent judgment while still generating deterministic navigation and impact evidence as part of the same commit.

## Manual use

```powershell
python scripts/agent/documentation_update.py
python scripts/agent/documentation_update.py --staged  # hook use; stages generated outputs
python scripts/agent/doc_freshness.py --check
python scripts/agent/install_git_hooks.py
```

The manual command writes only when the source snapshot is stale. The installer
configures the repository-local `core.hooksPath` as `githooks`.
