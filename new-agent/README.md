# Repository architecture knowledge

This directory contains the compact, maintained description of how the repository currently works.

## Navigation

- [System context](system-context.md)
- [Modules](modules/)
- [Flows](flows/)
- [Symbols](symbols/)
- [Change contracts](contracts/)
- [Implementation reviews](reviews/)
- [Generated repository map](generated/repository-map.md)
- [Generated documentation impact](generated/documentation-impact.md)

## Status

Read `.freshness.json` or run:

```bash
python scripts/agent/doc_freshness.py --check
```

A current marker means configured source hashes have not changed since explicit synchronization. It does not prove semantic correctness.

## Documentation rules

- Curated module, flow, symbol, system-context, and index documents describe current behavior.
- Contracts describe proposed or approved changes.
- Reviews describe review history.
- Generated files are navigation aids.
- Code, migrations, tests, and observable command output remain the source of truth.
- Updating only a contract or generated file does not satisfy the post-implementation documentation gate.
