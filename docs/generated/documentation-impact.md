# Generated documentation impact

Source snapshot: `49038bdf198923def959433c68c3db75902c5fcbe948ce35236d3e43cbf6c930`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `ai-data-contract-manager/docs/session-flow.md`
- `ai-data-contract-manager/src/adcm/application/services/value_resolver.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/handle_message.py`
- `ai-data-contract-manager/src/adcm/application/use_cases/stabilize_contract.py`
- `ai-data-contract-manager/tests/unit/test_stabilization.py`
- `ai-data-contract-manager/tests/unit/test_value_resolver.py`
- `docs/CURRENT_STATE.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/schema_paths.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/use_cases/evaluate_contract.py`
- `mcp-servers/mcp-contract-forge/tests/unit/test_evaluate_contract.py`
- `mcp-servers/mcp-contract-forge/tests/unit/test_union_branch_selector.py`

## Curated documentation to review

- `ai-data-contract-manager/docs/`
- `docs/CURRENT_STATE.md`
- `docs/architecture.md`
- `mcp-servers/mcp-contract-forge/docs/`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
