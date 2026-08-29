---
status: active
created: YYYY-MM-DD
completed:
---

# Implementation: <name>

## Implementation contract

Owning service:

Owning boundary:

Files expected to change:
- ...

Files/services explicitly not to change:
- ...

Main invariant:

Implementation approach:

Tests:
- ...

Architecture risks:
- ...

## Current behavior

Describe only the current behavior relevant to this task. Reference code/tests or service documentation rather than duplicating the whole architecture.

## Planned changes

1. ...
2. ...
3. ...

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

Record any discovery that invalidates an assumption or materially changes implementation complexity.

For each finding record:

### Finding: <short title>

Observation:

Affected assumption:

Implementation impact:

Workaround complexity:

Simpler corrective option:

Decision:

If there are no findings, write:

`None.`

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many special cases, non-obvious transformations or changes across unrelated components, stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema, configuration or protected file.

## Deviations from the original plan

Record only material deviations and why they were necessary.

`None.`

## Verification

- [ ] relevant unit tests pass
- [ ] relevant integration tests pass
- [ ] architecture/boundary tests pass when applicable
- [ ] configured quality gates pass
- [ ] documentation freshness reviewed
- [ ] `docs/generated/documentation-impact.md` reviewed
- [ ] required curated documentation updated

## Final result

Summarize what was actually implemented, not what was originally planned.

## Unresolved items

- none

## Completion procedure

Before declaring this task complete:

1. run relevant tests and repository quality gates;
2. verify documentation freshness;
3. review `docs/generated/documentation-impact.md`;
4. update only curated documents whose responsibility or documented behavior changed;
5. record the final implementation result, deviations and unresolved items above;
6. change this document metadata to:

```yaml
status: completed
completed: YYYY-MM-DD
```

7. update `TASK.md` status to `completed`;
8. move the entire task directory from:

`docs/active-task/YYYY-MM-DD_task-name/`

to:

`docs/history/YYYY-MM-DD_task-name/`

Do not leave completed task documentation in `docs/active-task/`.
