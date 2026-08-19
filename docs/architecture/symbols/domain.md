---
scope: src/adcm/domain
last_verified: working-tree-2026-08-19
---

# Symbol catalog: domain

## Provenance and candidate models

- `models.py::ValueCandidate` rejects non-finite confidence values; candidate IDs remain identity only, never ranking data.

- `models.py::EvidenceKind`, `Evidence` — classify and record sources.
- `models.py::ValueOrigin`, `CandidateScope`, `DEFAULT_ORIGIN_PRIORITY` — precedence metadata.
- `models.py::Signal`, `Preference`, `ValueCandidate` — semantic facts and concrete proposals; user-origin validators require evidence.
- `models.py::ResolvedValue` — winning value and selected candidate/evidence IDs.

## Schema, workflow, and rendering models

- `models.py::ContractDraft.canonical_hash()` uses strict canonical JSON; non-finite numbers raise `ValueError`.

- `models.py::CurrentSchemaView.is_path_allowed(path)` first requires a dict-rooted concrete path accepted by `ContractPath.parse`; schema wildcards only authorize matching indexed instances.

- `models.py::ContractDraft.canonical_hash()` — canonical JSON hash used for change/render identity.
- `models.py::CurrentSchemaView.is_path_allowed(path)` — exact or indexed-wildcard authorization.
- `models.py::ContractInput`, `ContractEvaluationResult`, `FinalValidationResult` — stateless Forge requests/results.
- `models.py::CapabilityRequest`, `CapabilityResult` — externally resolved capability exchange.
- `models.py::WorkflowOutcome`, `WorkflowOutcomeStatus` — stable application outcome.
- `models.py::RenderRequest`, `RenderedContract`, `RenderMode`, `FinalValidationReceipt` — canonical rendering contract.

## Aggregate state

- `models.py::ConversationState` rejects duplicate candidate IDs, multiple selected candidates per path, and resolved values that reference absent/non-selected candidates or differ from them in path, strict canonical JSON value, origin, or evidence IDs.

- `models.py::ConversationState` — messages, signals, preferences, candidates, resolved values, nested draft, workflow, evidence, revisions, and deterministic candidate sequence.
- `models.py::WorkflowState` — current schema view/stage, requirements, evaluation status, and capability results.
- `models.py::AgentContext` — compact interpreter input.

## Concrete paths

- `contract_path.py::ContractPath.write(document, path, value)` pads directly nested arrays with `[]` and object-list entries with `{}` according to the next path token.

- `contract_path.py::ContractPath.parse(path)` rejects malformed, root-list, and wildcard schema paths with `ValueError`; it produces tokens only for dict-rooted complete concrete paths.

- `contract_path.py::PathToken` — key or list index.
- `contract_path.py::ContractPath.parse(path)` — tokenize concrete instance paths.
- `contract_path.py::ContractPath.write(document, path, value)` — construct/update nested dict/list structures.
- `contract_path.py::ContractPath.read(document, path, default=None)` — safely read or return default.
