# Generated documentation impact

Source snapshot: `4ac97acf861df0319ebd2e15a51e54429d06d4483774a733c76d0e86d74bef81`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/src/adcm/adapters/intent_heuristic.py`
- `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- `ai-data-contract-manager/src/adcm/application/intent_resolution_policy.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/tests/test_api.py`
- `ai-data-contract-manager/tests/test_audit_compact.py`
- `ai-data-contract-manager/tests/test_intent_resolution_policy.py`
- `ai-data-contract-manager/tests/test_knowledge_query.py`
- `ai-data-contract-manager/tests/test_turn_audit.py`
- `docs/ARCHITECTURE_BASELINE.md`
- `docs/BUSINESS_BEHAVIOR.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/history/2026-08-30_intent-resolution-policy/IMPLEMENTATION.md`
- `docs/history/2026-08-30_intent-resolution-policy/TASK.md`

## Curated documentation to review

- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
