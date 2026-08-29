# Generated documentation impact

Source snapshot: `d9c51a46e2d4608205761096bcaccff35cca69f5f426ea9d3a10f1e28cbcce49`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/Dockerfile`
- `ai-data-contract-manager/README.md`
- `ai-data-contract-manager/src/adcm/adapters/api/app.py`
- `ai-data-contract-manager/src/adcm/adapters/api/composition.py`
- `ai-data-contract-manager/src/adcm/adapters/api/errors.py`
- `ai-data-contract-manager/src/adcm/adapters/api/mappers.py`
- `ai-data-contract-manager/src/adcm/adapters/api/models.py`
- `ai-data-contract-manager/src/adcm/adapters/forge_mcp.py`
- `ai-data-contract-manager/src/adcm/adapters/session_memory.py`
- `ai-data-contract-manager/src/adcm/application/session_service.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/domain/errors.py`
- `ai-data-contract-manager/src/adcm/domain/session.py`
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/src/adcm/ports/session_repository.py`
- `ai-data-contract-manager/tests/test_api.py`
- `ai-data-contract-manager/tests/test_api_architecture.py`
- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/history/2026-08-29_rest-api-v1/IMPLEMENTATION.md`
- `docs/history/2026-08-29_rest-api-v1/TASK.md`
- `docs/logging-architecture.md`
- `docs/logging-implementation-guide.md`
- `readme.md`

## Curated documentation to review

- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
