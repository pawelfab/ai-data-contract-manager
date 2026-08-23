# Start here — ADCM monorepo in VS Code / Codex

Open the monorepo root so `AGENTS.md`, `docs/`, `ai-data-contract-manager/` and
`mcp-servers/` are visible together. The root itself is not an installable Python
package; run commands from the relevant service directory.

Suggested first request to the coding agent:

```text
Read AGENTS.md and the referenced ADCM docs first. Then inspect the actual repository and compare it with docs/CURRENT_STATE.md. Do not change code yet. Report only:
1. where the current code matches the documented architecture,
2. where it differs,
3. the exact execution path from CLI/API user message to Contract Forge and back,
4. the smallest implementation plan to fix partial column input and enable explicit LLM configuration.
Reference concrete files/classes/functions from the repo.
```

After you approve the plan, use:

```text
Implement the approved plan. Preserve the ownership rules from AGENTS.md. Add regression tests, run the relevant tests, then update docs/CURRENT_STATE.md. Update docs/DECISIONS.md only if an architectural decision changed.
```
