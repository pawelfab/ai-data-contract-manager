# Integration flow

```text
User message / inline attachment text
        ↓
ADCM EvidenceStore
        ↓
ContractState effective document
        ↓
ContractForgePort (mandatory call)
        ↓
Contract Forge
   formal requirements
        ↓
   fillable filter
        ↓
   discovery policy
        ↓
   visible requirements + current deterministic suggestions
        ↓
ADCM
   replace/recompute derived values
        ↓
   semantic resolver matches all available evidence
        ↓
   CandidateOutcome (deterministic validation)
        ↓
   accepted user values only
        ↓
repeat until fixed point
```

The LLM never controls the loop and never mutates `ContractState` directly.

## Source-system-first behavior

The first discovery gate is the semantic source-system anchor. For contract JSON v1 it is mapped by the Forge adapter to `/metadata/sourceSystemGcpId`. Once supplied, global/system enrichment may derive other values. Generic source-system propagation is data-driven enrichment, not ADCM code.

## Editing after complete

`valid` is a validation result, not a terminal workflow state. A later user message can edit an existing field. ADCM gives the newest evidence one resolver pass, validates the candidate deterministically, rebuilds derived values and calls Forge again.
