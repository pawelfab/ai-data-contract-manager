# Generated repository map

Generated: `2026-08-19T06:50:56.505257+00:00`

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
- Lines: 39
- Symbols:
  - `class CandidateResolver` — line 6
    - `_rank` — line 10
    - `resolve` — line 20

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
- Lines: 31
- Symbols:
  - `class PreferenceExpander` — line 4
    - `expand` — line 7

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
- Lines: 36
- Symbols:
  - `class SignalBinder` — line 4
    - `bind` — line 7

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
- Lines: 76
- Symbols:
  - `class PathToken` — line 11
  - `class ContractPath` — line 16
    - `parse` — line 20
    - `write` — line 30
    - `read` — line 64

### `src/adcm/domain/models.py`
- Language: Python
- Lines: 432
- Symbols:
  - `function utcnow` — line 13
  - `class EvidenceKind` — line 17
  - `class ValueOrigin` — line 29
  - `class CandidateScope` — line 54
  - `class Evidence` — line 63
  - `class Signal` — line 73
    - `require_user_evidence` — line 85
  - `class Preference` — line 91
    - `require_user_evidence` — line 102
  - `class ValueCandidate` — line 108
    - `require_user_evidence` — line 126
    - `effective_priority` — line 131
  - `class ResolvedValue` — line 135
  - `class ContractDraft` — line 143
    - `canonical_hash` — line 147
  - `class AllowedPath` — line 152
  - `class Requirement` — line 159
  - `class CapabilityStatus` — line 165
  - `class CapabilityRequest` — line 171
  - `class CapabilityResult` — line 178
  - `class ValidationFindingStatus` — line 186
  - `class DependencyType` — line 192
  - `class ValidationDependency` — line 198
  - `class ValidationFinding` — line 205
  - `class ExternalCandidate` — line 212
  - `class EvaluationStatus` — line 223
  - `class FinalValidationStatus` — line 229
  - `class RenderMode` — line 235
  - `class CurrentSchemaView` — line 240
    - `allowed_path_set` — line 246
    - `_schema_pattern` — line 250
    - `is_path_allowed` — line 255
  - `class ContractInput` — line 261
  - `class ContractEvaluationResult` — line 267
  - `class FinalValidationResult` — line 276
  - `class FinalValidationReceipt` — line 283
  - `class RenderRequest` — line 289
  - `class RenderedContract` — line 295
  - `class WorkflowOutcomeStatus` — line 301
  - `class WorkflowOutcome` — line 309
  - `class WorkflowState` — line 319
  - `class ValueChange` — line 327
  - `class Revision` — line 335
  - `class AuditEvent` — line 342
  - `class ChatMessage` — line 351
  - `class ExtractedSignal` — line 358
  - `class ExtractedPreference` — line 365
  - `class CorrectionIntent` — line 372
  - `class PossibleTypo` — line 379
  - `class TurnInterpretation` — line 386
  - `class ConversationState` — line 394
  - `class SignalView` — line 410
  - `class PreferenceView` — line 417
  - `class AgentContext` — line 424

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
