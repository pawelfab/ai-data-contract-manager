---
scope: src/adcm/adapters
last_verified: working-tree-2026-08-18
---

# Symbol catalog: adapters

- `mcp/mock_contract_forge.py::MockContractForgeAdapter.evaluate_draft` — reference staged schema evaluation.
- `mcp/mock_contract_forge.py::MockContractForgeAdapter.validate_final` — reference final status.
- `mcp/mock_contract_forge.py::MockContractForgeAdapter.render_yaml` — reference YAML rendering.
- `llm/rule_based_interpreter.py::_ascii_fold`, `RuleBasedInterpreter.interpret_turn` — deterministic multilingual demo extraction.
- `llm/pydantic_ai_interpreter.py::PydanticAIInterpreter.__init__`, `interpret_turn` — optional Pydantic AI structured output.
- `persistence/memory.py::InMemorySessionRepository.load`, `save` — deep-copied in-memory sessions.
- `persistence/json_file.py::JsonFileSessionRepository.load`, `save` — Pydantic JSON session files.
- `logging/jsonl_audit.py::JsonlAuditSink.append` — append serialized audit event plus newline.

The mock Forge is executable reference behavior, not a production transport adapter. File persistence and audit perform direct filesystem writes and provide no cross-process locking.

