---
name: plan-change
description: Produce an implementation plan without editing code.
agent: Feature Coordinator
---

Plan the requested change but DO NOT implement it.

Use Repo Explorer once if implementation facts are unknown.
Use Git Analyst only if history materially affects the design.
Do not invoke Implementer, Test Runner, Reviewer, or Docs Updater.

Return a compact plan containing:
1. current behavior,
2. chosen approach and why,
3. exact files/symbols likely to change,
4. implementation steps,
5. tests/acceptance criteria,
6. real risks or unresolved facts.

Avoid speculative abstractions and avoid redesign outside the requested scope.
