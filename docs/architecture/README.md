# ADCM architecture knowledge

This directory is the maintained, evidence-linked description of how ADCM and its repository workflow currently work. Executable code, contract artifacts, tests, and observable command output remain authoritative.

## Navigation

- [System context](system-context.md)
- Modules: [domain](modules/domain.md), [application](modules/application.md), [ports](modules/ports.md), [adapters](modules/adapters.md), [contract schema](modules/contract-schema.md), [agent workflow](modules/agent-workflow.md)
- Flows: [user turn](flows/turn-lifecycle.md), [Contract Forge](flows/contract-forge-workflow.md), [repository change](flows/agent-change-workflow.md)
- Symbols: [domain](symbols/domain.md), [application](symbols/application.md), [ports](symbols/ports.md), [adapters](symbols/adapters.md), [agent workflow](symbols/agent-workflow.md)
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
- Updating only a contract, review, or generated file does not satisfy the post-implementation documentation gate.
- Legacy topic documents remain under `docs/`; this directory is the agent workflow's curated index and freshness evidence.
