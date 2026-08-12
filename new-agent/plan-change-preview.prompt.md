---
name: plan-change-preview
description: Analyze and present a concise implementation plan in chat without changing any repository file.
argument-hint: Describe the feature, fix, or refactor to preview.
agent: Planner Fast
tools: ['read', 'search', 'execute', 'todos']
---

Prepare an implementation plan for:

`${input:change:Describe the requested change and desired outcome}`

Return the complete plan in chat. Do not invoke subagents. Do not create or modify any repository file.

Include exact affected files and symbols, proposed signatures, tests, implementation order, risks, assumptions, and unresolved decisions.
