# Documentation migration plan

## Replace with generated final versions

Root:
- `AGENTS.md`
- `docs/architecture-guardrails.md`
- `docs/architecture.md`
- `docs/CURRENT_STATE.md`
- `docs/documentation-automation.md`

ADCM:
- `ai-data-contract-manager/docs/architecture.md`

Contract Forge:
- `mcp-servers/mcp-contract-forge/README.md`
- `mcp-servers/mcp-contract-forge/docs/architecture.md`
- `mcp-servers/mcp-contract-forge/docs/contract-format.md`
- `mcp-servers/mcp-contract-forge/docs/requirement-discovery.md`

## Add

- `docs/active-task/README.md`
- `docs/templates/task/TASK.md`
- `docs/templates/task/IMPLEMENTATION.md`
- `ai-data-contract-manager/docs/planned/logging.md`
- `mcp-servers/mcp-contract-forge/docs/history/contract-repair-note.md`

## Move

Root historical documents:
- `docs/CONSOLIDATED_ANALYSIS.md`
  → `docs/history/architecture/CONSOLIDATED_ANALYSIS_v0.4.md`

- `docs/MIGRATION_V4_TO_V5.md`
  → `docs/history/migrations/MIGRATION_V4_TO_V5.md`

- `docs/stages.md`
  → `docs/history/planning/delivery-stages-1-9.md`

Agent onboarding:
- `docs/START_HERE.md`
  → `docs/agent/START_HERE.md`

ADCM planned work:
- `ai-data-contract-manager/docs/logging.md`
  → replaced by `ai-data-contract-manager/docs/planned/logging.md`

Forge historical repair:
- `mcp-servers/mcp-contract-forge/docs/contract-repair-note.md`
  → replaced by `mcp-servers/mcp-contract-forge/docs/history/contract-repair-note.md`

## Delete after content has been merged

Root documents whose current content is merged into `docs/architecture.md`:
- `docs/service-boundaries.md`
- `docs/integration-flow.md`
- `docs/system-overview.md`

Forge:
- `mcp-servers/mcp-contract-forge/docs/normalized-contract.md`
  - its useful content is merged into Forge `docs/architecture.md`

## Keep unchanged for now

Root:
- `README.md`
- `docs/DECISIONS.md`
- `docs/KNOWN_ISSUES.md`
- `docs/deployment-overview.md`

ADCM:
- `CHANGELOG.md`
- `README.md`
- `docs/contract-state.md`
- `docs/llm-heuristics.md`
- `docs/ports-and-adapters.md`
- `docs/session-flow.md`

Contract Forge:
- `CHANGELOG.md`
- `docs/enrichment.md`
- `docs/mcp-api.md`
- `docs/ports-and-adapters.md`
- `docs/rules-engine.md`

Generated:
- keep `docs/generated/*` generated mechanically;
- do not edit generated files manually.

## Recommended task lifecycle

Before implementation:

```text
docs/active-task/YYYY-MM-DD_task-name/
├── TASK.md
└── IMPLEMENTATION.md
```

After implementation, tests and documentation synchronization:

```text
docs/history/YYYY-MM-DD_task-name/
├── TASK.md
└── IMPLEMENTATION.md
```

## Follow-up configuration change

Update the documentation automation configuration so that:
- `docs/active-task/**` counts as curated task documentation evidence;
- `docs/history/**` can contain completed task documentation;
- `docs/generated/**` never counts as curated evidence;
- documentation mappings point to the new/moved document paths;
- removed root files are deleted from documentation mappings.

The supplied Python scripts already support the needed conceptual split; exact regex/path edits depend on the repository `scripts/agent/config.json` or `config.example.json`, which was not included in the reviewed files.
