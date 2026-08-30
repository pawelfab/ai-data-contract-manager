# Generated documentation impact

Source snapshot: `ccd48c721ee1db58304613f15405c029cd33533e8111530f52c075443a2a4ec0`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- `ai-data-contract-manager/src/adcm/adapters/response_basic.py`
- `ai-data-contract-manager/src/adcm/application/intent_resolution_policy.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/tests/test_api.py`
- `ai-data-contract-manager/tests/test_intent_resolution_policy.py`
- `ai-data-contract-manager/tests/test_knowledge_query.py`
- `docs/ARCHITECTURE_BASELINE.md`
- `docs/BUSINESS_BEHAVIOR.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/history/2026-08-30_unresolved-intent-contract/IMPLEMENTATION.md`
- `docs/history/2026-08-30_unresolved-intent-contract/TASK.md`

## Curated documentation to review

- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
