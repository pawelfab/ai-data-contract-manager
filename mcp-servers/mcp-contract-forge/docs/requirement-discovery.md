# Requirement discovery

Contract Forge separates formal correctness from what ADCM should ask for now.

```text
contract
    ├─ JsonSchemaValidator / RuleEngine
    │      → formal validity/issues
    │
    └─ RequirementEngine
           → formal requirements
           ↓
       fillable filter
           ↓
       RequirementDiscovery
           → currently visible requirements
```

Discovery does not define final validity.

## Policy

The current discovery policy is loaded through `JsonDiscoveryPolicyRepository` from `resources/discovery_rules.json`.

Semantic tokens such as `@sourceSystem` resolve through normalized semantic paths supplied by the current contract adapter. Discovery policy therefore does not need to know concrete contract-v1 JSON pointers.

The default policy is progressive: source system first, then later requirement groups.

## Fillable requirements

Structural containers are not user questions when their existence follows from filling required descendants.

For example, if `/metadata/id` is the actual fillable value, `/metadata` should not also be exposed as a scalar/object question.

Genuinely fillable array/object leaves remain requirements.

## Discriminated unions

Runtime behavior follows the contract-format `x-discriminator` semantics.

| state | behavior |
|---|---|
| union without supported discriminator | union remains atomic |
| discriminator absent | expose only the discriminator requirement with allowed values |
| discriminator selects a branch | recurse only into that branch |
| discriminator value invalid | return deterministic validation issue |

Never merge requirements from all `oneOf` branches.

`allowed_values` may also be supplied generically for ordinary `const`/`enum` requirements.

## Arrays

Array discovery follows these rules:

```text
existing elements
→ recurse according to their item schema

missing elements + expansion permitted
→ synthesize only up to schema-defined minimum cardinality

otherwise
→ treat the array as one atomic requirement
```

Never invent an index solely because an array property is required.

Collections naturally supplied as one value should remain atomic unless the contract explicitly declares structural expansion semantics.

Known limitation: automatic expansion is bounded by the contract-defined minimum. User-driven creation of additional items beyond that minimum requires separate editing semantics.

## Validation is independent

The requirement walker is not the formal schema validator.

Formal validity is determined by the supported complete JSON Schema validator plus deterministic contract rules.

Conceptually:

```text
valid = not schema_errors and not rule_errors
```

Missing required data normally belongs to requirements/questions rather than duplicate user-facing validation noise.

Presentation/mapping of schema errors must remain separate from the validator so user-facing issue policy cannot change formal validity.

## Enrichment interaction

Discovery participates in deciding when a derived target may become visible/eligible, preventing later optional sections from being materialized prematurely.

Forge does not recursively apply its own suggestions.

ADCM applies current derived suggestions to its effective state and calls Forge again through the fixed-point loop.

## Strict/fail-open policy validation

Invalid discovery configuration should be detectable.

Development/strict mode may fail fast.

Production mode may emit controlled diagnostics and use a safe fallback according to the configured policy.
