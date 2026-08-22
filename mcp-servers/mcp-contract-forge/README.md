# MCP Contract Forge

Deterministic MCP service for contract discovery, defaults/enrichment and validation.

It intentionally does **not** depend on PydanticAI. The service uses Pydantic for typed models and the MCP Python SDK for transport.

Only the `contract_json_v1` adapter knows the supplied raw `contract.json` structure. A future structural change should be handled by replacing/adding this adapter while preserving normalized domain models and Forge API v1.


## Discovery and enrichment

`resources/discovery_rules.json` controls which formal requirements are visible now; it does not define validity. `resources/ux_rules.json` contains normalized enrichment data. Global rules support JSON-pointer value copying/interpolation and path patterns, while system rules are activated only when the semantic source-system context matches.

The source-system-first gate is a semantic anchor from `contract_json_v1/semantic_paths.py`, not a hard-coded ADCM path.

See `docs/requirement-discovery.md`, `docs/enrichment.md` and `docs/contract-repair-note.md`.
