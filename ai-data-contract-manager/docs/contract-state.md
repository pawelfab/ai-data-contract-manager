# Contract state

`ContractState` has two effective layers:
- accepted user/user-referenced events,
- derived Forge suggestions.

User events are append-only, so changing the same field several times preserves history while the latest accepted event wins.

`Authority` distinguishes direct user input, user-referenced external material, formal system rules, observed conventions and defaults. Provenance records the evidence/source reference.

`effective_document()` overlays accepted user values on derived values and supports complete JSON Pointer paths including array indices.
