# Generated repository map

Source snapshot: `280079b7d2dcc13b70dd0ad4322adf54b727a9d9132bbd2e369b5afc6480983f`

> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.

Source files indexed: **54**

## `ai-data-contract-manager/`

### `ai-data-contract-manager/pyproject.toml`
- Language: TOML
- Lines: 30
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
- Lines: 85
- Symbols:
  - `class TurnRequest` — line 22
  - `function _build_intent_resolver` — line 29
  - `async_function health` — line 70
  - `async_function turn` — line 75
  - `async_function get_session` — line 83

### `ai-data-contract-manager/src/adcm/adapters/forge_mcp.py`
- Language: Python
- Lines: 27
- Symbols:
  - `class ForgeMcpAdapter` — line 6
    - `__init__` — line 7
    - `async analyze` — line 10
    - `async describe` — line 19

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
- Lines: 41
- Symbols:
  - `class CandidatePolicy` — line 8
    - `__init__` — line 9
    - `decide` — line 12

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

### `ai-data-contract-manager/src/adcm/application/proposal_reconciler.py`
- Language: Python
- Lines: 103
- Symbols:
  - `class ProposalConflict` — line 11
  - `class ProposalReconciler` — line 15
    - `reconcile` — line 23
    - `_winner` — line 87

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
- Lines: 101
- Symbols:
  - `class StabilizationEngine` — line 15
    - `__init__` — line 16
    - `async stabilize` — line 31
    - `_forge_proposals` — line 66
    - `_foreign_cleanup_commands` — line 88

### `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- Language: Python
- Lines: 80
- Symbols:
  - `class TurnOrchestrator` — line 15
    - `__init__` — line 16
    - `async run_turn` — line 39

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
- Lines: 32
- Symbols:
  - `class IntentResolution` — line 8
  - `class StabilizationReport` — line 14
  - `class TurnOutcome` — line 22

### `ai-data-contract-manager/src/adcm/ports/__init__.py`
- Language: Python
- Lines: 0
- Symbols: none extracted

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
- Lines: 28
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

### `mcp-servers/mcp-contract-forge/src/contract_forge/ports/definition_repository.py`
- Language: Python
- Lines: 8
- Symbols:
  - `class ContractDefinitionPort` — line 6
    - `load` — line 7

### `mcp-servers/mcp-contract-forge/src/contract_forge/server.py`
- Language: Python
- Lines: 41
- Symbols:
  - `function contract_analyze` — line 22
  - `function contract_describe` — line 28
  - `async_function health` — line 34
