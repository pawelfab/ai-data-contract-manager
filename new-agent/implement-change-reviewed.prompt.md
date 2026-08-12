---
name: implement-change-reviewed
description: Plan, implement, independently review, test, and document a change using the full multi-agent workflow.
argument-hint: Describe the exact change to implement and independently review.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'edit', 'execute', 'todos']
---

MODE: IMPLEMENT_REVIEWED

Implement:

`${input:change:Describe the requested code change and acceptance outcome}`

Use the complete contract-first workflow: current-state analysis, bounded code verification, reviewed contract, implementation, independent implementation review, required correction cycles, quality checks, architecture documentation update, inventory regeneration, and freshness verification.
