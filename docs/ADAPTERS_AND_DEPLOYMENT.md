# Adapters, local execution and deployment

## LLM adapter

`SemanticInterpreterPort` isolates the semantic engine. Production can use `PydanticAIInterpreter`; local/offline tests use `RuleBasedInterpreter` or a fake.

The application should not depend directly on a particular Vertex/OpenAI/local model API. Pydantic AI is itself multi-provider, but the ADCM port also prevents application logic from depending on Pydantic AI APIs.

## Session persistence

Reference adapters:

- `InMemorySessionRepository` — tests/local ephemeral runs;
- `JsonFileSessionRepository` — local durable prototype.

Production can add BigQuery/Postgres/Firestore/etc. behind the same port. Cloud Run instances must not rely on process memory for durable session state.

## Logging vs audit

Keep them separate.

Technical log examples:
- MCP latency;
- retries;
- model/provider errors;
- HTTP status.

Audit examples:
- value changed from A to B;
- user value overrode enrichment;
- candidate selected from a specific evidence item;
- contract revision validated.

Local audit can use JSONL; production can use BigQuery or another durable append store.

## MCP transport

Pydantic AI currently supports MCP clients/toolsets including remote Streamable HTTP and local transports. Keep that detail in `adapters/mcp`. The application port should describe business capabilities, not protocol methods.

For a future per-call token policy or a connector that needs a different connection lifecycle, implement a separate adapter while preserving the same port.

## Configuration

Composition root (`main.py` in a real service) selects adapters from configuration:

```text
LOCAL:
SemanticInterpreter = local/provider adapter
SessionRepository    = JSON/SQLite
AuditSink             = JSONL
ContractForge         = local/mock or remote MCP

CLOUD:
SemanticInterpreter = Pydantic AI + Vertex/OpenAI provider
SessionRepository    = durable cloud store
AuditSink             = BigQuery/Cloud logging target
ContractForge         = Streamable HTTP MCP adapter
```
