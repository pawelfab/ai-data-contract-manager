# Generated documentation impact

Generated: `2026-08-23T12:12:42.770489+00:00`
Commit: `unavailable; current source inventory used`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/pyproject.toml`
- `ai-data-contract-manager/src/adcm/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/inbound/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/inbound/fastapi/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/inbound/fastapi/app.py`
- `ai-data-contract-manager/src/adcm/adapters/inbound/fastapi/routes.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/context_mcp/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/context_mcp/noop.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/context_mcp/pydantic_ai_agent.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/forge_mcp/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/forge_mcp/client.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/llm/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/llm/heuristics.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/llm/pydantic_ai_heuristics.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/session_memory/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/outbound/session_memory/repository.py`
- `ai-data-contract-manager/src/adcm/application/__init__.py`
- `ai-data-contract-manager/src/adcm/application/ports/__init__.py`
- `ai-data-contract-manager/src/adcm/application/ports/context_agent.py`
- `ai-data-contract-manager/src/adcm/application/ports/context_provider.py`
- `ai-data-contract-manager/src/adcm/application/ports/forge.py`
- `ai-data-contract-manager/src/adcm/application/ports/llm.py`
- `ai-data-contract-manager/src/adcm/application/ports/session_repository.py`
- `ai-data-contract-manager/src/adcm/application/services/__init__.py`
- `ai-data-contract-manager/src/adcm/application/services/candidate_decision.py`
- `ai-data-contract-manager/src/adcm/application/services/value_resolver.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/__init__.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/change_value.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/collect_context.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/create_session.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/handle_message.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/stabilize_contract.py`
- `ai-data-contract-manager/src/adcm/bootstrap/__init__.py`
- `ai-data-contract-manager/src/adcm/bootstrap/container.py`
- `ai-data-contract-manager/src/adcm/bootstrap/settings.py`
- `ai-data-contract-manager/src/adcm/domain/__init__.py`
- `ai-data-contract-manager/src/adcm/domain/contract/__init__.py`
- `ai-data-contract-manager/src/adcm/domain/contract/path.py`
- `ai-data-contract-manager/src/adcm/domain/contract/state.py`
- `ai-data-contract-manager/src/adcm/domain/contract/value.py`
- `ai-data-contract-manager/src/adcm/domain/evidence/__init__.py`
- `ai-data-contract-manager/src/adcm/domain/evidence/models.py`
- `ai-data-contract-manager/src/adcm/domain/issues/__init__.py`
- `ai-data-contract-manager/src/adcm/domain/issues/models.py`
- `ai-data-contract-manager/src/adcm/domain/session/__init__.py`
- `ai-data-contract-manager/src/adcm/domain/session/models.py`
- `ai-data-contract-manager/src/adcm/main.py`
- `ai-data-contract-manager/src/adcm/rendering/__init__.py`
- `ai-data-contract-manager/src/adcm/rendering/yaml_renderer.py`
- `mcp-servers/mcp-contract-forge/pyproject.toml`
- `mcp-servers/mcp-contract-forge/resources/contract.json`
- `mcp-servers/mcp-contract-forge/resources/discovery_rules.json`
- `mcp-servers/mcp-contract-forge/resources/ux_rules.json`
- `mcp-servers/mcp-contract-forge/src/contract_forge/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/inbound/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/inbound/mcp/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/inbound/mcp/server.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_file/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_file/source.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/loader.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/parser.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/ref_resolver.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/rule_parser.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/schema_parser.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/semantic_paths.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/contract_json_v1/source_linter.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/discovery_json/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/discovery_json/repository.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_composite/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_composite/repository.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_json/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_json/adapter.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_user_store/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_user_store/memory.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/outbound/enrichment_user_store/noop.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/ports/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/ports/contract_parser.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/ports/contract_source.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/ports/discovery_policy.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/ports/enrichment_source.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/enrichment_context.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/enrichment_resolver.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/fillable_requirements.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/json_schema_validator.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/requirement_discovery.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/rule_engine.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/schema_engine.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/schema_paths.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/schema_validation_issue_mapper.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/semantic_path_resolver.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/union_branch_selector.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/use_cases/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/use_cases/evaluate_contract.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/bootstrap/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/bootstrap/container.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/bootstrap/settings.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/contract/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/contract/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/discovery/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/discovery/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/enrichment/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/enrichment/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/evaluation/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/evaluation/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/rules/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/rules/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/schema/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/schema/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/main.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/utils/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/utils/pointer.py`

## Curated documentation to review

- `ai-data-contract-manager/docs/`
- `docs/CURRENT_STATE.md`
- `docs/architecture.md`
- `mcp-servers/mcp-contract-forge/docs/`
- `mcp-servers/mcp-contract-forge/docs/contract-format.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- `mcp-servers/mcp-contract-forge/docs/requirement-discovery.md`

## Commit workflow

The pre-commit hook requires curated documentation with documentation-relevant code. The post-commit hook regenerates this report and the repository inventory, then records the source snapshot. Generated files are left unstaged for review and a subsequent commit.
