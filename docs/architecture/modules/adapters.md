---
module: adapters
source_roots:
  - src/adcm/adapters
last_verified: working-tree-2026-08-18
owners: []
---

# Adapters module

## Responsibility

Provide replaceable reference implementations for semantic interpretation, Contract Forge behavior, session persistence, and audit output.

## Components

| Path | Symbol | Responsibility |
|---|---|---|
| `src/adcm/adapters/mcp/mock_contract_forge.py` | `MockContractForgeAdapter` | Executable stateless Forge example with staged schema views, evaluation, final validation, and YAML rendering. |
| `src/adcm/adapters/llm/rule_based_interpreter.py` | `RuleBasedInterpreter` | Deterministic demo/test extraction, including ASCII-folded Polish delimiter variants. |
| `src/adcm/adapters/llm/pydantic_ai_interpreter.py` | `PydanticAIInterpreter` | Optional Pydantic AI structured semantic adapter; raises `RuntimeError` when the optional dependency is unavailable. |
| `src/adcm/adapters/persistence/memory.py` | `InMemorySessionRepository` | Deep-copied in-process state. |
| `src/adcm/adapters/persistence/json_file.py` | `JsonFileSessionRepository` | One UTF-8 JSON document per session. |
| `src/adcm/adapters/logging/jsonl_audit.py` | `JsonlAuditSink` | Append-only JSONL audit output. |

## Side effects and failure behavior

JSON persistence creates its target directory and writes session files. JSONL audit creates its parent and appends. The mock Forge checks expected schema revisions. Infrastructure-specific retries, authentication, and transport configuration are not implemented in the reference adapters.

## Tests proving behavior

`tests/test_workflow.py`, `tests/test_render_service.py`, and `tests/test_rule_based_interpreter.py` exercise the mock Forge and deterministic semantic adapter. Persistence/audit adapters currently have no dedicated integration tests.

