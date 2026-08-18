# Corrected package manifest

## New Python files
- `src/adcm/domain/contract_path.py`
- `src/adcm/application/render_service.py`

## Updated Python files
- `src/adcm/domain/models.py`
- `src/adcm/application/candidate_resolver.py`
- `src/adcm/application/draft_projector.py`
- `src/adcm/application/signal_binder.py`
- `src/adcm/application/preference_expander.py`
- `src/adcm/application/turn_processor.py`
- `src/adcm/application/context_builder.py`
- `src/adcm/application/workflow_runner.py`
- `src/adcm/application/capability_router.py`
- `src/adcm/application/chat_service.py`
- `src/adcm/ports/contract_forge.py`
- `src/adcm/adapters/mcp/mock_contract_forge.py`
- `src/adcm/adapters/llm/rule_based_interpreter.py`
- `examples/demo_flow.py`

## New / updated tests
- `tests/test_contract_path.py`
- `tests/test_render_service.py`
- `tests/test_rule_based_interpreter.py`
- `tests/test_candidate_resolver.py`
- `tests/test_draft_projector.py`
- `tests/test_signal_binding.py`
- `tests/test_workflow.py`

## New / updated architecture documentation
- `docs/ISSUES_AND_RESOLUTIONS.md`
- `docs/STAGE_SPEC_TEMPLATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/MCP_CONTRACT.md`
- `docs/TURN_LIFECYCLE.md`
- `docs/DESIGN_DECISIONS.md`
- `docs/TESTING_STRATEGY.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `LLM_REPO_GUIDE.md`
- `README.md`

## Main planning prompt
- `PROMPT_STAGE_SPEC_GENERATOR.md`

## Dependency change
- `PyYAML` added for reference YAML rendering.
- optional AI dependency changed to `pydantic-ai-slim[mcp]`.

## Verification
- `pytest`: 17 passed
- `python -m compileall`: passed
