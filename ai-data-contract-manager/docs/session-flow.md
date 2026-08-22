# Session and stabilization flow

Each message becomes evidence. `attachments: list[str]` currently means inline textual evidence, not paths or upload identifiers.

ADCM stabilizes synchronously at the application level:

```text
current state
  → Forge evaluate
  → replace current derived suggestions
  → resolve current exposed requirements (and explicit edits on the first round)
  → deterministic candidate decisions
  → if state changed, repeat
  → at fixed point run semantic consistency once and compose the question/result
```

## Candidate decisions

LLM output is a candidate, never a state mutation. The application checks evidence existence, confidence, legal/current path, expected type, container safety and authority. A rejected candidate is not persisted in `ContractState`; its evidence remains available. `NEEDS_USER_DECISION` is reserved for a future explicit conflict policy.

`CandidateOutcome.changed` is independent from decision status. An identical accepted value has `changed=false`, which is required for convergence.

## Derived values

Derived/default/enrichment values are replaced from the current Forge suggestions on every round. This prevents stale values from a former source system surviving a user edit.

## Warnings

The API response contains warnings for the current fixed point only. Historical/intermediate warnings belong in a future session audit logger, not the current response.

## Future uploads

File upload should be added through an inbound upload endpoint plus `FileContentExtractorPort` and extractor adapters. Existing evidence, heuristics and stabilization logic should remain unchanged.
