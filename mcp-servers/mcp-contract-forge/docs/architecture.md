# Contract Forge architecture

```text
contract.json / ux_rules
       |
       v
outbound source adapters
- contract_json_v1
- enrichment_json
       |
       v
NormalizedContract
       |
       +--> schema engine
       +--> rule engine
       +--> enrichment/default resolution
       |
       v
ForgeEvaluation
       |
       v
MCP evaluate_contract
```

No LLM is involved. This property is intentional: identical inputs should produce identical Forge outputs.
