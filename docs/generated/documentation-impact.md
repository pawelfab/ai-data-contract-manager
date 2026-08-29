# Generated documentation impact

Source snapshot: `280079b7d2dcc13b70dd0ad4322adf54b727a9d9132bbd2e369b5afc6480983f`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `.codex/agents/explorer.toml`
- `.codex/agents/reviewer.toml`
- `.codex/agents/worker.toml`
- `.codex/config.toml`
- `AGENTS.md`
- `ai-data-contract-manager/README.md`
- `ai-data-contract-manager/pyproject.toml`
- `ai-data-contract-manager/requirements-ai.txt`
- `ai-data-contract-manager/requirements-dev.txt`
- `ai-data-contract-manager/requirements.txt`
- `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- `docker-compose.yml`
- `docs/CURRENT_STATE.md`
- `docs/agent/START_HERE.md`
- `docs/history/2026-08-29_agent-automation-refresh/IMPLEMENTATION.md`
- `docs/history/2026-08-29_agent-automation-refresh/TASK.md`
- `docs/templates/task/IMPLEMENTATION.md`
- `mcp-servers/mcp-contract-forge/README.md`
- `mcp-servers/mcp-contract-forge/pyproject.toml`
- `mcp-servers/mcp-contract-forge/resources/contract.json`
- `mcp-servers/mcp-contract-forge/src/contract_forge/server.py`
- `mcp-servers/mcp-contract-forge/tests/test_analyzer.py`
- `readme.md`
- `scripts/agent/config.example.json`
- `scripts/agent/config.json`

## Curated documentation to review

- `AGENTS.md`
- `ai-data-contract-manager/README.md`
- `docs/ARCHITECTURE_BASELINE.md`
- `docs/BUSINESS_BEHAVIOR.md`
- `docs/CORE_INVARIANTS.md`
- `docs/CURRENT_STATE.md`
- `docs/MODULE_CONTRACTS.md`
- `docs/protocol/README.md`
- `mcp-servers/mcp-contract-forge/README.md`
- `scripts/agent/README.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
