# Start here — ADCM in VS Code / Codex

Put this package in the root of the ADCM repository so `AGENTS.md` is at repository root.

Suggested first request to the coding agent:

```text
Read AGENTS.md and the referenced ADCM docs first. Then inspect the actual repository and compare it with docs/CURRENT_STATE.md. Do not change code yet. Report only:
1. where the current code matches the documented architecture,
2. where it differs,
3. the exact execution path from CLI/API user message to Contract Forge and back,
4. the current cause of the repeated source.columns question,
5. the smallest implementation plan to fix partial column input and enable explicit LLM configuration.
Reference concrete files/classes/functions from the repo.
```

After you approve the plan, use:

```text
Implement the approved plan. Preserve the ownership rules from AGENTS.md. Add regression tests, run the relevant tests, then update docs/CURRENT_STATE.md. Update docs/DECISIONS.md only if an architectural decision changed.
```
