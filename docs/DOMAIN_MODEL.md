# Domain model and provenance

## Primary pipeline

```text
RawMessage
  -> Evidence
  -> Signal / Preference
  -> ValueCandidate
  -> ResolvedValue
  -> ContractDraft
```

## Signal

A `Signal` is a schema-agnostic fact extracted from user language. It does not need a contract path.

Example given before source type is known:

```json
{"concept":"field_delimiter","value":";","status":"unbound"}
```

It can remain unbound for several MCP stages. When Contract Forge later authorizes a path declaring `field_delimiter` as a supported concept, `SignalBinder` may create a candidate.

## Preference

A `Preference` is cross-cutting user intent. Example: `encoding=UTF-8` globally or `encryption=false`. A preference is not a contract value by itself. `PreferenceExpander` creates candidates only for currently legal paths that declare the matching concept.

## ValueCandidate

A candidate is a concrete value proposed for a concrete legal path. It records origin, evidence and optional confidence/priority. Multiple candidates can coexist.

Typical sources:

- explicit user value;
- user preference;
- existing contract;
- Schema Explorer finding;
- MCP enrichment;
- MCP derived value;
- MCP default.

## Resolution

`CandidateResolver` is deterministic. Default precedence in this reference implementation is:

```text
user explicit      100
user preference     90
existing contract   80
external schema     70
MCP enrichment      60
MCP derived         40
MCP default         10
```

The policy is data/code, never an LLM decision. Priorities can later be injected/configured.

## Evidence

Evidence explains where information came from: a user message, MCP enrichment, default, external schema, GitHub source or derivation. Candidates reference evidence IDs rather than embedding the entire history.

## Revisions

A correction supersedes the previous semantic fact instead of deleting it. `Revision` records the change. This allows audit questions such as:

- who/what supplied the current value;
- what value existed previously;
- why it changed;
- whether the current value overrides an enrichment/default.

## ContractDraft

The draft intentionally contains only path/value material that could become the final contract. It does not contain evidence, signals or preferences.

`DraftProjector` is the security/authority barrier: it projects resolved values only when `path in allowed_paths` supplied by Contract Forge.
