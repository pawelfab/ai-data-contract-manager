# User-turn lifecycle

Every user turn follows this order.

```text
1. Save raw user message
2. Build compact AgentContext from application state
3. SemanticInterpreter -> TurnInterpretation
4. Apply signals / preferences / corrections
5. WorkflowRunner starts or continues Contract Forge onboarding
6. For each MCP stage:
   a. merge newly authorized paths
   b. bind pending signals
   c. expand cross-cutting preferences
   d. ingest MCP enrichment/default candidates with evidence
   e. resolve candidates deterministically
   f. project only legal resolved paths into draft
   g. if all requirements are satisfied, call next stage immediately
7. Stop when:
   - user input is genuinely missing, or
   - workflow is complete, or
   - an external required capability must be resolved
8. Persist state + audit/revision data
9. Compose the user-visible response
```

The user-visible response must never be produced between steps 3 and 7. This prevents the LLM from presenting raw/unprocessed MCP requirements before enrichment/default logic has run.

## Fast-forward example

User provides one prompt containing system, feed name, format, delimiter, encoding and target details. Semantic extraction captures all facts at once. Contract Forge may still expose stages one by one; WorkflowRunner reuses already known information and traverses all satisfiable stages internally without asking the user again.

## Missing information

If a stage requires a path and none of these produce a candidate:

- explicit user signal;
- preference expansion;
- existing draft/contract import;
- external MCP finding;
- enrichment;
- derived candidate;
- default;

then `WorkflowResult.needs_user_input=True` and the UI/response layer asks a focused question.

## Corrections

A later user statement can represent replacement or uncertainty. SemanticInterpreter returns a typed `CorrectionIntent`. A definite replacement supersedes the old signal and creates a revision; an uncertain change does not mutate state and should lead to clarification.
