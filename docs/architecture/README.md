# Repository architecture knowledge

This directory is the compact, maintained description of how the repository currently works.

## Navigation

- [System context](system-context.md)
- [Modules](modules/)
- [Flows](flows/)
- [Symbols](symbols/)
- [Change contracts](contracts/)
- [Implementation reviews](reviews/)
- [Generated repository map](generated/repository-map.md)

## Status

Read `.freshness.json` or run:

```bash
python scripts/agent/doc_freshness.py --check
```

A current marker means no configured source file hash changed since the last documentation synchronization. It does not guarantee semantic correctness.

## Documentation rules

- Curated documents describe current behavior.
- Contracts describe approved changes and their review history.
- Generated files support navigation and may contain heuristic symbol extraction.
- Code and tests remain the source of truth.
