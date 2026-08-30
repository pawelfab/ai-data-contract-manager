# Generated documentation impact

Source snapshot: `732b63c79e5ce2ea2742f984b2160a5df78a101c392d5702ba3bf46bd064f08d`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/README.md`
- `ai-data-contract-manager/pyproject.toml`
- `ai-data-contract-manager/requirements-dev.txt`
- `ai-data-contract-manager/tests/live/conftest.py`
- `ai-data-contract-manager/tests/live/helpers.py`
- `ai-data-contract-manager/tests/live/test_live_authority.py`
- `ai-data-contract-manager/tests/live/test_live_completeness.py`
- `ai-data-contract-manager/tests/live/test_live_enrichment.py`
- `ai-data-contract-manager/tests/live/test_live_intent_kinds.py`
- `ai-data-contract-manager/tests/live/test_live_llm_intent.py`
- `docs/CURRENT_STATE.md`
- `docs/history/2026-08-30_live-e2e-tests/IMPLEMENTATION.md`
- `docs/history/2026-08-30_live-e2e-tests/TASK.md`
- `readme.md`
- `scripts/agent/config.json`

## Curated documentation to review

- `AGENTS.md`
- `ai-data-contract-manager/README.md`
- `docs/CURRENT_STATE.md`
- `scripts/agent/README.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
