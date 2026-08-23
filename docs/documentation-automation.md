# Documentation automation

The repository separates curated documentation from deterministic generated navigation.

## Curated documentation

Curated documents describe architecture, current behavior, accepted decisions and service semantics.

Important sources:
- `docs/architecture-guardrails.md`;
- `docs/architecture.md`;
- `docs/CURRENT_STATE.md`;
- `docs/DECISIONS.md`;
- `docs/KNOWN_ISSUES.md`;
- service-specific documentation;
- current task documentation under `docs/active-task/`.

Generated files never replace these documents.

## Generated documentation

`scripts/agent/documentation_update.py` regenerates:

- `docs/generated/repository-inventory.json` — machine-readable source inventory;
- `docs/generated/repository-map.md` — mechanically generated file/symbol navigation map;
- `docs/generated/documentation-impact.md` — changed source paths and curated documents to review;
- `docs/.freshness.json` — source snapshot represented by the generated documentation.

The repository map is a navigation aid. Coding agents should inspect only relevant sections and then verify behavior in actual code/tests.

## Freshness

`doc_freshness.py` compares configured source hashes with the documented source snapshot.

The freshness result may be:
- `CURRENT`;
- `STALE`;
- `UNKNOWN`.

A stale result means relevant source changed after the last documentation synchronization. It does not automatically mean every curated document must change.

Source hashes are computed over line-ending-normalized content (`CRLF` collapsed to `LF`). The marker is written from the staged Git index during a commit but compared against working-tree files, and on a `core.autocrlf` checkout those two byte streams differ for every text file Git converted. Without the normalization, a clean working tree reports as stale forever, and because `githooks/pre-push` runs `--check`, pushing is blocked with no command able to resolve it.

## Staged commit workflow

When documentation-relevant source files are staged, the pre-commit workflow can generate artifacts from the staged Git index and stage those generated artifacts in the same commit.

Generated artifacts intentionally do **not** count as curated documentation evidence.

If documentation-relevant code changed, review the curated documents indicated by `docs/generated/documentation-impact.md` and update only those whose documented responsibility or behavior actually changed.

### Two independent staged requirements

`doc_freshness.py --check-staged` enforces two separate requirements when documentation-relevant code is staged:

1. **curated documentation evidence** — at least one staged document matching `documentation_evidence_patterns` and not `documentation_non_evidence_patterns`;
2. **task documentation** — at least one staged `IMPLEMENTATION.md` matching `task_documentation_active_pattern` or `task_documentation_completed_pattern`.

The second check never consults `documentation_evidence_patterns`. Those patterns cover a wide curated surface, so without the separation, editing any arbitrary service document would satisfy the task-lifecycle requirement.

Either requirement can be relaxed independently through `require_docs_for_staged_relevant_code` and `require_task_doc_for_staged_relevant_code`.

The reported reason names which requirement is unmet, and the result lists `staged_architecture_docs` and `staged_task_docs` separately.

Moving a completed task folder from `docs/active-task/` to `docs/history/` stages both the removed and the added path, so completion commits satisfy the task-documentation requirement.

There is no post-commit generator that modifies the working tree after a successful commit.

## Active task workflow

Every feature, fix or material refactor should have:

```text
docs/active-task/YYYY-MM-DD_task-name/
├── TASK.md
└── IMPLEMENTATION.md
```

`TASK.md` records the requested outcome and scope.

`IMPLEMENTATION.md` records:
- ownership and boundaries;
- implementation plan;
- expected change surface;
- tests;
- architecture risks;
- unexpected findings;
- deviations from the original plan;
- final result.

It is not a minute-by-minute activity log.

Before declaring the task complete:

1. run relevant tests and configured quality gates;
2. run/review documentation generation and freshness;
3. inspect `docs/generated/documentation-impact.md`;
4. update only relevant curated documentation;
5. update the final result in `IMPLEMENTATION.md`;
6. mark the task completed;
7. move the whole task folder to `docs/history/YYYY-MM-DD_task-name/`.

Completed task folders must not remain in `docs/active-task/`.

## Historical documentation

`docs/history/` is not mandatory reading.

Use it only when:
- investigating a regression;
- explaining why a design exists;
- a current decision/task explicitly references earlier work.

## Manual commands

```powershell
python scripts/agent/documentation_update.py
python scripts/agent/documentation_update.py --staged
python scripts/agent/doc_freshness.py --check
python scripts/agent/install_git_hooks.py
```

The exact configured source/document mappings remain controlled by the agent documentation configuration.
