# Generated repository map

Generated: `2026-08-19T10:50:56.485088+00:00`

> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.

Source files indexed: **37**

## `contracts/`

### `contracts/contract.json`
- Language: JSON
- Lines: 1860
- Symbols: none extracted

### `contracts/ux_rules.json`
- Language: JSON
- Lines: 111
- Symbols: none extracted

## `examples/`

### `examples/contract-rules.json`
- Language: JSON
- Lines: 159
- Symbols: none extracted

## `pyproject.toml/`

### `pyproject.toml`
- Language: TOML
- Lines: 30
- Symbols: none extracted

## `src/`

### `src/adcm/__init__.py`
- Language: Python
- Lines: 2
- Symbols: none extracted

### `src/adcm/adapters/llm/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/adapters/llm/pydantic_ai_interpreter.py`
- Language: Python
- Lines: 49
- Symbols:
  - `class PydanticAIInterpreter` — line 34
    - `__init__` — line 35
    - `async interpret_turn` — line 40

### `src/adcm/adapters/llm/rule_based_interpreter.py`
- Language: Python
- Lines: 38
- Symbols:
  - `function _ascii_fold` — line 8
  - `class RuleBasedInterpreter` — line 12
    - `async interpret_turn` — line 13

### `src/adcm/adapters/logging/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/adapters/logging/jsonl_audit.py`
- Language: Python
- Lines: 13
- Symbols:
  - `class JsonlAuditSink` — line 5
    - `__init__` — line 6
    - `async append` — line 10

### `src/adcm/adapters/mcp/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/adapters/mcp/mock_contract_forge.py`
- Language: Python
- Lines: 195
- Symbols:
  - `class MockContractForgeAdapter` — line 27
    - `_value` — line 31
    - `_check_revision` — line 34
    - `_base_paths` — line 41
    - `async evaluate_draft` — line 44
    - `async validate_final` — line 176
    - `async render_yaml` — line 188

### `src/adcm/adapters/persistence/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/adapters/persistence/json_file.py`
- Language: Python
- Lines: 24
- Symbols:
  - `class JsonFileSessionRepository` — line 6
    - `__init__` — line 7
    - `_path` — line 11
    - `async load` — line 14
    - `async save` — line 20

### `src/adcm/adapters/persistence/memory.py`
- Language: Python
- Lines: 16
- Symbols:
  - `class InMemorySessionRepository` — line 6
    - `__init__` — line 7
    - `async load` — line 10
    - `async save` — line 14

### `src/adcm/api/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/application/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/application/candidate_resolver.py`
- Language: Python
- Lines: 73
- Symbols:
  - `class CandidateResolver` — line 7
    - `_preflight` — line 11
    - `_rank` — line 22
    - `resolve` — line 35

### `src/adcm/application/capability_router.py`
- Language: Python
- Lines: 20
- Symbols:
  - `class CapabilityRouter` — line 4
    - `__init__` — line 5
    - `register` — line 8
    - `can_execute` — line 11
    - `async execute` — line 14

### `src/adcm/application/chat_service.py`
- Language: Python
- Lines: 37
- Symbols:
  - `class ChatService` — line 11
    - `__init__` — line 12
    - `async handle_user_message` — line 24

### `src/adcm/application/context_builder.py`
- Language: Python
- Lines: 25
- Symbols:
  - `class AgentContextBuilder` — line 4
    - `build` — line 5

### `src/adcm/application/draft_projector.py`
- Language: Python
- Lines: 19
- Symbols:
  - `class DraftProjector` — line 5
    - `project` — line 8

### `src/adcm/application/preference_expander.py`
- Language: Python
- Lines: 36
- Symbols:
  - `class PreferenceExpander` — line 5
    - `expand` — line 8

### `src/adcm/application/render_service.py`
- Language: Python
- Lines: 57
- Symbols:
  - `class RenderCacheKey` — line 17
  - `class ContractRenderService` — line 23
    - `__init__` — line 26
    - `async render` — line 30

### `src/adcm/application/signal_binder.py`
- Language: Python
- Lines: 42
- Symbols:
  - `class SignalBinder` — line 5
    - `bind` — line 8

### `src/adcm/application/turn_processor.py`
- Language: Python
- Lines: 116
- Symbols:
  - `class TurnProcessor` — line 15
    - `apply_user_turn` — line 18

### `src/adcm/application/workflow_runner.py`
- Language: Python
- Lines: 290
- Symbols:
  - `class WorkflowRunner` — line 27
    - `__init__` — line 30
    - `_candidate_key` — line 45
    - `_append_unique_candidates` — line 56
    - `_convert_external_candidate` — line 70
    - `async _resolve_capabilities` — line 99
    - `async run_until_stable` — line 135
    - `async run` — line 287

### `src/adcm/config.py`
- Language: Python
- Lines: 48
- Symbols:
  - `class Settings` — line 9
    - `validate_contract_forge_selection` — line 18

### `src/adcm/domain/__init__.py`
- Language: Python
- Lines: 2
- Symbols: none extracted

### `src/adcm/domain/contract_path.py`
- Language: Python
- Lines: 100
- Symbols:
  - `class PathToken` — line 11
  - `class ContractPath` — line 16
    - `parse` — line 20
    - `write` — line 50
    - `read` — line 88

### `src/adcm/domain/models.py`
- Language: Python
- Lines: 498
- Symbols:
  - `function utcnow` — line 15
  - `function _canonical_json` — line 19
  - `class EvidenceKind` — line 29
  - `class ValueOrigin` — line 41
  - `class CandidateScope` — line 66
  - `class Evidence` — line 75
  - `class Signal` — line 85
    - `require_user_evidence` — line 97
  - `class Preference` — line 103
    - `require_user_evidence` — line 114
  - `class ValueCandidate` — line 120
    - `require_user_evidence` — line 138
    - `effective_priority` — line 146
  - `class ResolvedValue` — line 150
  - `class ContractDraft` — line 158
    - `canonical_hash` — line 162
  - `class AllowedPath` — line 167
  - `class Requirement` — line 174
  - `class CapabilityStatus` — line 180
  - `class CapabilityRequest` — line 186
  - `class CapabilityResult` — line 193
  - `class ValidationFindingStatus` — line 201
  - `class DependencyType` — line 207
  - `class ValidationDependency` — line 213
  - `class ValidationFinding` — line 220
  - `class ExternalCandidate` — line 227
  - `class EvaluationStatus` — line 238
  - `class FinalValidationStatus` — line 244
  - `class RenderMode` — line 250
  - `class CurrentSchemaView` — line 255
    - `allowed_path_set` — line 261
    - `_schema_pattern` — line 265
    - `is_path_allowed` — line 270
  - `class ContractInput` — line 280
  - `class ContractEvaluationResult` — line 286
  - `class FinalValidationResult` — line 295
  - `class FinalValidationReceipt` — line 302
  - `class RenderRequest` — line 308
  - `class RenderedContract` — line 314
  - `class WorkflowOutcomeStatus` — line 320
  - `class WorkflowOutcome` — line 328
  - `class WorkflowState` — line 338
  - `class ValueChange` — line 346
  - `class Revision` — line 354
  - `class AuditEvent` — line 361
  - `class ChatMessage` — line 370
  - `class ExtractedSignal` — line 377
  - `class ExtractedPreference` — line 384
  - `class CorrectionIntent` — line 391
  - `class PossibleTypo` — line 398
  - `class TurnInterpretation` — line 405
  - `class ConversationState` — line 413
    - `resolved_values_reference_known_candidates` — line 429
  - `class SignalView` — line 476
  - `class PreferenceView` — line 483
  - `class AgentContext` — line 490

### `src/adcm/ports/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `src/adcm/ports/audit_sink.py`
- Language: Python
- Lines: 7
- Symbols:
  - `class AuditSinkPort` — line 5
    - `async append` — line 6

### `src/adcm/ports/capability.py`
- Language: Python
- Lines: 6
- Symbols:
  - `class CapabilityHandlerPort` — line 4
    - `async execute` — line 5

### `src/adcm/ports/contract_forge.py`
- Language: Python
- Lines: 18
- Symbols:
  - `class ContractForgePort` — line 12
    - `async evaluate_draft` — line 13
    - `async validate_final` — line 15
    - `async render_yaml` — line 17

### `src/adcm/ports/semantic_interpreter.py`
- Language: Python
- Lines: 7
- Symbols:
  - `class SemanticInterpreterPort` — line 5
    - `async interpret_turn` — line 6

### `src/adcm/ports/session_repository.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class SessionRepositoryPort` — line 6
    - `async load` — line 7
    - `async save` — line 8
