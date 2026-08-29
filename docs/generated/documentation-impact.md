# Generated documentation impact

Source snapshot: `8e77a1aee3cee3de58c3fc59ed9bb401935de5cf7c7784612049a402bd2a1354`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `AGENTS.md`
- `ai-data-contract-manager/Dockerfile`
- `ai-data-contract-manager/README.md`
- `ai-data-contract-manager/pyproject.toml`
- `ai-data-contract-manager/requirements-bigquery.txt`
- `ai-data-contract-manager/src/adcm/adapters/api/app.py`
- `ai-data-contract-manager/src/adcm/adapters/forge_mcp.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/__init__.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/bigquery_app_log_sink.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/bigquery_session_audit_sink.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/local_app_log_sink.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/local_session_audit_sink.py`
- `ai-data-contract-manager/src/adcm/adapters/logging/sanitizer.py`
- `ai-data-contract-manager/src/adcm/application/candidate_policy.py`
- `ai-data-contract-manager/src/adcm/application/observability/__init__.py`
- `ai-data-contract-manager/src/adcm/application/observability/app_log_recorder.py`
- `ai-data-contract-manager/src/adcm/application/observability/models.py`
- `ai-data-contract-manager/src/adcm/application/observability/sanitizer.py`
- `ai-data-contract-manager/src/adcm/application/observability/session_audit_recorder.py`
- `ai-data-contract-manager/src/adcm/application/proposal_reconciler.py`
- `ai-data-contract-manager/src/adcm/application/stabilization_engine.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/src/adcm/ports/app_log_sink.py`
- `ai-data-contract-manager/src/adcm/ports/forge.py`
- `ai-data-contract-manager/src/adcm/ports/session_audit_sink.py`
- `ai-data-contract-manager/tests/test_document_engine.py`
- `ai-data-contract-manager/tests/test_forge_mcp_adapter.py`
- `ai-data-contract-manager/tests/test_logging_architecture.py`
- `ai-data-contract-manager/tests/test_observability.py`
- `ai-data-contract-manager/tests/test_turn_audit.py`
- `docker-compose.yml`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/active-task/2026-08-29_logs_module_implement/IMPLEMENTATION.md`
- `docs/active-task/2026-08-29_logs_module_implement/TASK.md`
- `docs/architecture-guardials.md`
- `docs/logging-architecture.md`
- `docs/logging-implementation-guide.md`
- `mcp-servers/mcp-contract-forge/Dockerfile`
- `mcp-servers/mcp-contract-forge/README.md`
- `mcp-servers/mcp-contract-forge/pyproject.toml`
- `mcp-servers/mcp-contract-forge/requirements-bigquery.txt`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/bigquery_app_log_sink.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/local_app_log_sink.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/adapters/logging/sanitizer.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/__init__.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/app_log_recorder.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/models.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/observability/sanitizer.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/ports/app_log_sink.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/server.py`
- `mcp-servers/mcp-contract-forge/tests/test_logging_architecture.py`
- `mcp-servers/mcp-contract-forge/tests/test_observability.py`
- `scripts/agent/README.md`

## Curated documentation to review

- `AGENTS.md`
- `ai-data-contract-manager/README.md`
- `docs/ARCHITECTURE_BASELINE.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/protocol/README.md`
- `mcp-servers/mcp-contract-forge/README.md`
- `scripts/agent/README.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
