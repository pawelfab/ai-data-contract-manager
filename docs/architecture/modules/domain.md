---
module: domain
source_roots:
  - src/adcm/domain
last_verified: working-tree-2026-08-19
owners: []
---

# Domain module

## Responsibility

Define ADCM state, provenance, schema-view, evaluation, validation, rendering, and workflow-outcome models without infrastructure dependencies. `ContractPath` reads and writes concrete nested instance paths.

## Public entry points

| Path | Symbol | Contract |
|---|---|---|
| `src/adcm/domain/models.py` | `ConversationState` | Aggregate session state for messages, signals, preferences, candidates, resolutions, draft, workflow, evidence, and revisions; candidate IDs are unique, one candidate per path may be selected, and every resolution mirrors that candidate's path, canonical JSON value, origin, and evidence IDs. |
| `src/adcm/domain/models.py` | `ContractDraft.canonical_hash` | Stable SHA-256 over strict canonical sorted JSON; non-finite numbers are rejected. |
| `src/adcm/domain/models.py` | `CurrentSchemaView.is_path_allowed` | Accept a parseable dict-rooted concrete exact path or indexed instance matching an authorized `[*]` schema path; never the wildcard itself. |
| `src/adcm/domain/contract_path.py` | `ContractPath.read`, `write` | Navigate concrete object/list paths such as `silver.tables[0].columns[1].name`. |

## Invariants and errors

- User-origin `Signal`, `Preference`, and `ValueCandidate` instances require evidence; Pydantic validation rejects missing evidence.
- `ValueCandidate.confidence` is optional but finite; NaN and positive/negative infinity are rejected.
- `ContractPath.parse` accepts complete concrete paths starting with an object key only; it raises `ValueError` for empty, malformed, root-list, or wildcard paths. `write` raises `TypeError` when the existing container shape conflicts, retains `{}` padding for skipped object-list entries, and uses `[]` padding before directly nested array indices; `read` returns its default for missing/incompatible traversal.
- `CurrentSchemaView.is_path_allowed` rejects malformed, root-list, or wildcard query paths before exact/indexed-wildcard authorization.
- Candidate origin priority is declared by `DEFAULT_ORIGIN_PRIORITY`. The application resolver applies it before same-origin Forge priority, then correction revision/sequence and confidence; a policy-rank tie after confidence is rejected instead of being resolved by input order.
- `ConversationState` rejects duplicate candidate IDs, multiple selected candidates for one path, and resolved values whose selected candidate is absent, non-selected, or differs in path, canonical JSON value, origin, or evidence IDs. Canonical comparison distinguishes booleans, integers, and floats while ignoring object-key order.

## Dependencies

Pydantic is the only runtime modeling dependency. The domain does not import application, adapter, MCP, persistence, or Pydantic AI modules.

## Tests proving behavior

- `tests/test_contract_path.py` — nested arrays and padding behavior.
- `tests/test_signal_binding.py::test_user_explicit_signal_without_evidence_is_invalid_state` — evidence invariant.
- `tests/test_draft_projector.py` — authorization and reprojection.
- `tests/test_candidate_resolver.py` — priority and deterministic correction ordering.
