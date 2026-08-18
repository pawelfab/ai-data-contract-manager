# ADCM architecture

## 1. Goal

ADCM is a conversational orchestrator for contract onboarding. The application should remain small and deterministic while delegating contract authority to MCP Contract Forge and semantic interpretation to an LLM.

The system is intentionally **not** designed as an autonomous agent that sees a whole contract and decides what to ask. Contract Forge progressively discloses the current stage and legal paths. ADCM fast-forwards through stages using knowledge already extracted from the conversation and asks the user only when deterministic resolution cannot continue.

## 2. Top-level architecture

```text
User/UI
  |
  v
ChatService
  |
  +--> SemanticInterpreter (Pydantic AI adapter)
  |        -> intent/signals/preferences/corrections/typos
  |
  v
ADCM ConversationState
  |  signals, preferences, evidence, candidates, revisions
  |
  v
WorkflowRunner --------------------------------------+
  |                                                  |
  +--> ContractForgePort --> Contract Forge MCP       |
  |       schema / allowed paths / workflow           |
  |       defaults / enrichments / validation         |
  |                                                  |
  +--> CapabilityRouter --> Schema Explorer MCP       |
  |                        Repository MCP             |
  |                        future MCPs                |
  |                                                  |
  v                                                  |
CandidateResolver -> DraftProjector ------------------+
  |
  v
ContractDraft
```

## 3. Authority boundaries

### LLM authority
LLM may interpret language but has no contract authority. It emits typed semantic facts and proposed interpretations. It does not define paths, required fields or ordering.

### ADCM authority
ADCM owns conversation/session knowledge, evidence, provenance, precedence, revisions and orchestration.

### Contract Forge authority
Contract Forge owns schema legality, allowed paths, dynamic stages, defaults, enrichments and validation.

### Other MCP authority
External MCPs own facts from their systems (for example table existence) but return them as findings/evidence/candidates. ADCM decides how they participate; they never write the draft directly.

## 4. Why this prevents the original failure mode

A model never receives an unrestricted list of all contract fields and then immediately exposes it to the user. The user response is generated only after:

1. semantic interpretation;
2. state reconciliation;
3. the deterministic MCP workflow loop;
4. candidate resolution;
5. legal draft projection.

Contract Forge exposes only the current stage. ADCM can apply data already present in the user message without another user turn, and repeatedly call MCP until a genuinely missing value blocks progress.

## 5. Ports and adapters

Ports isolate replaceable infrastructure:

- `SemanticInterpreterPort`: Pydantic AI today, another library/provider locally tomorrow.
- `ContractForgePort`: MCP HTTP/stdio implementation or local fake in tests.
- `SessionRepositoryPort`: memory/file locally, database in cloud.
- `AuditSinkPort`: JSONL locally, BigQuery/Cloud Logging/other durable sink in production.
- `CapabilityHandlerPort`: Schema Explorer and future MCPs.

Domain/application code imports ports, never concrete adapters.

## 6. One-agent policy

Use one semantic Pydantic AI agent rather than a multi-agent system. The agent performs language tasks only. Workflow orchestration remains Python. This reduces token use, race conditions and accidental leakage of future contract requirements.

## 7. Future extensions

The architecture supports:

- Schema Explorer MCP for table-name checks and schema discovery;
- GitHub-backed enrichment repositories behind Contract Forge;
- existing-contract import and edit flows;
- naming-policy capabilities;
- data catalog / DQ MCPs;
- external persistence and audit stores;
- richer UI response generation without changing domain rules.
