---
module: ports
source_roots:
  - src/adcm/ports
last_verified: working-tree-2026-08-18
owners: []
---

# Ports module

## Responsibility

Define typed infrastructure boundaries used by the application without choosing transport, provider, or storage technology.

## Protocols

| Path | Protocol | Operations |
|---|---|---|
| `src/adcm/ports/contract_forge.py` | `ContractForgePort` | `evaluate_draft(ContractInput)`, `validate_final(ContractInput)`, `render_yaml(RenderRequest)`. |
| `src/adcm/ports/semantic_interpreter.py` | `SemanticInterpreterPort` | `interpret_turn(text, AgentContext)`. |
| `src/adcm/ports/session_repository.py` | `SessionRepositoryPort` | Async `load(UUID)` and `save(ConversationState)`. |
| `src/adcm/ports/capability.py` | `CapabilityHandlerPort` | Async `execute(capability, args)`. |
| `src/adcm/ports/audit_sink.py` | `AuditSinkPort` | Async `append(AuditEvent)`. |

## Boundary rules

Contract Forge is stateless from ADCM's perspective. `ContractInput` contains the current draft snapshot, prior capability results, and an optional expected schema revision—not the conversation, evidence history, or unbound signals. Adapter failures cross the boundary as application outcomes or explicit exceptions handled by the caller.

## Incoming and outgoing dependencies

Application services depend on these protocols and domain models. Adapter modules implement the protocols. Ports import only typing/UUID and domain types.

