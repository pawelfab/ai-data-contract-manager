# User turn lifecycle

1. Save raw user message.
2. Build compact `AgentContext` from structured state plus recent chat history.
3. Semantic interpreter returns typed `TurnInterpretation`.
4. TurnProcessor creates Evidence, Signals/Preferences/corrections and revisions.
5. WorkflowRunner begins fast-forward.
6. Send current ContractDraft snapshot to stateless Forge `evaluate_draft`.
7. Replace `CurrentSchemaView` with the returned view.
8. Bind currently legal pre-path Signals.
9. Expand Preferences only to currently legal paths.
10. Add Forge candidates with explicit provenance.
11. Deterministically resolve candidates.
12. Rebuild ContractDraft from resolved values + current schema view.
13. If Forge requests a capability and ADCM has a handler, execute it and evaluate again.
14. If a required value cannot be resolved automatically, stabilize as `WAITING_FOR_USER`.
15. If evaluate is COMPLETE, call `validate_final`.
16. Resolve final external dependencies if possible and retry validation.
17. Stabilize as COMPLETE / INVALID / BLOCKED_EXTERNAL / FAILED.
18. Persist state/audit.
19. If the draft/schema artifact key changed, call Forge `render_yaml` once after stabilization.
20. Generate the assistant response for the user.

The assistant must not respond before the internal turn has stabilized.
