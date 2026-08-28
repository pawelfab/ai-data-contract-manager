# Forge wire protocol v1

Te schematy opisują publiczny wire-format ADCM <-> Contract Forge. Nie są współdzielonym pakietem Python.
Oba serwisy posiadają własne modele Pydantic i walidują payload po swojej stronie.

- `forge-analysis-v1.schema.json`
- `forge-describe-v1.schema.json`

Zmiana niekompatybilna wymaga nowej wersji protokołu; nie wolno po prostu zmienić wewnętrznego modelu Forge i oczekiwać, że ADCM się dostosuje.
