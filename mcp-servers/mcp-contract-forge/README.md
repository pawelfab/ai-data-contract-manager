# MCP Contract Forge

Deterministic MCP service for contract interpretation, requirement discovery, enrichment/defaults and validation.

It intentionally does **not** depend on PydanticAI. Identical relevant inputs should produce identical Forge outputs.

Only the concrete `contract_json_v1` adapter understands the current raw `contract.json` layout. Contract-format evolution should remain behind that adapter whenever normalized semantics remain compatible.

## Runtime configuration sources

- `resources/contract.json` — formal contract/schema/rule semantics;
- `resources/discovery_rules.json` — progressive requirement visibility/presentation;
- `resources/ux_rules.json` — enrichment configuration.

These sources have separate responsibilities.

## Documentation

Start with:

`docs/architecture.md`

It routes to detailed documents for:
- contract format;
- requirements/discovery/schema validation;
- enrichment;
- rules;
- ports/adapters;
- MCP API.

Historical repair notes are under `docs/history/` and are not normal implementation guidance.
