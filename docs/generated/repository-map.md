# Generated repository map

Source snapshot: `7a48e619d173ace4fd5569044d1b27f3f861f2e0a8ac8cc0f1111cb236a44e2d`

> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.

Source files indexed: **77**

## `ai-data-contract-manager/`

### `ai-data-contract-manager/pyproject.toml`
- Language: TOML
- Lines: 32
- Symbols: none extracted

### `ai-data-contract-manager/resources/ux_rules.json`
- Language: JSON
- Lines: 56
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/adapters/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/adapters/api/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/adapters/api/app.py`
- Language: Python
- Lines: 179
- Symbols:
  - `class TurnRequest` — line 32
  - `function _build_observability` — line 37
  - `function _build_intent_resolver` — line 75
  - `async_function lifespan` — line 117
  - `async_function application_log_middleware` — line 127
  - `async_function health` — line 160
  - `async_function turn` — line 165
  - `async_function get_session` — line 177

### `ai-data-contract-manager/src/adcm/adapters/forge_mcp.py`
- Language: Python
- Lines: 81
- Symbols:
  - `class ForgeMcpAdapter` — line 9
    - `__init__` — line 10
    - `async analyze` — line 14
    - `async describe` — line 45
    - `_info` — line 68
    - `_error` — line 72

### `ai-data-contract-manager/src/adcm/adapters/intent_heuristic.py`
- Language: Python
- Lines: 58
- Symbols:
  - `class HeuristicIntentResolver` — line 14
    - `async resolve` — line 17
    - `_parse_value` — line 52

### `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- Language: Python
- Lines: 26
- Symbols:
  - `class PydanticAIIntentResolver` — line 9
    - `__init__` — line 10
    - `async resolve` — line 21

### `ai-data-contract-manager/src/adcm/adapters/logging/__init__.py`
- Language: Python
- Lines: 3
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/adapters/logging/bigquery_app_log_sink.py`
- Language: Python
- Lines: 24
- Symbols:
  - `class BigQueryAppLogSink` — line 7
    - `__init__` — line 8
    - `_client` — line 13
    - `emit` — line 19

### `ai-data-contract-manager/src/adcm/adapters/logging/bigquery_session_audit_sink.py`
- Language: Python
- Lines: 41
- Symbols:
  - `class BatchInsertError` — line 9
    - `__init__` — line 10
  - `class BigQuerySessionAuditSink` — line 15
    - `__init__` — line 16
    - `_client` — line 23
    - `emit` — line 29

### `ai-data-contract-manager/src/adcm/adapters/logging/local_app_log_sink.py`
- Language: Python
- Lines: 24
- Symbols:
  - `class LocalAppLogSink` — line 12
    - `__init__` — line 13
    - `emit` — line 16

### `ai-data-contract-manager/src/adcm/adapters/logging/local_session_audit_sink.py`
- Language: Python
- Lines: 28
- Symbols:
  - `class LocalSessionAuditSink` — line 13
    - `__init__` — line 14
    - `emit` — line 17

### `ai-data-contract-manager/src/adcm/adapters/logging/sanitizer.py`
- Language: Python
- Lines: 4
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/adapters/response_basic.py`
- Language: Python
- Lines: 21
- Symbols:
  - `class BasicResponseComposer` — line 6
    - `async compose` — line 7

### `ai-data-contract-manager/src/adcm/adapters/rules_file.py`
- Language: Python
- Lines: 15
- Symbols:
  - `class FileRulesRepository` — line 7
    - `__init__` — line 8
    - `async load` — line 11

### `ai-data-contract-manager/src/adcm/adapters/session_memory.py`
- Language: Python
- Lines: 21
- Symbols:
  - `class InMemorySessionRepository` — line 7
    - `__init__` — line 8
    - `async get_or_create` — line 12
    - `async save` — line 18

### `ai-data-contract-manager/src/adcm/application/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/application/candidate_policy.py`
- Language: Python
- Lines: 101
- Symbols:
  - `class CandidateDisposition` — line 12
  - `class CandidateDecision` — line 18
  - `class CandidatePolicyResult` — line 27
  - `class CandidatePolicy` — line 34
    - `__init__` — line 35
    - `decide` — line 38
    - `evaluate` — line 42

### `ai-data-contract-manager/src/adcm/application/document_engine.py`
- Language: Python
- Lines: 135
- Symbols:
  - `class DocumentEngine` — line 10
    - `apply` — line 11
    - `_apply_one` — line 19
    - `_add` — line 72
    - `_replace` — line 89
    - `_remove` — line 105
    - `_prune_empty_ancestors` — line 117
    - `_drop_provenance_at_or_below` — line 131

### `ai-data-contract-manager/src/adcm/application/external_check_coordinator.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class ExternalCheckCoordinator` — line 4
    - `async run` — line 7

### `ai-data-contract-manager/src/adcm/application/json_pointer.py`
- Language: Python
- Lines: 73
- Symbols:
  - `class JsonPointerError` — line 6
  - `function _tokens` — line 10
  - `function _index` — line 18
  - `function get` — line 30
  - `function exists` — line 47
  - `function parent_and_token` — line 55

### `ai-data-contract-manager/src/adcm/application/observability/__init__.py`
- Language: Python
- Lines: 3
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/application/observability/app_log_recorder.py`
- Language: Python
- Lines: 35
- Symbols:
  - `class AppLogRecorder` — line 12
    - `__init__` — line 13
    - `emit` — line 16
    - `info` — line 30
    - `error` — line 33

### `ai-data-contract-manager/src/adcm/application/observability/audit_views.py`
- Language: Python
- Lines: 106
- Symbols:
  - `function forge_analysis_completed_view` — line 20
  - `function turn_completed_view` — line 65
  - `function _missing_view` — line 94

### `ai-data-contract-manager/src/adcm/application/observability/models.py`
- Language: Python
- Lines: 54
- Symbols:
  - `function utc_now` — line 8
  - `class AppLogEvent` — line 12
    - `timestamp_is_utc` — line 31
  - `class SessionAuditEvent` — line 37
    - `timestamp_is_utc` — line 50

### `ai-data-contract-manager/src/adcm/application/observability/sanitizer.py`
- Language: Python
- Lines: 50
- Symbols:
  - `function _is_secret_key` — line 29
  - `function sanitize` — line 39

### `ai-data-contract-manager/src/adcm/application/observability/session_audit_recorder.py`
- Language: Python
- Lines: 79
- Symbols:
  - `class BoundTurnAuditRecorder` — line 9
    - `__init__` — line 10
    - `level` — line 14
    - `emit` — line 18
    - `record` — line 23
    - `__getattr__` — line 27
  - `class SessionAuditRecorder` — line 34
    - `__init__` — line 35
    - `bind` — line 40
    - `_emit` — line 43
  - `function _dump` — line 56

### `ai-data-contract-manager/src/adcm/application/proposal_reconciler.py`
- Language: Python
- Lines: 129
- Symbols:
  - `class ProposalConflict` — line 11
  - `class ProposalReconciler` — line 15
    - `reconcile` — line 23
    - `_losing_decisions` — line 102
    - `_winner` — line 113

### `ai-data-contract-manager/src/adcm/application/rules_engine.py`
- Language: Python
- Lines: 106
- Symbols:
  - `class ConventionRulesEngine` — line 15
    - `evaluate` — line 16
    - `_conditions_match` — line 43
    - `_condition_matches` — line 49
    - `_render_value` — line 76
    - `_condition_dependencies` — line 94
    - `_read_optional` — line 101

### `ai-data-contract-manager/src/adcm/application/stabilization_engine.py`
- Language: Python
- Lines: 247
- Symbols:
  - `class StabilizationEngine` — line 23
    - `__init__` — line 24
    - `async stabilize` — line 39
    - `async _analyze` — line 147
    - `_record_mutations` — line 181
    - `_record_proposal_decisions` — line 186
    - `_record` — line 207
    - `_forge_proposals` — line 212
    - `_foreign_cleanup_commands` — line 234

### `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- Language: Python
- Lines: 206
- Symbols:
  - `class TurnOrchestrator` — line 21
    - `__init__` — line 22
    - `async run_turn` — line 49
    - `_audit` — line 199
    - `_app_info` — line 203

### `ai-data-contract-manager/src/adcm/domain/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/domain/common.py`
- Language: Python
- Lines: 5
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/domain/contract.py`
- Language: Python
- Lines: 20
- Symbols:
  - `class ContractState` — line 10
    - `snapshot_document` — line 18

### `ai-data-contract-manager/src/adcm/domain/external.py`
- Language: Python
- Lines: 18
- Symbols:
  - `class CheckState` — line 6
  - `class ExternalChecksStatus` — line 12

### `ai-data-contract-manager/src/adcm/domain/forge.py`
- Language: Python
- Lines: 87
- Symbols:
  - `class WritableTarget` — line 6
  - `class MissingRequirement` — line 17
  - `class ForeignLocation` — line 26
  - `class ForgeProposal` — line 33
  - `class Diagnostic` — line 44
  - `class ContractStatus` — line 53
  - `class ForgeAnalysis` — line 60
  - `class FieldDescriptor` — line 72
  - `class ForgeDescription` — line 82

### `ai-data-contract-manager/src/adcm/domain/mutations.py`
- Language: Python
- Lines: 60
- Symbols:
  - `class CandidateAction` — line 10
  - `class MutationOperation` — line 15
  - `class MutationCandidate` — line 21
  - `class MutationCommand` — line 32
  - `class MutationEvent` — line 45

### `ai-data-contract-manager/src/adcm/domain/proposals.py`
- Language: Python
- Lines: 43
- Symbols:
  - `class ProposalMode` — line 9
  - `class ProposalAction` — line 14
  - `class Proposal` — line 21
  - `class ProposalDecision` — line 36

### `ai-data-contract-manager/src/adcm/domain/provenance.py`
- Language: Python
- Lines: 32
- Symbols:
  - `class ValueSource` — line 6
  - `class ValueProvenance` — line 25

### `ai-data-contract-manager/src/adcm/domain/rules.py`
- Language: Python
- Lines: 47
- Symbols:
  - `class RuleScope` — line 7
  - `class RuleCondition` — line 13
    - `path_is_pointer` — line 23
  - `class ConventionRule` — line 29
  - `class RulesDocument` — line 41

### `ai-data-contract-manager/src/adcm/domain/session.py`
- Language: Python
- Lines: 20
- Symbols:
  - `class TurnSnapshot` — line 6
  - `class SessionState` — line 13

### `ai-data-contract-manager/src/adcm/domain/turn.py`
- Language: Python
- Lines: 35
- Symbols:
  - `class IntentResolution` — line 10
  - `class StabilizationReport` — line 17
  - `class TurnOutcome` — line 25

### `ai-data-contract-manager/src/adcm/ports/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/ports/app_log_sink.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class AppLogSinkPort` — line 6
    - `emit` — line 7

### `ai-data-contract-manager/src/adcm/ports/forge.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class ContractForgePort` — line 6
    - `async analyze` — line 7
    - `async describe` — line 8

### `ai-data-contract-manager/src/adcm/ports/intent.py`
- Language: Python
- Lines: 15
- Symbols:
  - `class IntentResolverPort` — line 7
    - `async resolve` — line 8

### `ai-data-contract-manager/src/adcm/ports/response.py`
- Language: Python
- Lines: 8
- Symbols:
  - `class ResponseComposerPort` — line 6
    - `async compose` — line 7

### `ai-data-contract-manager/src/adcm/ports/rules_repository.py`
- Language: Python
- Lines: 8
- Symbols:
  - `class RulesRepositoryPort` — line 6
    - `async load` — line 7

### `ai-data-contract-manager/src/adcm/ports/session_audit_sink.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class SessionAuditSinkPort` — line 6
    - `emit` — line 7

### `ai-data-contract-manager/src/adcm/ports/session_repository.py`
- Language: Python
- Lines: 9
- Symbols:
  - `class SessionRepositoryPort` — line 6
    - `async get_or_create` — line 7
    - `async save` — line 8

## `mcp-servers/`

### `mcp-servers/mcp-contract-forge/pyproject.toml`
- Language: TOML
- Lines: 30
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/resources/contract.json`
- Language: JSON
- Lines: 64
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/file_definition.py`
- Language: Python
- Lines: 18
- Symbols:
  - `class FileContractDefinitionRepository` — line 8
    - `__init__` — line 11
    - `load` — line 15

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/__init__.py`
- Language: Python
- Lines: 2
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/bigquery_app_log_sink.py`
- Language: Python
- Lines: 28
- Symbols:
  - `class BigQueryAppLogSink` — line 8
    - `__init__` — line 11
    - `_client` — line 14
    - `to_row` — line 21
    - `emit` — line 24

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/local_app_log_sink.py`
- Language: Python
- Lines: 27
- Symbols:
  - `class LocalAppLogSink` — line 14
    - `__init__` — line 15
    - `emit` — line 18

### `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/sanitizer.py`
- Language: Python
- Lines: 6
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/analyzer.py`
- Language: Python
- Lines: 230
- Symbols:
  - `class ContractAnalyzer` — line 24
    - `__init__` — line 25
    - `analyze` — line 28
    - `_missing` — line 53
    - `_missing_for_absent_required` — line 71
    - `_foreign` — line 90
    - `_diagnostics` — line 115
    - `_writable` — line 131
    - `_default_proposals` — line 154
    - `_enrichment_proposals` — line 179
    - `_when_matches` — line 202
    - `_render` — line 215

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/definition_normalizer.py`
- Language: Python
- Lines: 20
- Symbols:
  - `class ContractDefinitionNormalizer` — line 6
    - `normalize` — line 13

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/describer.py`
- Language: Python
- Lines: 37
- Symbols:
  - `class ContractDescriber` — line 7
    - `__init__` — line 8
    - `describe` — line 11
    - `_fields` — line 16

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/__init__.py`
- Language: Python
- Lines: 7
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/app_log_recorder.py`
- Language: Python
- Lines: 45
- Symbols:
  - `class AppLogRecorder` — line 13
    - `__init__` — line 16
    - `emit` — line 20
    - `info` — line 40
    - `error` — line 43

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/models.py`
- Language: Python
- Lines: 36
- Symbols:
  - `class AppLogEvent` — line 8
    - `timestamp_is_utc` — line 27
    - `event_type` — line 33

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/sanitizer.py`
- Language: Python
- Lines: 50
- Symbols:
  - `function _is_secret_key` — line 29
  - `function sanitize` — line 39

### `mcp-servers/mcp-contract-forge/src/contract_forge/application/schema_utils.py`
- Language: Python
- Lines: 47
- Symbols:
  - `function escape_token` — line 6
  - `function join_pointer` — line 10
  - `function resolve_ref` — line 14
  - `function pointer_get` — line 28
  - `function pointer_exists` — line 41

### `mcp-servers/mcp-contract-forge/src/contract_forge/domain/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/domain/definition.py`
- Language: Python
- Lines: 13
- Symbols:
  - `class ContractDefinition` — line 6

### `mcp-servers/mcp-contract-forge/src/contract_forge/domain/protocol.py`
- Language: Python
- Lines: 89
- Symbols:
  - `class WritableTarget` — line 8
  - `class MissingRequirement` — line 19
  - `class ForeignLocation` — line 28
  - `class ForgeProposal` — line 35
  - `class Diagnostic` — line 46
  - `class ContractStatus` — line 55
  - `class ForgeAnalysis` — line 62
  - `class FieldDescriptor` — line 74
  - `class ForgeDescription` — line 84

### `mcp-servers/mcp-contract-forge/src/contract_forge/ports/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/ports/app_log_sink.py`
- Language: Python
- Lines: 8
- Symbols:
  - `class AppLogSinkPort` — line 6
    - `emit` — line 7

### `mcp-servers/mcp-contract-forge/src/contract_forge/ports/definition_repository.py`
- Language: Python
- Lines: 8
- Symbols:
  - `class ContractDefinitionPort` — line 6
    - `load` — line 7

### `mcp-servers/mcp-contract-forge/src/contract_forge/server.py`
- Language: Python
- Lines: 89
- Symbols:
  - `function _build_app_log_recorder` — line 18
  - `function contract_analyze` — line 44
  - `function contract_describe` — line 64
  - `async_function health` — line 82
