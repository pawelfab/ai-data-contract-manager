---
status: active
created: 2026-08-23
type: feature
services: [scripts/agent]
---

# Task: enforce one task document per code-changing commit

## Problem

`docs/documentation-automation.md` and `AGENTS.md` require every feature, fix or material
refactor to own exactly one task folder — `docs/active-task/YYYY-MM-DD_task-name/` while in
flight, moved unchanged to `docs/history/YYYY-MM-DD_task-name/` on completion.

Nothing enforced that rule. `check_staged()` in `scripts/agent/doc_freshness.py` had a
single gate: staged documentation-relevant code had to be accompanied by something matching
`documentation_evidence_patterns`. Those patterns deliberately cover a wide curated surface
(`^ai-data-contract-manager/docs/`, `^mcp-servers/mcp-contract-forge/docs/`, the top-level
curated documents), so editing any arbitrary service document already satisfied the gate.

The task-lifecycle requirement cannot be expressed by tuning that single list: narrowing it
breaks the curated-documentation gate, widening it changes nothing.

## Goal

`python scripts/agent/doc_freshness.py --check-staged` reports two independent failures with
distinct reasons — missing curated documentation, and missing task documentation — and the
pre-commit hook blocks a commit that lacks either.

## Scope

Included:
- a second, independent task-documentation gate inside `check_staged()`, keyed on
  `task_documentation_active_pattern` / `task_documentation_completed_pattern` and never on
  `documentation_evidence_patterns`;
- `staged_task_docs` in the JSON payload and in the human-readable output;
- repair of the over-escaped regexes in `scripts/agent/config.json`;
- the same task-documentation keys added to `scripts/agent/config.example.json`.

## Out of scope

- the untracked `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow/` folder
  (plural directory, `-` date separator, non-conforming filenames) — it satisfies neither
  the documented convention nor the new gate, and its migration belongs to that task;
- any change to `githooks/pre-commit`, which already fails on a non-zero exit code.

## Constraints

- the task-documentation check must stay separate from `documentation_evidence_patterns`,
  otherwise changing any arbitrary service document would satisfy the task-lifecycle
  requirement;
- the singular `docs/active-task/` convention is authoritative, matching `AGENTS.md`,
  `docs/documentation-automation.md`, `docs/templates/task/` and `DOCS_MIGRATION_PLAN.md`;
- moving a task folder to `docs/history/` must not be blocked by the gate.

Constraints control expected scope, but they are not proof that an input, contract, schema or
assumption is correct. If preserving a constraint requires disproportionate workaround
complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [x] staged relevant code with curated documentation but no task document reports `STALE`
- [x] staged relevant code with a task document but no curated documentation reports the
      curated-documentation reason
- [x] both missing produces a combined reason, not one that hides the other requirement
- [x] a completion move (`docs/active-task/` → `docs/history/`) passes the gate
- [x] `staged_task_docs` is present in `--json` output and in the human-readable output

## Relevant references

- issue/ticket: —
- prior task/decision: `docs/documentation-automation.md` § Active task workflow
- documentation: `docs/documentation-automation.md`, `AGENTS.md`
