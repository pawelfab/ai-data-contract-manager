# Supplied contract snapshot — compatibility repair

`resources/contract.input.json` is the exact supplied `contract_poprawiony1.json` snapshot.
It contains nine dangling local `$ref` occurrences referring to six missing `$defs` names:

- `BigQueryTable`
- `Column`
- `ChecksumConfig`
- `BusinessKeyHashConfig`
- `BronzeTableConfig`
- `ConverterConfig`

`resources/contract.json` is the runtime copy used by this package. It adds conservative compatibility definitions so Contract Forge can parse and test the current vertical slice.

These definitions are **not claimed to be authoritative business schemas**. When the producing module supplies the authoritative versions, replace only `resources/contract.json` (or introduce a new contract-format adapter if the format changes). Do not propagate these structures into ADCM.
