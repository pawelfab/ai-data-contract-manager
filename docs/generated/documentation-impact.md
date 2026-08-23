# Generated documentation impact

Source snapshot: `070963b3c76eb9f343e2bfc013ec9fe18550efa3eab32e433471c02adce49f2f`
Input: `staged Git index`

> This deterministic review aid does not replace curated architecture or service documentation.

## Changed source paths

- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/DECISIONS.md`
- `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow/HANDOFF.md`
- `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow/IMPLEMENTATION_GUIDE.md`
- `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow/PLAN.md`
- `docs/architecture-guardrails.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- `mcp-servers/mcp-contract-forge/resources/ux_rules.json`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/services/enrichment_resolver.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/application/use_cases/evaluate_contract.py`
- `mcp-servers/mcp-contract-forge/src/contract_forge/domain/enrichment/models.py`
- `mcp-servers/mcp-contract-forge/tests/unit/test_enrichment_repository.py`
- `mcp-servers/mcp-contract-forge/tests/unit/test_evaluate_contract.py`

## Curated documentation to review

- `docs/CURRENT_STATE.md`
- `docs/architecture.md`
- `mcp-servers/mcp-contract-forge/docs/`
- `mcp-servers/mcp-contract-forge/docs/contract-format.md`
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`
- `mcp-servers/mcp-contract-forge/docs/requirement-discovery.md`

## Commit workflow

When documentation-relevant source is staged, the pre-commit hook generates these artifacts from the staged Git index and stages them in the same commit. The post-commit hook does not modify the working tree.
