---
name: bootstrap-repository-knowledge
description: Build the initial architecture knowledge base for an existing repository.
argument-hint: Optional scope or module grouping instructions.
agent: Feature Coordinator
tools: ['agent', 'read', 'search', 'edit', 'execute', 'todos']
---

MODE: BOOTSTRAP_DOCS

Build the initial repository knowledge base.

Scope or grouping guidance:

`${input:scope:Whole repository, or name the source roots/modules to document}`

Run mechanical inventory first. Analyze independent modules in parallel with bounded Code Verifier subagents. Create curated module, flow, and symbol documentation. Mark documentation current only after verification.
