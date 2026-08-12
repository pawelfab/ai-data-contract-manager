---
name: sync-architecture-docs
description: Synchronize architecture documentation with current code without changing application code.
argument-hint: Optional module, paths, commit, or diff scope.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'edit', 'execute']
---

MODE: DOC_SYNC

Synchronize repository knowledge for:

`${input:scope:Current diff, named module, paths, or all stale files}`

Do not modify application code. Update only documentation, generated inventory, and the freshness marker.
