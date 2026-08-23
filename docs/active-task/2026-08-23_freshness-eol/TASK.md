---
status: active
created: 2026-08-23
type: fix
services: [scripts/agent]
---

# Task: freshness must ignore checkout line endings

## Problem

On a clean working tree with everything committed, `doc_freshness.py --check` reported
`STALE` with 37 modified files. Nothing had changed.

`core.autocrlf=true` is set and the repository has no `.gitattributes`, so Git stores `LF`
in the index and writes `CRLF` into the working tree. The freshness marker is written from
the staged index by `mark_staged()` during the pre-commit hook, but `--check` compares it
against files read from disk. The same unmodified file therefore hashes differently on the
two paths.

Because `githooks/pre-push` runs `doc_freshness.py --check` under `set -eu`, `git push` was
blocked, and no existing command could resolve it: marking current from the working tree
cleared the check until the next commit re-marked from the index, then it went stale again.

## Goal

`doc_freshness.py --check` reports `CURRENT` on a clean working tree, and stays `CURRENT`
after a commit whose marker was written from the Git index.

## Scope

Included:
- line-ending-normalized content hashing shared by the staged and working-tree paths;
- the same normalization in the generated repository inventory, whose `sha256`, `bytes` and
  `lines` fields drifted for the same reason.

## Out of scope

- `.gitattributes` with `* text=auto eol=lf` plus `git add --renormalize .` — the canonical
  Git fix, rejected here because it rewrites line endings across the whole repository and
  changes the working tree for every clone;
- changing `core.autocrlf`, which is a local setting and would not help other clones.

## Constraints

- both hash paths must agree by construction, not by convention, so the marker stays valid
  whichever command wrote it;
- normalization must not corrupt content — collapsing `CRLF` to `LF` must not touch a
  carriage return that stands on its own.

Constraints control expected scope, but they are not proof that an input, contract, schema or
assumption is correct. If preserving a constraint requires disproportionate workaround
complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [x] staged and working-tree hashes agree for all 119 tracked source files
- [x] `--check` reports `CURRENT` on a clean tree
- [x] no tracked source file contains a lone carriage return
- [x] `scripts/agent/tests/test_documentation_update.py` still passes
- [x] generated documentation does not churn after the change

## Relevant references

- issue/ticket: —
- prior task/decision: `docs/active-task/2026-08-23_task-doc-gate/` (commit `dbe2121`)
- documentation: `docs/documentation-automation.md` § Freshness
