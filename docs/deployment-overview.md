# Deployment overview

Each service is independently buildable and deployable.

```text
ai-data-contract-manager/
  .venv
  pyproject.toml
  Dockerfile

mcp-servers/mcp-contract-forge/
  .venv
  pyproject.toml
  Dockerfile
```

Production ADCM may use a PydanticAI Google Cloud model (`google-cloud:<model>`) through Application Default Credentials. Remote MCP connections use Streamable HTTP.

Forge is configured separately and does not install PydanticAI.

Future logging is intentionally a later change:
- application logs: local file adapter / GCP stdout adapter,
- session audit logs: local JSONL adapter / BigQuery adapter.
