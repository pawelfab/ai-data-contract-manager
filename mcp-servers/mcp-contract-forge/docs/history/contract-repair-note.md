# Historical contract repair note

An earlier supplied contract snapshot contained dangling local `$ref` references to missing `$defs`.

The runtime contract was repaired and `resources/contract.json` is the current single runtime contract source.

The checked-in source is protected by source-linter validation so dangling local references are treated as contract/source defects.

This file exists only as historical rationale.

For current contract-format rules use:

`../contract-format.md`

For current architecture use:

`../architecture.md`

Future contract-source defects should be corrected or isolated at the Contract Forge source/format boundary. They must not be compensated for by contract-specific ADCM logic.
