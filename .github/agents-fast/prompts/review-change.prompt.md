---
name: review-change
description: Review the current change set for material correctness issues.
agent: Feature Coordinator
---

Review the current change set.
Invoke Reviewer directly with the scope of the current diff.
Do not run Repo Explorer first unless Reviewer reports that one critical dependency cannot be understood from the changed files.
Do not implement fixes unless explicitly requested.
Return only material findings and the final verdict.
