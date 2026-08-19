# Generated repository map

Generated: `2026-08-19T18:43:45.131729+00:00`

> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.

Source files indexed: **23**

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
- Lines: 78
- Symbols:
  - `function _uses_multiline_input` — line 12
  - `function _read_answer` — line 24
  - `async_function run` — line 37
  - `function main` — line 69

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
- Lines: 693
- Symbols:
  - `function _ascii` — line 15
  - `function slugify_identifier` — line 23
  - `class StructuredParseResult` — line 33
    - `complete` — line 39
  - `class SpecializedResolver` — line 43
    - `resolve` — line 44
  - `class LabeledContractFieldResolver` — line 53
    - `resolve` — line 56
  - `class HeuristicResolver` — line 100
    - `__init__` — line 103
    - `extract` — line 113
    - `parse_structured` — line 141
    - `merge_structured` — line 175
    - `_for_requirement` — line 211
    - `supports` — line 262
    - `_schema_choices` — line 266
    - `_explicit_json_value` — line 275
    - `_direct_custom_choice` — line 282
    - `_boolean_value` — line 287
    - `_integer_value` — line 296
    - `_number_value` — line 303
    - `_within_numeric_bounds` — line 320
    - `_string_value` — line 329
    - `_valid_string` — line 386
    - `_array_object_item_schema` — line 402
    - `_decode_json_records` — line 418
    - `_parse_text_record` — line 434
    - `_find_token` — line 491
    - `_evaluate_records` — line 524
    - `_normalize_property` — line 563
    - `_identity_property` — line 600
    - `_record_label` — line 612
    - `_same_identity` — line 622
    - `_combine_results` — line 628
    - `_dedupe_strings` — line 646
    - `_unambiguous_pattern_candidate` — line 650
    - `_fuzzy_choice` — line 671

### `ai-data-contract-manager/src/adcm/model_factory.py`
- Language: Python
- Lines: 54
- Symbols:
  - `function _openai_model_name` — line 8
  - `function build_pydantic_ai_model` — line 15

### `ai-data-contract-manager/src/adcm/models.py`
- Language: Python
- Lines: 154
- Symbols:
  - `class Origin` — line 8
  - `class ExtractionMethod` — line 18
  - `class Requirement` — line 23
  - `class ValidationIssue` — line 36
  - `class AppliedValue` — line 42
  - `class RuleIssue` — line 49
  - `class ForgeState` — line 55
  - `class AssistantTurn` — line 71
  - `class ChatMessage` — line 82
  - `class UserFact` — line 88
  - `class PartialFact` — line 97
  - `class ConversationMemory` — line 106
    - `add_user_message` — line 114
    - `add_assistant_message` — line 124
    - `remember_fact` — line 129
    - `get_fact` — line 136
    - `forget_fact` — line 139
    - `remember_partial` — line 142
    - `get_partial` — line 149
    - `clear_partial` — line 152

### `ai-data-contract-manager/src/adcm/orchestrator.py`
- Language: Python
- Lines: 611
- Symbols:
  - `class ADCMOrchestrator` — line 29
    - `__init__` — line 32
    - `async start` — line 49
    - `async message` — line 58
    - `async _auto_resolve` — line 106
    - `_merge_current_structured` — line 216
    - `_scan_history` — line 259
    - `async state` — line 291
    - `_resolvable_fields` — line 296
    - `_candidate_from_facts` — line 306
    - `_semantic_prefix` — line 322
    - `_candidate_from_semantic` — line 332
    - `_evidence_message_sequence` — line 394
    - `_state_signature` — line 414
    - `_with_candidate_issue` — line 425
    - `_remember_deterministic` — line 432
    - `_candidate_issue_summary` — line 451
    - `_partial_question` — line 458
    - `_turn_from_state` — line 535

### `ai-data-contract-manager/src/adcm/runtime.py`
- Language: Python
- Lines: 43
- Symbols:
  - `function build_gateway` — line 14
  - `function build_semantic` — line 19
  - `function build_orchestrator` — line 26

### `ai-data-contract-manager/src/adcm/semantic.py`
- Language: Python
- Lines: 124
- Symbols:
  - `class CandidateValue` — line 13
  - `class ExtractionResult` — line 20
  - `class SemanticResolver` — line 24
    - `async extract_from_history` — line 26
    - `async close` — line 35
  - `class NoopSemanticResolver` — line 39
    - `async extract_from_history` — line 40
  - `class PydanticAISemanticResolver` — line 51
    - `__init__` — line 54
    - `async close` — line 76
    - `async extract_from_history` — line 85

### `ai-data-contract-manager/src/adcm/settings.py`
- Language: Python
- Lines: 91
- Symbols:
  - `class ADCMSettings` — line 15
    - `resolved_llm_provider` — line 43
    - `semantic_model_name` — line 53
    - `public_runtime_summary` — line 58
    - `validate_enabled_llm` — line 68
  - `function project_root` — line 83
  - `function load_settings` — line 87

## `mcp-servers/`

### `mcp-servers/mcp-contract-forge/config/contract.json`
- Language: JSON
- Lines: 1864
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/config/ux_rules_contract_v1.json`
- Language: JSON
- Lines: 153
- Symbols: none extracted

### `mcp-servers/mcp-contract-forge/config/ux_rules_original.json`
- Language: JSON
- Lines: 455
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
- Lines: 333
- Symbols:
  - `class ContractForge` — line 25
    - `__init__` — line 36
    - `from_files` — line 43
    - `list_source_systems` — line 48
    - `start_session` — line 54
    - `submit_values` — line 59
    - `get_state` — line 76
    - `_candidate_path_allowed` — line 81
    - `_disallowed_path_issue` — line 96
    - `_apply_explicit` — line 109
    - `_advance` — line 174
    - `_pending` — line 214
    - `_source_type_choices` — line 254
    - `_overridable` — line 261
    - `_state` — line 297
    - `_get` — line 328

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
- Lines: 97
- Symbols:
  - `class Origin` — line 8
  - `function can_replace` — line 33
  - `class Requirement` — line 44
  - `class ValidationIssue` — line 57
  - `class AppliedValue` — line 63
  - `class RuleIssue` — line 70
  - `class ForgeState` — line 76
  - `class SessionData` — line 90

### `mcp-servers/mcp-contract-forge/src/contract_forge/path_utils.py`
- Language: Python
- Lines: 93
- Symbols:
  - `function split_path` — line 11
  - `function get_path` — line 15
  - `function has_path` — line 29
  - `function set_path` — line 37
  - `function write_value` — line 59
  - `function delete_path` — line 82

### `mcp-servers/mcp-contract-forge/src/contract_forge/rules.py`
- Language: Python
- Lines: 188
- Symbols:
  - `class RuleEngine` — line 14
    - `__init__` — line 15
    - `systems` — line 21
    - `source_types` — line 24
    - `input_mode` — line 27
    - `apply_system_source_type` — line 35
    - `apply_pass` — line 54
    - `_apply_rule` — line 78
    - `_condition_matches` — line 145
    - `_render` — line 155
    - `_transform` — line 163
    - `_set` — line 171

### `mcp-servers/mcp-contract-forge/src/contract_forge/schema.py`
- Language: Python
- Lines: 367
- Symbols:
  - `class SchemaNavigator` — line 30
    - `__init__` — line 39
    - `resolve_ref` — line 43
    - `active_node` — line 58
    - `schema_at_path` — line 79
    - `path_exists_in_schema` — line 98
    - `requirement_at_path` — line 101
    - `source_type_values` — line 118
    - `inject_defaults` — line 133
    - `ensure_required_containers` — line 164
    - `missing_requirements` — line 185
    - `_walk_array` — line 239
    - `_walk_object_item` — line 249
    - `_dedupe` — line 268
    - `public_schema` — line 277
    - `unsupported_requirement_keywords` — line 317
    - `allowed_values` — line 342
    - `validate_value` — line 350
    - `validate` — line 361
