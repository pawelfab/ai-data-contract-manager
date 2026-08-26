# Fast Copilot agent set

This setup is intentionally small and biased toward short cycle time.

## Model allocation

| Agent | Primary model | Role |
|---|---|---|
| Feature Coordinator | Claude Opus 5 | architecture, routing, final decisions |
| Repo Explorer | Gemini 3.6 Flash | search/read/summarize repository facts |
| Git Analyst | Claude Haiku 4.5 | status/diff/log/blame only |
| Test Runner | Claude Haiku 4.5 | targeted tests/checks and compressed diagnostics |
| Implementer | GPT-5.3-Codex | focused code changes |
| Reviewer | GPT-5.6 Luna | conditional high-value review |
| Docs Updater | Gemini 3.5 Flash | small documentation patches only |

Fallbacks are declared in each `.agent.md` file.

## Why this is faster than a large multi-agent pipeline

The coordinator does not automatically run every role. It first classifies the task:

- SIMPLE: direct work, optional one test run.
- STANDARD: Repo Explorer -> Implementer -> Test Runner; Reviewer only when warranted.
- COMPLEX: exploration + optional Git history -> Opus decision -> implementation -> tests -> review.

Normal changes should require roughly 2-4 subagent calls, not a fixed pipeline of many agents.

## Installation

Copy:

- `.github/agents/` into the repository's `.github/agents/`
- `.github/prompts/` into `.github/prompts/`

Do not blindly replace an existing `AGENTS.md`. Merge only the durable rules you want from `AGENTS.md.template`.

Review `.vscode/settings.recommended.json` and merge the settings you want into your existing workspace settings.

## Recommended VS Code settings

`chat.subagents.allowInvocationsFromSubagents=false` is deliberate. Worker agents must not spawn other workers; this prevents runaway agent trees and long execution chains.

`chat.useNestedAgentsMdFiles=false` is also deliberate for the first iteration. Nested always-available instructions can increase context and make behavior harder to predict. Enable them later only if service-local `AGENTS.md` files are short and demonstrably useful.

## Reasoning level

Keep the normal/default reasoning level for day-to-day work. Raise reasoning for Feature Coordinator only when the task is genuinely architectural or ambiguous. Do not use extended context simply because it is available.

## Prompt entry points

- `/implement-change` — implementation workflow.
- `/plan-change` — plan only; no code changes.
- `/inspect-current` — explain current behavior.
- `/review-change` — review current diff only.

## Important behavior

Subagents are stateless, so the coordinator sends a complete narrow task in one invocation. Each worker is explicitly instructed to return compressed evidence rather than raw code/logs.

The coordinator is restricted to the named workers through the `agents` frontmatter property. Workers have `agents: []`, so they cannot recursively delegate.

## If model identifiers differ

The files use current Copilot-qualified display names such as `Claude Opus 5 (copilot)`. If your VS Code build exposes a slightly different identifier, select the model in the custom agent editor and let VS Code rewrite the value. Model availability depends on Copilot plan and client version.
