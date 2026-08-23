# ADCM architecture

ADCM is the conversational service. It understands user intent and owns state/orchestration; it does not understand the physical contract format.

## Main flow

```text
API / CLI
    ↓
application use cases
    ↓
Session / EvidenceStore / ContractState
    ↓
stabilization
    ├─ ContractForgePort ── mandatory deterministic call
    ├─ HeuristicsPort ───── semantic interpretation
    └─ AgentContextPort ─── optional context MCPs
```

Contract Forge is never exposed as an optional PydanticAI tool.

## Domain

Core domain concepts include:
- `Session`;
- `ContractState`;
- `EvidenceItem`;
- authority/provenance;
- advisory issues.

## Application responsibilities

Application code owns:
- session lifecycle;
- handling user messages/evidence;
- fixed-point stabilization;
- deterministic candidate validation/application;
- deciding when another question/result is required.

## Outbound boundaries

- `ContractForgePort` — mandatory Forge evaluation;
- `HeuristicsPort` — semantic LLM behavior;
- `AgentContextPort` — optional context MCP integration;
- `SessionRepositoryPort` — session persistence.

Introduce additional ports only for real I/O or independent change boundaries.

## Documentation map

State model and authority:
- `contract-state.md`

Fixed-point flow, candidate decisions, editing and warnings:
- `session-flow.md`

PydanticAI responsibilities:
- `llm-heuristics.md`

Port/adapter details:
- `ports-and-adapters.md`

Runtime/startup configuration:
- service `README.md`

Planned logging:
- `planned/logging.md`

Use `docs/generated/repository-map.md` at repository root to locate concrete implementations when needed. Verify final behavior in code and tests.
