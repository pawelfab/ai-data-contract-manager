---
module: domain
source_roots:
  - src/adcm/domain
last_verified: working-tree-2026-08-18
owners: []
---

# Domain module

## Responsibility

Define ADCM state, provenance, schema-view, evaluation, validation, rendering, and workflow-outcome models without infrastructure dependencies. `ContractPath` reads and writes concrete nested instance paths.

## Public entry points

| Path | Symbol | Contract |
|---|---|---|
| `src/adcm/domain/models.py` | `ConversationState` | Aggregate session state for messages, signals, preferences, candidates, draft, workflow, evidence, and revisions. |
| `src/adcm/domain/models.py` | `ContractDraft.canonical_hash` | Stable SHA-256 over canonical sorted JSON. |
| `src/adcm/domain/models.py` | `CurrentSchemaView.is_path_allowed` | Accept an exact path or an indexed instance matching an authorized `[*]` schema path. |
| `src/adcm/domain/contract_path.py` | `ContractPath.read`, `write` | Navigate concrete object/list paths such as `silver.tables[0].columns[1].name`. |

## Invariants and errors

- User-origin `Signal`, `Preference`, and `ValueCandidate` instances require evidence; Pydantic validation rejects missing evidence.
- `ContractPath.parse` raises `ValueError` for an empty/invalid path; `write` raises `TypeError` when the existing container shape conflicts; `read` returns its default for missing/incompatible traversal.
- Candidate origin priority is declared by `DEFAULT_ORIGIN_PRIORITY`; deterministic tie-breaking is completed by the application resolver.

## Dependencies

Pydantic is the only runtime modeling dependency. The domain does not import application, adapter, MCP, persistence, or Pydantic AI modules.

## Tests proving behavior

- `tests/test_contract_path.py` — nested arrays and padding behavior.
- `tests/test_signal_binding.py::test_user_explicit_signal_without_evidence_is_invalid_state` — evidence invariant.
- `tests/test_draft_projector.py` — authorization and reprojection.
- `tests/test_candidate_resolver.py` — priority and deterministic correction ordering.

