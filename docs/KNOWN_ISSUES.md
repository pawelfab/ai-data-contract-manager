# Known issues / consciously deferred work

1. **Supplied contract has dangling refs.** Runtime copy is repaired conservatively; authoritative `$defs` are still required from the owner.
2. **Source-specific defs are currently not referenced by the root snapshot.** `JdbcSourceConfig`, `JsonSourceConfig`, `FixedWidthSourceConfig`, `TxtSourceConfig` exist in `$defs`, but the supplied root does not currently activate them. The global `/**/systemZrodlowy` enrichment is ready for when such a branch becomes reachable/discovered.
3. **Partial columns.** Names-only column evidence is not retained in a dedicated partial-fact model. Do not insert invalid incomplete columns into canonical state.
4. **Context MCP + no-tool local endpoint.** Optional context MCP agents require a model/provider capable of tool calls. `PromptedOutput` solves structured output for heuristic agents but does not make an API without tool support capable of MCP tool calling.
5. **Conflict policy.** `NEEDS_USER_DECISION` is defined but no generic deterministic conflict policy exists yet.
6. **Persistence/logging.** In-memory sessions remain developer/demo only; Cloud Run scale-out needs durable shared session storage.
7. **Contract DSL compatibility.** Schema/rules/enrichment versions should eventually be compatibility-gated as one runtime bundle.
