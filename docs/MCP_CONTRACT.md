# MCP integration contract

## Contract Forge

ADCM should consume Contract Forge through `ContractForgePort`; the adapter may use Pydantic AI MCP tools, FastMCP directly or another transport. Do not leak the transport into application logic.

Minimal logical operations:

```python
next_requirements(known_values) -> RequirementBundle
validate_partial(draft) -> list[str]
validate_final(draft) -> list[str]
```

A real MCP can expose more explicit methods (`start_onboarding`, `submit_stage_values`, `explain_value`, etc.), but the ADCM adapter should normalize them into the port.

## RequirementBundle

A stage bundle contains:

- `stage_id`;
- `allowed_paths` — legal paths currently disclosed by Contract Forge;
- `requirements` — values required to leave the stage;
- `candidates` — defaults/enrichments/derived values with explicit origin/reason/evidence;
- `capability_requests` — calls ADCM should route to other MCPs;
- `complete`.

## Progressive disclosure

Contract Forge must not return the entire contract simply because it can parse the entire schema. It exposes enough legal paths and requirements for the current stage. ADCM accumulates authorized paths over the session.

## Unknown source systems

Onboarding order and base/default enrichments must work even if the source system has no system-specific enrichment. Contract Forge should layer enrichment conceptually:

```text
common defaults
+ source family
+ source format
+ source-system-specific rules (optional)
```

Missing the last layer must not destroy workflow structure.

## Enrichment repository inside Contract Forge

Keep enrichment storage behind an internal `EnrichmentRepository` port:

```text
JsonEnrichmentRepository       # first implementation
GitHubEnrichmentRepository     # future
CompositeEnrichmentRepository  # optional layered lookup
```

ADCM does not know where Contract Forge obtained the enrichment. It only consumes origin/evidence metadata.

## Other MCPs

Schema Explorer should expose capabilities such as:

```text
schema.table_exists
schema.get_columns
schema.validate_table_name
schema.find_similar
```

Contract Forge can request a capability by name. ADCM routes it through `CapabilityRouter`, stores the returned result as evidence/finding/candidate, then continues Contract Forge. Contract Forge does not need a direct dependency on Schema Explorer transport.
