---
name: implement-change
description: Implement a change using the fast coordinator workflow.
agent: Feature Coordinator
---

Implement the requested change.

Optimize for short cycle time and small context:
- use the SIMPLE / STANDARD / COMPLEX routing rules,
- do not invoke agents ceremonially,
- for STANDARD work use at most one repository exploration before implementation,
- use Git Analyst only when history or current diff is genuinely relevant,
- use Reviewer only when the review gate is met,
- keep each delegated task narrow and request compressed summaries.

If repository facts conflict with the requested design, report the conflict instead of building a complex workaround.
