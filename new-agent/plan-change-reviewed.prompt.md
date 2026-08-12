---
name: plan-change-reviewed
description: Create an independently reviewed implementation contract without changing application code.
argument-hint: Describe the feature, fix, or refactor to analyze and review.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'edit', 'execute', 'todos']
---

MODE: PLAN_REVIEWED

Create a reviewed implementation contract for:

`${input:change:Describe the requested change and desired outcome}`

Use current-state documentation analysis, bounded code verification, solution architecture, independent contract review, and contract finalization. Save the final contract under `docs/architecture/contracts/`.

Do not modify application code.
