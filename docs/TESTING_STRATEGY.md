# Testing strategy

Prioritize invariant tests over prompt snapshots.

Required test classes:

1. Candidate precedence: explicit user beats enrichment and default.
2. Draft authority: unauthorized paths never enter the draft.
3. Pre-path signals: remain unbound until a legal path exists.
4. Cross-cutting preferences: expand only to legal paths.
5. Corrections: old signal becomes superseded and revision is retained.
6. Unknown systems: base workflow still proceeds.
7. Fast-forward: one rich user message can satisfy several MCP stages without additional user turns.
8. No-progress protection: workflow loop fails deterministically instead of spinning.
9. MCP provenance: enrichment/default candidates preserve evidence.
10. External capability results: are candidates/findings, never direct draft writes.

LLM tests should focus on structured semantic extraction against fixed examples. Core application tests should not require an LLM or network.
