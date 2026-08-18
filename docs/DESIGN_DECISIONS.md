# Design decisions

## Why not let the LLM own the contract object?

Because chat semantics and schema authority have different failure modes. A model may map a concept to a plausible but nonexistent path. ADCM therefore stores semantic knowledge separately and projects into a draft only after MCP authorization.

## Why keep full chat history if state is structured?

Structured state is operational truth; raw chat is semantic context and evidence. A later sentence such as "change the previous separator" may need linguistic context, while revisions need a stable application record.

## Why not pass the entire ConversationState to the LLM?

It is larger than necessary and exposes implementation/audit details. `AgentContextBuilder` creates a purpose-built projection: current stage, active signals/preferences, known values, legal paths, pending requirements and recent messages.

## Why deterministic workflow rather than agent tool-loop?

Order, precedence and schema legality are business rules. Keeping them in Python makes behavior testable, cheap and predictable. LLM calls remain limited to semantics.

## Why ports/adapters without heavy DDD?

External dependencies genuinely vary (model/provider, MCP transport, logging, session storage, enrichment storage), so ports are useful. The business domain is small enough that aggregates/repository-per-entity/event-bus/CQRS would add noise.
