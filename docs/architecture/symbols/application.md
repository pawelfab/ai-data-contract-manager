---
scope: src/adcm/application
last_verified: working-tree-2026-08-19
---

# Symbol catalog: application

| Path | Symbol | Responsibility / errors |
|---|---|---|
| `chat_service.py` | `ChatService.handle_user_message` | Complete load → interpret → apply → fast-forward → save turn; persistence/interpreter errors propagate. |
| `context_builder.py` | `AgentContextBuilder.build` | Project active state and bounded recent messages. |
| `turn_processor.py` | `TurnProcessor.apply_user_turn` | Append evidence, signals/preferences/corrections, supersession, and revision history; no draft writes. |
| `signal_binder.py` | `SignalBinder.bind` | Bind a signal only when one concrete authorized path declares its concept; reset it to `unbound` when the current view has zero or multiple matches. |
| `preference_expander.py` | `PreferenceExpander.expand` | Create candidates for every concrete current authorized path declaring an active preference concept. |
| `candidate_resolver.py` | `CandidateResolver.resolve` | Preflight all IDs/confidence and compute all winners before status commit; select by origin precedence, same-origin Forge priority, revision/sequence, and finite confidence. Any error leaves statuses unchanged. |
| `draft_projector.py` | `DraftProjector.project` | Rebuild nested draft from resolved values allowed by `CurrentSchemaView`. |
| `capability_router.py` | `CapabilityRouter.register`, `can_execute`, `execute` | Longest-prefix handler routing; missing handler raises `KeyError`. |
| `workflow_runner.py` | `WorkflowRunner.run_until_stable` | Stateless Forge fast-forward and stable outcome mapping. |
| `workflow_runner.py` | `WorkflowRunner.run` | Compatibility alias. |
| `render_service.py` | `RenderCacheKey`, `ContractRenderService.render` | Cached Forge rendering; invalid/mismatched FINAL receipt raises `ValueError`. |

## Call graph

`ChatService` calls `AgentContextBuilder`, `SemanticInterpreterPort`, `TurnProcessor`, `WorkflowRunner`, and `SessionRepositoryPort`. `WorkflowRunner` calls Forge, optional `CapabilityRouter`, binder/expander/resolver/projector, and mutates `ConversationState`. `ContractRenderService` calls only Forge rendering and maintains an in-memory cache.
