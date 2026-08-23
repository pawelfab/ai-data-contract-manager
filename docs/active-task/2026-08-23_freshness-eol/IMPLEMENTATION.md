---
status: active
created: 2026-08-23
completed:
---

# Implementation: freshness must ignore checkout line endings

## Implementation contract

Owning service: `scripts/agent` (documentation automation)

Owning boundary: source hashing and the freshness marker

Files expected to change:
- `scripts/agent/common.py`
- `scripts/agent/repo_inventory.py`
- `docs/documentation-automation.md`

Files/services explicitly not to change:
- `githooks/pre-push` — it correctly aborts on a non-zero exit code; the defect was the
  comparison it invoked, not the hook
- `docs/.freshness.json` — see the deviation below, no re-mark turned out to be required
- repository line endings and `core.autocrlf`

Main invariant: `current_source_hashes()` and `staged_source_hashes()` produce identical
digests for an unmodified file, regardless of how the working tree was checked out.

Implementation approach: one shared `content_digest()` helper used by both paths, rather than
normalizing at either call site, so the two cannot drift apart again.

Tests: existing `scripts/agent/tests/test_documentation_update.py`, plus direct comparison of
the two hash maps across the real 119-file corpus.

Architecture risks:
- normalization could corrupt a file containing a lone carriage return — checked, none exist;
- changing digest values invalidates the committed marker — checked, it did not.

## Current behavior

`sha256_file()` streamed each working-tree file and `staged_source_hashes()` hashed index
blobs from `git show :path`. Both fed `source_snapshot_id()` and the `source_hashes` map in
`docs/.freshness.json`.

`compare()` (`--check`) read the marker and re-hashed the working tree; `mark_staged()`,
invoked by `documentation_update.py --staged` from the pre-commit hook, wrote the marker from
the index. On a `core.autocrlf` checkout the two never agreed.

`repo_inventory.inspect_bytes()` hashed raw bytes the same way, so
`docs/generated/repository-inventory.json` carried EOL-dependent `sha256` and `bytes` values.

## Planned changes

1. add `content_digest()` to `scripts/agent/common.py` and route both hash paths through it;
2. remove the now-unused `sha256_file()`;
3. normalize in `repo_inventory.inspect_bytes()` so the inventory is generation-path stable;
4. document the normalization under **Freshness** in `docs/documentation-automation.md`.

## Unexpected findings

### Finding: the committed marker was already correct, so no re-mark was needed

Observation: the plan assumed normalization would invalidate `docs/.freshness.json` and
budgeted a `documentation_update.py` run to rewrite it. In practice that run reported
`Documentation freshness is current; generated documentation is unchanged.` and wrote
nothing.

Affected assumption: that both sides of the comparison were wrong.

Implementation impact: none, in the reducing direction. The marker had been written by
`mark_staged()` from the index, so it already held LF-domain digests. Only the working-tree
reader disagreed. Normalizing that reader made it match what was already stored — the fix
converged on the existing baseline instead of replacing it.

Workaround complexity: none.

Simpler corrective option: not applicable.

Decision: dropped step 3 of the plan. `git status --short` after the change lists only the
two edited scripts, confirming no generated artifact churned.

### Finding: pre-push is still blocked, for an unrelated environment reason

Observation: with freshness fixed, `quality_gate.py --profile pre-push` still exits 1.
`ai-data-contract-manager` passes (29 passed, 9 skipped), but the
`mcp-servers/mcp-contract-forge` venv has no `pytest` installed — `pydantic` and `mcp` are
present, `pytest` and `fastapi` are not.

Affected assumption: that clearing the freshness gate would unblock `git push`.

Implementation impact: none on this task's code. It is an environment gap, not a defect in
the automation, and it predates this change.

Workaround complexity: none — it is an install, not a code change.

Simpler corrective option: `uv pip install --python mcp-servers/mcp-contract-forge/.venv pytest`
(uv 0.12.5 is on PATH).

Decision: reported, not performed. Modifying the environment is outside this task's scope and
is the maintainer's call.

## Deviations from the original plan

Step 3 (re-mark the freshness baseline) was dropped as unnecessary — see the first finding.
No other deviation.

## Verification

- [x] relevant unit tests pass — `test_documentation_update.py`, 3 tests, OK
- [ ] relevant integration tests pass — not applicable
- [ ] architecture/boundary tests pass when applicable — not applicable
- [x] configured quality gates pass — `pre-commit` profile is empty; `pre-push` fails only on
      the missing `pytest` recorded above
- [x] documentation freshness reviewed — `--check` reports `CURRENT`, exit 0
- [x] `docs/generated/documentation-impact.md` reviewed — unchanged, no churn
- [x] required curated documentation updated

Measured results:

| check | before | after |
| --- | --- | --- |
| tracked source files compared | 119 | 119 |
| digests differing on a clean tree | 37 | 0 |
| `--check` status / exit code | STALE / 1 | CURRENT / 0 |
| generated artifacts rewritten | — | none |
| files with a lone carriage return | 0 | 0 |

## Final result

`content_digest()` in `scripts/agent/common.py` hashes content with `CRLF` collapsed to `LF`,
and both `current_source_hashes()` and `staged_source_hashes()` call it, so the staged and
working-tree views of an unmodified file can no longer disagree. `sha256_file()` was removed
with its only caller. `repo_inventory.inspect_bytes()` normalizes before deriving `bytes`,
`lines` and `sha256`, making the generated inventory identical whichever path produced it;
its now-unused `hashlib` import was dropped.

The 37 phantom modifications are gone and `--check` exits 0 on a clean tree, so the freshness
gate no longer blocks `githooks/pre-push`.

## Unresolved items

- `pytest` is missing from the `mcp-servers/mcp-contract-forge` venv, so the configured
  `pre-push` quality profile still fails and `git push` remains blocked by that step. Not a
  code defect; needs an install decision from the maintainer.
- Branch `adcm_v5_consolidated` has no upstream, which is why `git pull` failed. Resolved by
  `git push -u origin adcm_v5_consolidated` when the maintainer chooses to push.

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

`docs/active-task/2026-08-23_freshness-eol/`

to:

`docs/history/2026-08-23_freshness-eol/`

Do not leave completed task documentation in `docs/active-task/`.
