---
name: plan-change
description: Quickly create an implementation-ready class-and-method-level plan without subagents or application-code changes.
argument-hint: Describe the feature, fix, or refactor to plan.
agent: Planner Fast
tools: ['read', 'search', 'edit', 'execute', 'todos']
---

Create a fast implementation plan for:

`${input:change:Describe the requested change and desired outcome}`

Use maintained architecture documentation first, then verify only the affected source symbols, callers, and tests. Save the plan under `docs/architecture/contracts/` with `STATUS: FAST_PLAN`.

Do not invoke subagents. Do not modify application code.
