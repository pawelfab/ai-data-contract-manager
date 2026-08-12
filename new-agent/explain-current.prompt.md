---
name: explain-current
description: Explain current repository behavior without changing code.
argument-hint: What behavior, flow, module, class, or method should be explained?
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'execute']
---

MODE: EXPLAIN

Answer how the repository currently works for:

`${input:question:Describe the behavior, flow, module, class, or method}`

Use maintained architecture documentation first. Verify only unresolved claims. Do not plan or implement changes.
