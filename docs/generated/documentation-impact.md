# Generated documentation impact

Source snapshot: `7a48e619d173ace4fd5569044d1b27f3f861f2e0a8ac8cc0f1111cb236a44e2d`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/README.md`
- `ai-data-contract-manager/src/adcm/adapters/api/app.py`
- `ai-data-contract-manager/src/adcm/application/observability/audit_views.py`
- `ai-data-contract-manager/src/adcm/application/observability/session_audit_recorder.py`
- `ai-data-contract-manager/src/adcm/application/stabilization_engine.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/tests/test_audit_compact.py`
- `docker-compose.yml`
- `docs/active-task/2026-08-29_compact-session-audit/IMPLEMENTATION.md`
- `docs/active-task/2026-08-29_compact-session-audit/TASK.md`
- `docs/active-task/2026-08-29_compact-session-audit/measure_audit_size.py`
- `docs/history/2026-08-29_logs_module_implement/IMPLEMENTATION.md`
- `docs/history/2026-08-29_logs_module_implement/TASK.md`
- `docs/logging-architecture.md`
- `docs/logging-implementation-guide.md`

## Curated documentation to review

- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
