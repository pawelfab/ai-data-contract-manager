---
status: active
created: 2026-08-23
completed:
---

# Implementation: enforce one task document per code-changing commit

## Implementation contract

Owning service: `scripts/agent` (documentation automation)

Owning boundary: staged pre-commit documentation gate

Files expected to change:
- `scripts/agent/doc_freshness.py`
- `scripts/agent/config.json`
- `scripts/agent/config.example.json`
- `docs/documentation-automation.md`

Files/services explicitly not to change:
- `githooks/pre-commit` — already fails on a non-zero exit code
- `scripts/agent/common.py` — `staged_files()` and `documentation_relevant()` are reused as-is
- `docs/active-tasks/**` — untracked migration leftover, out of scope

Main invariant: the task-documentation check never consults
`documentation_evidence_patterns`. A curated service document must not be able to satisfy
the task-lifecycle requirement.

Implementation approach: add a second boolean gate inside the existing `check_staged()`
rather than a new entry point, so one `--check-staged` invocation reports both requirements
and the hook keeps its single call site.

Tests: exercised through `check_staged()` directly with synthetic staged file sets, plus an
end-to-end `--check-staged` run against the real Git index.

Architecture risks:
- a too-strict pattern blocks every commit with no satisfiable path — realised, see findings;
- a completion move could be read as "no task document staged" — covered, both the deleted
  and the added path are staged and both match.

## Current behavior

`check_staged()` (`scripts/agent/doc_freshness.py`) collects staged paths via
`staged_files()`, filters them to documentation-relevant code with `documentation_relevant()`
excluding the architecture docs directory, then requires at least one staged path matching
`documentation_evidence_patterns` and not `documentation_non_evidence_patterns`.

`main()` returns `1` on `STALE`; `githooks/pre-commit` invokes
`python scripts/agent/doc_freshness.py --check-staged` and aborts the commit on that code.

## Planned changes

1. repair the over-escaped regexes in `scripts/agent/config.json`;
2. add the task-documentation gate to `check_staged()` and return `staged_task_docs`;
3. report staged task documentation in `print_human()`; update the `--check-staged` help;
4. mirror the task-documentation keys into `scripts/agent/config.example.json`;
5. document the two independent requirements in `docs/documentation-automation.md`.

## Unexpected findings

### Finding: every regex in the working-tree config was double-escaped

Observation: the uncommitted edit to `scripts/agent/config.json` doubled every backslash in
every regex value — 93 occurrences. In JSON, `"\\\\d"` parses to the string `\\d`, which as
a regex matches a literal backslash followed by `d`, never a digit.

Verified empirically before any code change: of the five `documentation_evidence_patterns`,
only the two containing no escapes (`^ai-data-contract-manager/docs/`,
`^mcp-servers/mcp-contract-forge/docs/`) matched anything. `docs/architecture.md`,
`docs/CURRENT_STATE.md` and both task-documentation patterns matched nothing. The same
doubling had reached `quality_commands.test`, producing `\\.venv\\Scripts\\` path separators.

Affected assumption: that the task-documentation config keys were ready and only the code to
honour them was missing.

Implementation impact: with `require_task_doc_for_staged_relevant_code: true` and a pattern
that cannot match, the new gate would have rejected every commit touching relevant code with
no file the author could add to satisfy it.

Workaround complexity: none warranted — normalising the escaping in the config is strictly
simpler than compensating for it in code, and compensating would have hidden the defect.

Simpler corrective option: restore the escaping style already used at `HEAD` and in
`scripts/agent/config.example.json`, both of which are correct.

Decision: repaired the config as part of this task, with the user's explicit agreement to fix
all over-escaped patterns rather than only the two task-documentation keys.

## Deviations from the original plan

The config repair was not part of the original request, which named only
`scripts/agent/doc_freshness.py`. It was added because the requested gate cannot function
without it. Confirmed with the user before implementation.

## Verification

- [x] relevant unit tests pass — no test suite covers `scripts/agent`; verified by direct
      invocation of `check_staged()` across seven staged-file scenarios
- [ ] relevant integration tests pass — not applicable
- [ ] architecture/boundary tests pass when applicable — not applicable
- [x] configured quality gates pass — `format_check` and `lint` are empty in config
- [x] documentation freshness reviewed
- [x] `docs/generated/documentation-impact.md` reviewed
- [x] required curated documentation updated

Scenario results:

| staged files | status | gate that failed |
| --- | --- | --- |
| no relevant code | CURRENT | — |
| code only | STALE | both |
| code + curated service document only | STALE | task document |
| code + task document only | CURRENT | — |
| code + curated + task document | CURRENT | — |
| completion move (`active-task` D + `history` A) | CURRENT | — |
| code + generated documentation only | STALE | both |

The third row is the regression this task exists to prevent.

## Final result

`check_staged()` now evaluates two independent gates and combines them:

- `curated_ok` — unchanged behavior, driven by `documentation_evidence_patterns` minus
  `documentation_non_evidence_patterns` and `require_docs_for_staged_relevant_code`;
- `task_ok` — new, driven by `task_documentation_active_pattern`,
  `task_documentation_completed_pattern` and `require_task_doc_for_staged_relevant_code`,
  matched against all staged paths and never against the curated evidence list.

The returned payload carries `staged_task_docs` alongside `staged_architecture_docs`, and the
`reason` names which of the two requirements is unmet — combined, curated-only, or
task-document-only. `print_human()` lists staged task documentation, so a blocked commit
shows what was and was not detected.

`scripts/agent/config.json` regex and command values were restored to single escaping, and
the three task-documentation keys were added to `scripts/agent/config.example.json` so a
fresh clone gets the documented workflow by default.

## Unresolved items

- `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow/` remains untracked and
  non-conforming; it will not satisfy the gate until it is renamed to
  `docs/active-task/2026-08-23_source-bronze-silver-gold-flow/` with `TASK.md` and
  `IMPLEMENTATION.md`. Owned by that task, not this one.

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

`docs/active-task/2026-08-23_task-doc-gate/`

to:

`docs/history/2026-08-23_task-doc-gate/`

Do not leave completed task documentation in `docs/active-task/`.
