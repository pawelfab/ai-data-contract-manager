# Service boundaries

## ADCM owns

- chat/session lifecycle,
- direct user input and attachments,
- external evidence gathered at the user's request,
- source authority and provenance,
- accepted value history,
- LLM semantic interpretation,
- optional MCP tool selection,
- Forge stabilization loop,
- conflict presentation,
- YAML rendering.

ADCM must not parse `contract.json`, `$defs`, `$ref`, `x-contract-rules` or enrichment files.

## Contract Forge owns

- raw contract format,
- rule DSL format,
- schema/rule normalization,
- requirement discovery,
- validation,
- defaults and enrichment suggestions.

Forge must not own chat history, Jira access, LLM heuristics or user decisions.

## External/context MCPs own

They expose source-specific capabilities, for example:
- Atlassian: retrieve Jira/Wiki content,
- Schema Explorer: query BigQuery/schema/repository facts,
- Repository: locate and return existing YAMLs,
- Visualizer: produce Mermaid/diagram artifacts from structured inputs.

They should be deterministic where possible. Add PydanticAI inside an MCP only if that MCP itself has a real semantic/agentic responsibility, not merely because it uses MCP.
