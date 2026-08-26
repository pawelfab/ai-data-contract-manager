---
name: inspect-current
description: Explain how a specific behavior currently works without modifying code.
agent: Feature Coordinator
---

Answer how the requested behavior currently works.

Use Repo Explorer for one focused repository question unless the necessary file is explicitly named and can be read directly.
Do not implement, edit, run tests, review, or update documentation.
Use Git Analyst only if the user explicitly asks about history or when a change was introduced.

Return the explanation, relevant files/symbols, and any uncertainty. Keep it concise.
