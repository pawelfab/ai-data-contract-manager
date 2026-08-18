---
name: review-current-change
description: Independently review the current implementation diff without changing files.
argument-hint: Describe the intended behavior, contract path, or review scope.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'execute', 'todos']
---

MODE: REVIEW_ONLY

Independently review the current change for:

`${input:scope:Describe expected behavior, acceptance criteria, contract path, or diff scope}`

Inspect the complete relevant diff, callers, tests, compatibility, errors, transactions, concurrency, security, and documentation impact. Do not edit any file.
