# Documentation automation

`docs/architecture-guardrails.md` is the authoritative architecture contract. This automation helps keep supporting documentation traceable to source changes; it never rewrites the guardrails or curated service documentation from code alone.

## What runs

`scripts/agent/documentation_update.py` regenerates:

- `docs/generated/repository-inventory.json` — machine-readable source inventory;
- `docs/generated/repository-map.md` — navigable symbol map;
- `docs/generated/documentation-impact.md` — changed source paths and configured documents to review;
- `docs/.freshness.json` — the source snapshot corresponding to the generated material.

The `post-commit` hook runs the script with `--after-commit`. It leaves generated changes unstaged because a post-commit hook cannot modify the commit that has already been created. Review those files and commit them normally.

## Guardrails for curated documentation

The `pre-commit` hook checks staged documentation-relevant code. It requires a curated matching document (root architecture/current-state documentation or service documentation). Files below `docs/generated/` intentionally do not satisfy this condition.

This split preserves the repository rule that architecture changes need human/agent judgment while still generating deterministic navigation and impact evidence after every commit.

## Manual use

```powershell
python scripts/agent/documentation_update.py
python scripts/agent/doc_freshness.py --check
python scripts/agent/install_git_hooks.py
```

The installer configures the repository-local `core.hooksPath` as `githooks`.
