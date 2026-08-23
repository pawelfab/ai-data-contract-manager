# Supplied contract snapshot — compatibility repair

An earlier supplied `contract_poprawiony1.json` snapshot contained nine dangling local `$ref` occurrences referring to six missing `$defs` names:

- `BigQueryTable`
- `Column`
- `ChecksumConfig`
- `BusinessKeyHashConfig`
- `BronzeTableConfig`
- `ConverterConfig`

`resources/contract.json` is now the only runtime source used by this package. The checked-in source is verified by the source linter and has no dangling local `$ref` values.

If a future supplied contract requires repair, keep it inside the Contract Forge format adapter or replace the one runtime source. Do not introduce a second runtime contract file and do not propagate its structure into ADCM.
