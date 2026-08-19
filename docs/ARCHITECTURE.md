# ADCM — target architecture

## Repository layout

The repository root is a monorepo coordination layer, not a Python package:

```text
ai-data-contract-manager/                  # independently deployed ADCM service
mcp-servers/mcp-contract-forge/            # independently deployed Forge service
docs/                                      # cross-service architecture and decisions
```

Each service owns its `src`, tests, documentation, `pyproject.toml`, lock snapshot
and `.venv`. The services do not import one another's Python packages.

## 1. Component view

```text
+-----------------------------+
| CLI now / Web UI later      |
+--------------+--------------+
               |
               v
+-----------------------------+
| ADCM API / Orchestrator     |
|                             |
| - session flow              |
| - conversation history      |
| - stair-step loop           |
| - conflict handling         |
+------+----------------------+ 
       |
       +-------------------+
       |                   |
       v                   v
+--------------+    +------------------+
| Heuristics   |    | Semantic Resolver|
| deterministic|    | LLM/Pydantic AI  |
+------+-------+    +---------+--------+
       |                      |
       +-----------+----------+
                   |
             candidate facts
                   |
                   v
+--------------------------------------+
| Forge Gateway                        |
| - MCP Streamable HTTP client         |
| - response DTO validation            |
+------------------+-------------------+
                   |
                   v
+--------------------------------------+
| Contract Forge MCP                   |
|                                      |
| - canonical contract state           |
| - schema navigator                   |
| - enrichment engine                  |
| - defaults                           |
| - pending requirement discovery      |
| - validation                         |
| - provenance/diagnostics             |
+------------------+-------------------+
                   |
          +--------+---------+
          |                  |
          v                  v
   contract.json       enrichment rules

Future:

ADCM Orchestrator ---> Schema Explorer MCP ---> BigQuery / Git repo
        |
        +---------- context ----------> Contract Forge MCP
```

The physical service boundary is mandatory even for the minimal local demo. ADCM
tests replace the MCP boundary with a fake gateway; they do not run Forge in-process.

## 2. Session state

There are conceptually two different state domains:

### Conversation state (ADCM)
Contains:
- transcript;
- user facts/partial facts;
- UI/session metadata;
- semantic extraction context.

### Canonical contract state (Forge)
Contains:
- current contract document;
- active source system/type;
- value origins/provenance;
- applied enrichment/default history;
- pending requirements;
- validation errors.

Do not collapse these into one mutable dictionary owned by ADCM.

## 3. Stair-step algorithm

Pseudo-flow:

```python
state = forge.start_session()

while not state.finished:
    if state.pending:
        candidates = heuristics.resolve(history, state.pending)

        if not candidates:
            candidates = llm.resolve(history, state.pending)

        if candidates:
            state = forge.submit(candidates)
            continue

        user_answer = ask_user(state.pending[0])
        store_in_history(user_answer)
        continue

    state = forge.refresh()
```

In practice, the orchestrator needs protection against loops (`max_auto_steps`) and should distinguish:
- no candidate found;
- candidate rejected by Forge;
- partial candidate accepted/stored;
- a genuinely new requirement exposed.

A repeated identical question after a rejected parse is poor UX unless accompanied by a reason and a narrower clarification.

## 4. Value provenance

Recommended origin model:

```text
USER
SYSTEM_ENRICHMENT
GENERIC_ENRICHMENT
SCHEMA_DEFAULT
STRUCTURAL
```

Recommended precedence:

```text
USER
  > SYSTEM_ENRICHMENT
  > GENERIC_ENRICHMENT
  > SCHEMA_DEFAULT
  > STRUCTURAL
```

Deterministic and LLM extraction are ADCM metadata, not Forge business origins. A
fact extracted from the user's words by either method reaches Forge as `USER`.
Recency between multiple USER facts belongs to ADCM conversation memory, not to
Forge precedence.

Forge should expose origins for debugging and later UI explanations such as:

> `targets.bronze.table.dataset` was filled by SAP system enrichment rule `sap.bronze.dataset`.

`ForgeState.overridable` is also the controlled edit surface. It contains lower-origin
values and existing semantic scalar USER values that may receive a later USER
correction, but excludes explicit workflow gates. Structured USER values stay on the
pending/partial protocol because canonical items may contain nested defaults or
enrichments. ADCM compares `current_value` with its latest UserFact before submitting,
so an unchanged USER value is not replayed. Forge still validates the candidate and
owns the canonical write; it does not compare message sequence.

## 5. Schema navigation

The generic Forge schema layer should support as much as practical through standard JSON Schema 2020-12:
- local `$ref`;
- `properties`;
- `required`;
- `default`;
- `enum`/`const`;
- `oneOf` + discriminator for the known source pattern;
- nested objects/arrays;
- descriptions/questions;
- final validator.

When a requirement can be expressed with standard JSON Schema (`if/then`, `dependentRequired`, `oneOf`, etc.), prefer that over an opaque textual custom rule.

## 6. Enrichment engine

Enrichment is executed by Contract Forge. Rules should be machine-readable and registry-backed.

Typical actions:
- `set_default`;
- `copy_value`;
- `format_value`;
- controlled derivation of target columns;
- environment-driven enrichment through explicit context.

Unknown actions should be rejected or reported as unsupported. They must not be interpreted by the LLM from their natural-language message.

## 7. Partial facts

ADCM needs a representation for facts that are useful but do not yet satisfy a complete Forge field.

Example:

```json
{
  "path": "source.columns",
  "partial": [
    {"name": "data_d"},
    {"name": "sap1"},
    {"name": "sap2"},
    {"name": "sap3"}
  ],
  "missing": ["dataType"]
}
```

This may live only in ADCM conversation memory until enough information exists to submit a valid `source.columns` candidate to Forge.

Do not write invalid partial structures into the canonical contract unless Forge explicitly defines a draft/partial contract protocol.

## 8. API boundary for future web UI

The web UI should remain a renderer of conversation state, not a second contract engine.

Minimal API shape:

```text
POST /sessions
POST /sessions/{id}/messages
GET  /sessions/{id}
GET  /health
```

A response should be able to contain:
- assistant message;
- status;
- pending path/type/allowed values;
- current contract snapshot;
- validation/diagnostic details;
- optional provenance/partial-input hints.

This allows later specialized widgets for enums, tables or columns without changing Contract Forge ownership.

## 9. Schema Explorer integration

Recommended orchestration:

```text
ADCM
  -> Schema Explorer: environment/repo facts
  <- structured context
  -> Contract Forge: candidate + explorer context
  <- enrichment/validation/pending
```

Do not make Contract Forge depend on network calls to Schema Explorer for every field unless there is a strong reason. Keep external environment lookups explicit, cacheable and observable.

## 10. Production concerns kept outside the minimal core

Not required for the first terminal demo, but architecture should leave room for:
- durable session store;
- auth/user identity propagation;
- audit/provenance logs;
- Cloud Run multi-instance behavior;
- contract/rules compatibility versioning;
- existing-contract editing workflow;
- optional decisions (`x-acdm-optional-decision`);
- Schema Explorer MCP;
- web UI.
