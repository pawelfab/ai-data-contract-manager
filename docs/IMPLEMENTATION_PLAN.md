# Plan wdrożenia i status v0.1

## Etap 0 — granice odpowiedzialności — DONE

Cel: nie powtórzyć poprzedniego problemu, w którym ADCM przejmował enrichment i logikę kontraktu.

Wynik:

- Forge ma kanoniczny state;
- ADCM nie mutuje contract;
- LLM nie steruje tool loop;
- MCP mówi, jakie paths są aktualnie wymagane.

## Etap 1 — dynamiczny Contract Forge kernel — DONE

Cel:

- JSON Schema Draft 2020-12;
- `$ref`;
- source discriminator;
- required discovery;
- schema defaults;
- final validation.

Czego celowo nie robi v0:

- nie interpretuje arbitrary `x-contract-rules` z tekstowego message;
- nie wykonuje zewnętrznych lookupów.

## Etap 2 — enrichment precedence — DONE

Kolejność:

1. source type wynikający z system rules;
2. system rules;
3. generic rules;
4. JSON Schema defaults;
5. missing requirements.

Silnik pracuje do fixpointu, bo np. `metadata.id` może dopiero odblokować `dagId`, nazwę Bronze table i kolejne reguły.

## Etap 3 — ADCM stair-step orchestrator — DONE

Cel:

- pytanie o source system jako pierwszy gate;
- po każdej odpowiedzi call do Forge;
- jeśli Forge odsłoni następne wymaganie, spróbować odpowiedzieć z historii;
- jeśli brak faktu, wrócić do usera.

Zabezpieczenia:

- `max_auto_steps`;
- Forge przyjmuje tylko current pending paths;
- finalna walidacja po stronie Forge.

## Etap 4 — heurystyka — DONE

Obsługuje:

- fuzzy source system;
- identyfikatory;
- owner/e-mail;
- URI;
- JSON columns;
- `name TYPE NOT NULL`;
- fixed-width `name start end TYPE`.

## Etap 5 — Pydantic AI semantic resolver — DONE / OPTIONAL RUNTIME

LLM ma tylko rolę ekstraktora faktów z rozmowy.

Nie może:

- zgłaszać path spoza current requirements;
- samodzielnie wykonać enrichmentu;
- wywołać Contract Forge w niekontrolowanej kolejności.

Vertex AI jest obsługiwany przez `GoogleModel(..., provider="google-cloud")`.

## Etap 6 — MCP transport — DONE / REFERENCE SERVER

Referencyjny Forge jest wystawiony przez FastMCP HTTP pod `/mcp`.

ADCM używa Pydantic AI `MCPToolset` jako programmatic MCP client i utrzymuje lifecycle toolsetu przez czas działania CLI/API.

## Etap 7 — terminal + API — DONE

Terminal jest demo UI.

FastAPI jest kontraktem pod późniejszy web frontend.

## Etap 8 — testy — DONE

Automatyczne testy rdzenia i pełnego minimalnego flow.

## Następne etapy po demo

### P1 — contract/rules compatibility gate

Na starcie Forge:

- schema version;
- rules version;
- registry version;
- fail-fast na nieznane actions / paths.

### P1 — optional decision loop

Obsłużyć `x-acdm-optional-decision` jako osobny typ requirement:

```text
configure / skip
```

z zapamiętaniem decyzji, aby nie pytać ponownie.

### P1 — edit existing contract

- MCP pobiera istniejący YAML/JSON;
- Forge tworzy session from existing;
- ADCM pokazuje różnice i pozwala zmieniać jawnie wybrane fields.

### P1 — trwały state i logi

- session store poza pamięcią procesu;
- correlation id ADCM <-> MCP;
- structured event log: user input, normalized candidates, enrichment rule ids, validation issues.

### P2 — Schema Explorer MCP

Osobny owner dla:

- BigQuery existence/naming;
- GitHub existing configs;
- external metadata.

Contract Forge może prosić ADCM o wynik z drugiego MCP albo zostać orchestrated przez ADCM, ale własność reguły walidacyjnej musi pozostać jawna.

### P2 — Web UI

UI czyta tylko response API i renderuje:

- text question;
- enum choices;
- structured columns editor;
- contract preview;
- provenance per value.
