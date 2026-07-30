---
name: plan-change
description: Produce a reviewed class-and-method-level implementation contract without changing application code.
argument-hint: Describe the feature, fix, or refactor to plan.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'edit', 'execute', 'todos']
---

MODE: PLAN

Create a reviewed implementation contract for:

`${input:change:Describe the requested change and desired outcome}`

The final artifact must be saved under `docs/architecture/contracts/`. Do not modify application code.
