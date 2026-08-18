# Testing strategy

## Separate semantic tests from workflow tests
WorkflowRunner tests use deterministic typed fake interpretations. They must not fail because a demo NLP parser missed spelling/diacritics. RuleBasedInterpreter has its own tests.

## Domain invariants
Test at least:
- USER_EXPLICIT Signal without evidence fails;
- SignalBinder propagates evidence and source signal ID;
- same-origin correction resolves deterministically by revision/sequence;
- candidate scope is inspected on winning candidate, not ResolvedValue;
- DraftProjector rejects unauthorized paths;
- CurrentSchemaView replacement removes no-longer-legal paths;
- ContractPath writes nested arrays and uses `{}` padding for intermediate object-list elements.

## Workflow
Test:
- one prompt fast-forwards through multiple Forge evaluations;
- empty-requirement candidate stages still continue;
- workflow stops only on a real user requirement;
- capabilities can be resolved and retried;
- blocked capability maps to BLOCKED_EXTERNAL;
- COMPLETE triggers final validation.

## Rendering
Test artifact key semantics `(draft_hash, schema_revision, render_mode)` and that FINAL render requires VALID final validation.

## Contract integration
Real `contract.json`, `x-contract-rules`, enrichment rules and canonical path compilation belong to Contract Forge integration tests, not ADCM mock-path tests.
