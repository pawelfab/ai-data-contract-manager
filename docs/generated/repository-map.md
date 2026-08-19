# Generated repository map

Generated: `2026-08-19T14:42:07.088026+00:00`

> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.

Source files indexed: **24**

## `ai-data-contract-manager/`

### `ai-data-contract-manager/pyproject.toml`
- Language: TOML
- Lines: 46
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/__init__.py`
- Language: Python
- Lines: 4
- Symbols: none extracted

### `ai-data-contract-manager/src/adcm/api.py`
- Language: Python
- Lines: 83
- Symbols:
  - `class MessageRequest` — line 14
  - `function create_app` — line 18
  - `function main` — line 69

### `ai-data-contract-manager/src/adcm/cli.py`
- Language: Python
- Lines: 65
- Symbols:
  - `function _read_answer` — line 11
  - `async_function run` — line 24
  - `function main` — line 56

### `ai-data-contract-manager/src/adcm/gateway.py`
- Language: Python
- Lines: 92
- Symbols:
  - `class ForgeGateway` — line 10
    - `async start_session` — line 12
    - `async get_state` — line 15
    - `async submit_values` — line 18
    - `async __aenter__` — line 20
    - `async __aexit__` — line 23
  - `class MCPForgeGateway` — line 27
    - `__init__` — line 34
    - `async __aenter__` — line 42
    - `async __aexit__` — line 48
    - `async start_session` — line 54
    - `async get_state` — line 58
    - `async submit_values` — line 62
    - `_normalize` — line 70

### `ai-data-contract-manager/src/adcm/heuristics.py`
- Language: Python
- Lines: 189
- Symbols:
  - `function _ascii` — line 18
  - `function slugify_identifier` — line 22
  - `class HeuristicResolver` — line 31
    - `extract` — line 34
    - `_for_requirement` — line 49
    - `_fuzzy_choice` — line 112
    - `_parse_columns` — line 128
    - `_parse_regular_line` — line 161
    - `_parse_fixed_width_line` — line 175

### `ai-data-contract-manager/src/adcm/model_factory.py`
- Language: Python
- Lines: 54
- Symbols:
  - `function _openai_model_name` — line 8
  - `function build_pydantic_ai_model` — line 15

### `ai-data-contract-manager/src/adcm/models.py`
- Language: Python
- Lines: 79
- Symbols:
  - `class Origin` — line 8
  - `class Requirement` — line 19
  - `class ValidationIssue` — line 28
  - `class AppliedValue` — line 34
  - `class RuleIssue` — line 41
  - `class ForgeState` — line 47
  - `class AssistantTurn` — line 61
  - `class ChatMessage` — line 70
  - `class ConversationMemory` — line 75

### `ai-data-contract-manager/src/adcm/orchestrator.py`
- Language: Python
- Lines: 155
- Symbols:
  - `class ADCMOrchestrator` — line 12
    - `__init__` — line 15
    - `async start` — line 28
    - `async message` — line 37
    - `async state` — line 114
    - `_semantic_prefix` — line 119
    - `_turn_from_state` — line 129

### `ai-data-contract-manager/src/adcm/runtime.py`
- Language: Python
- Lines: 42
- Symbols:
  - `function build_gateway` — line 14
  - `function build_semantic` — line 19
  - `function build_orchestrator` — line 26

### `ai-data-contract-manager/src/adcm/semantic.py`
- Language: Python
- Lines: 110
- Symbols:
  - `class CandidateValue` — line 12
  - `class ExtractionResult` — line 19
  - `class SemanticResolver` — line 23
    - `async extract_from_history` — line 25
    - `async close` — line 33
  - `class NoopSemanticResolver` — line 37
    - `async extract_from_history` — line 38
  - `class PydanticAISemanticResolver` — line 42
    - `__init__` — line 45
    - `async close` — line 67
    - `async extract_from_history` — line 76

### `ai-data-contract-manager/src/adcm/settings.py`
- Language: Python
- Lines: 84
- Symbols:
  - `class ADCMSettings` — line 14
    - `resolved_llm_provider` — line 36
    - `semantic_model_name` — line 46
    - `public_runtime_summary` — line 51
    - `validate_enabled_llm` — line 61
  - `function project_root` — line 76
  - `function load_settings` — line 80

## `mcp-servers/`

### `mcp-servers/mcp-contract-forge/config/contract.json`
- Language: JSON
- Lines: 1860
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/config/ux_rules_contract_v1.json`
- Language: JSON
- Lines: 153
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/config/ux_rules_original.json`
- Language: JSON
- Lines: 455
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/contracts/data-contract.schema.json`
- Language: JSON
- Lines: 1640
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/pyproject.toml`
- Language: TOML
- Lines: 31
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/__init__.py`
- Language: Python
- Lines: 5
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/src/contract_forge/engine.py`
- Language: Python
- Lines: 200
- Symbols:
  - `class ContractForge` — line 17
    - `__init__` — line 26
    - `from_files` — line 33
    - `list_source_systems` — line 38
    - `start_session` — line 44
    - `submit_values` — line 49
    - `get_state` — line 65
    - `_apply_explicit` — line 70
    - `_advance` — line 101
    - `_pending` — line 131
    - `_source_type_choices` — line 162
    - `_state` — line 169
    - `_get` — line 195

### `mcp-servers/mcp-contract-forge/src/contract_forge/mcp_server.py`
- Language: Python
- Lines: 85
- Symbols:
  - `function _root` — line 13
  - `function _service_path` — line 17
  - `function build_forge` — line 23
  - `function create_server` — line 34
  - `function main` — line 79

### `mcp-servers/mcp-contract-forge/src/contract_forge/models.py`
- Language: Python
- Lines: 73
- Symbols:
  - `class Origin` — line 8
  - `class Requirement` — line 27
  - `class ValidationIssue` — line 36
  - `class AppliedValue` — line 42
  - `class RuleIssue` — line 49
  - `class ForgeState` — line 55
  - `class SessionData` — line 67

### `mcp-servers/mcp-contract-forge/src/contract_forge/path_utils.py`
- Language: Python
- Lines: 61
- Symbols:
  - `function split_path` — line 9
  - `function get_path` — line 13
  - `function has_path` — line 27
  - `function set_path` — line 35
  - `function delete_path` — line 50

### `mcp-servers/mcp-contract-forge/src/contract_forge/rules.py`
- Language: Python
- Lines: 184
- Symbols:
  - `class RuleEngine` — line 14
    - `__init__` — line 15
    - `systems` — line 21
    - `source_types` — line 24
    - `input_mode` — line 27
    - `apply_system_source_type` — line 35
    - `apply_pass` — line 48
    - `_apply_rule` — line 72
    - `_condition_matches` — line 147
    - `_render` — line 157
    - `_transform` — line 165
    - `_set` — line 173

### `mcp-servers/mcp-contract-forge/src/contract_forge/schema.py`
- Language: Python
- Lines: 262
- Symbols:
  - `class SchemaNavigator` — line 12
    - `__init__` — line 21
    - `resolve_ref` — line 25
    - `active_node` — line 40
    - `schema_at_path` — line 57
    - `path_exists_in_schema` — line 76
    - `source_type_values` — line 79
    - `inject_defaults` — line 94
    - `ensure_required_containers` — line 119
    - `missing_requirements` — line 141
    - `_walk_array` — line 194
    - `_walk_object_item` — line 204
    - `_dedupe` — line 222
    - `public_schema` — line 232
    - `allowed_values` — line 237
    - `validate_value` — line 245
    - `validate` — line 256
