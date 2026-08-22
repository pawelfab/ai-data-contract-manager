# PydanticAI heuristics

PydanticAI is used as an ADCM adapter, not as the owner of application state.

Three structured responsibilities are implemented:
1. evidence-to-requirement resolution (`ResolveResult`),
2. semantic inconsistency detection (`AdvisoryIssue[]`),
3. user question composition (`QuestionResult`).

Every proposed contract candidate must contain an `evidence_id`. `ValueResolver` rejects an LLM value if that evidence is not present in the session. Authority is taken from the evidence record, not trusted from model output.

Optional context MCPs can be attached through `MCPToolset`. They gather Jira/Wiki/repository/schema context or produce user-visible tool output. Forge is deliberately excluded.
