# Known issues / consciously deferred work

1. **Source-specific definitions are not referenced by the root snapshot.** `JdbcSourceConfig`, `JsonSourceConfig`, `FixedWidthSourceConfig`, `TxtSourceConfig` exist in `$defs`, but the root does not currently activate them. The global `/**/systemZrodlowy` enrichment is ready when such a branch becomes reachable/discovered.
2. **Partial columns.** Names-only column evidence is not retained in a dedicated partial-fact model. Do not insert invalid incomplete columns into canonical state.
3. **Context MCP + no-tool local endpoint.** Optional context MCP agents require a model/provider capable of tool calls. `PromptedOutput` solves structured output for heuristic agents but does not make an API without tool support capable of MCP tool calling.
4. **Conflict policy.** `NEEDS_USER_DECISION` is defined but no generic deterministic conflict policy exists yet.
5. **Persistence/logging.** In-memory sessions remain developer/demo only; Cloud Run scale-out needs durable shared session storage.
6. **Contract DSL compatibility.** Schema/rules/enrichment versions should eventually be compatibility-gated as one runtime bundle.
