---
name: implement-change
description: Implement, test, self-review, and document a bounded change using one agent and no subagents.
argument-hint: Describe the exact change and expected result.
agent: Feature Fast
tools: ['read', 'search', 'edit', 'execute', 'todos']
---

Implement:

`${input:change:Describe the requested code change and acceptance outcome}`

Use the fast single-agent workflow. Read relevant architecture documentation, inspect only affected code, implement the smallest coherent change, add tests, run relevant checks, self-review the complete diff, update impacted architecture documentation, regenerate repository inventory, and verify freshness.

Do not invoke subagents.
