# Testy live

Testy integracyjne uruchamiające **prawdziwy** stos: `build_container()` → `ForgeMcpAdapter`
→ HTTP MCP Contract Forge → `PydanticAiHeuristicsAdapter` → skonfigurowany endpoint LLM.
Nic nie jest mockowane. `test_zasilanie_flow.py` odtwarza turę po turze ręczną sesję
„robimy zasilanie".

## Uruchamianie

Domyślnie testy są pomijane, więc `pytest ai-data-contract-manager/tests` w bramce pre-push
pozostaje szybki i zielony. Włącza je `ADCM_LIVE=1` — dodatkowo sprawdzana jest dostępność
obu usług, a komunikat skipa mówi, czego brakuje.

```powershell
# Warstwa MCP, deterministycznie, bez kosztu LLM (<1 s)
$env:ADCM_LIVE='1'
.venv\Scripts\python.exe -m pytest tests\live\test_forge_mcp_live.py -q

# Pełna rozmowa; -s pokazuje tabelkę per tura
.venv\Scripts\python.exe -m pytest tests\live -q -s
```

Wymagane: Forge MCP na `ADCM_FORGE_MCP_URL`
(`mcp-servers\mcp-contract-forge\.venv\Scripts\python.exe -m contract_forge.main`)
oraz endpoint LLM z `ADCM_LLM_BASE_URL`. Reszta konfiguracji pochodzi z `.env`.

Zmienne: `ADCM_LIVE`, `ADCM_LIVE_TURN_TIMEOUT` (240 s), `ADCM_LIVE_STRICT` (0),
`ADCM_LIVE_ARTIFACT_DIR` (domyślnie `logs/live/`, już w `.gitignore`).

## Trzy poziomy oczekiwań

LLM jest niedeterministyczny, więc nie wszystko może być twardą asercją.

| poziom | co obejmuje | efekt |
|---|---|---|
| **twardy** | wartości w dokumencie, sekwencja requirementów z Forge, `valid`/`yaml`, zbieżność pętli | fail |
| **znany defekt** | twarda porażka pasująca do `KNOWN_ISSUES` w `scenario.py` | wypisany, nie czerwieni |
| **miękki** | brzmienie pytania, ostrzeżenia doradcze | wypisany |

`ADCM_LIVE_STRICT=1` czerwieni wszystkie trzy — to jest wariant „pełna wierność ręcznemu
transkryptowi".

Sekwencja requirementów jest twarda, bo pochodzi wprost z Forge i jest w pełni
deterministyczna; widać ją dzięki `RecordingForge`, który jest przezroczystym dekoratorem na
prawdziwym adapterze. Ostrzeżenia (literówka „star date", backfill `startDate`) nie wynikają
z żadnej reguły w repo — powstają wyłącznie z `_CONSISTENCY_INSTRUCTIONS`, więc są miękkie.

## Artefakty

Każdy przebieg zapisuje `logs/live/<timestamp>-<test>.md` oraz `.json` — także gdy test padnie.
Plik `.md` ma format identyczny z ręcznym transkryptem (`u: <wiadomość>` + koperta JSON),
plus rozbicie na rundy Forge i wywołania LLM, co pozwala odróżnić „LLM nie zaproponował
wartości" od „zaproponował, ale `ValueResolver` ją odrzucił".

## Pliki

- `conftest.py` — bramka, sondy usług, kontener ze spy, zapis transkryptu
- `scenario.py` — 6 tur jako dane + matchery + `KNOWN_ISSUES`
- `recording.py` — przezroczyste dekoratory na portach Forge i LLM
- `test_forge_mcp_live.py` — deterministyczne sprawdzenie MCP, bez LLM
- `test_zasilanie_flow.py` — rozmowa + test przełączenia systemu źródłowego
