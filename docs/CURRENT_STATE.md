# ADCM current state

This document is a concise cross-service snapshot. Detailed behavior belongs to service-specific documentation.

## Runtime services

```text
ai-data-contract-manager
        |
        | ContractForgePort / MCP
        v
mcp-contract-forge
```

The services are independently versioned and have no runtime Python imports between them.

## ADCM

Current ADCM behavior includes:
- conversation/session and evidence handling;
- user and derived state layers;
- evidence/provenance and authority-aware value history;
- mandatory Contract Forge stabilization;
- evidence-grounded PydanticAI candidate extraction;
- deterministic candidate validation before state mutation;
- fixed-point progress based on actual state changes;
- recomputation of Forge-derived values;
- editing existing values after `valid=True`;
- optional context MCP integration;
- inline text attachments as evidence.

Detailed ADCM behavior:
- `ai-data-contract-manager/docs/architecture.md`
- `ai-data-contract-manager/docs/contract-state.md`
- `ai-data-contract-manager/docs/session-flow.md`
- `ai-data-contract-manager/docs/llm-heuristics.md`

## Contract Forge

Current Forge behavior includes:
- one runtime contract source;
- isolated `contract_json_v1` parsing into `NormalizedContract`;
- full supported JSON Schema validation;
- deterministic contract-rule evaluation;
- formal/fillable requirement derivation;
- configurable progressive requirement discovery;
- semantic path anchors owned by the contract adapter;
- generic discriminated `oneOf` handling;
- explicit array expansion semantics;
- deterministic global/system enrichment;
- recomputable derived suggestions;
- stable MCP evaluation response.

Current discovery starts from the semantic source-system anchor and then exposes later requirements progressively according to Forge discovery policy.

Detailed Forge behavior:
- `mcp-servers/mcp-contract-forge/docs/architecture.md`
- `mcp-servers/mcp-contract-forge/docs/contract-format.md`
- `mcp-servers/mcp-contract-forge/docs/requirement-discovery.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- `mcp-servers/mcp-contract-forge/docs/rules-engine.md`

## Integration invariants

- Contract Forge is called deterministically by ADCM and is not an optional LLM tool.
- Context MCPs are optional and provide evidence/context/actions.
- LLM output never mutates `ContractState` directly.
- Formal validation and requirement discovery remain separate.
- `valid=True` is not a terminal workflow state.
- Derived values must be recalculated when relevant user context changes.

## Current known limitations

See `docs/KNOWN_ISSUES.md`.

Notable areas still deferred include persistent production sessions/audit logging, generic conflict-resolution policy and a durable partial-fact mechanism for incomplete column information.

## Documentation workflow

Current feature/fix/refactor work lives under:

`docs/active-task/YYYY-MM-DD_task-name/`

After completion and documentation synchronization the entire task directory moves to:

`docs/history/YYYY-MM-DD_task-name/`

Generated repository maps and documentation-impact files live under `docs/generated/` and are navigation aids, not architecture authority.
