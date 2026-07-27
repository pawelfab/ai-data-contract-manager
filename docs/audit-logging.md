# Logowanie sesji i decyzji agenta

Audyt jest domyślnie włączony, gdy aplikacja korzysta z
`AppSettings.from_env()`. Konfiguracja:

```dotenv
ACDM_AUDIT_ENABLED=true
ACDM_AUDIT_DIR=logs
ACDM_AUDIT_INCLUDE_MODEL_IO=true
ACDM_AUDIT_INCLUDE_MCP_PAYLOADS=true
```

Każda sesja otrzymuje append-only plik:

```text
logs/sessions/<hash-conversation-id>/events.jsonl
```

Każda linia jest niezależnym obiektem JSON zawierającym między innymi:

- `conversation_id` i `run_id`,
- numer `sequence` w sesji,
- czas UTC i typ zdarzenia,
- źródło oraz payload,
- informację, czy zastosowano redakcję sekretów.

Rejestrowane są:

- wejście i zakończenie każdej tury,
- historia oraz wiadomości rzeczywiście wysłane do modelu,
- odpowiedzi tekstowe modelu,
- `ThinkingPart`, tylko jeśli dostawca zwrócił je przez API,
- wybrane narzędzia, argumenty, wyniki i błędy,
- requesty i odpowiedzi MCP,
- próby walidacji i generowanie YAML,
- snapshot stanu kontraktu,
- deterministyczny `decision_trace` z argumentów narzędzia,
  wypowiedzi użytkownika i `evidence_text`.

Audyt nie zapisuje niedostępnego, wewnętrznego chain-of-thought modelu.
`thinking` oznacza wyłącznie treść jawnie udostępnioną przez dostawcę.

Pola takie jak `api_key`, `Authorization`, `password`, `secret` i tokeny
są redagowane przed przekazaniem zdarzenia do adaptera. Historia rozmowy
i kontrakty mogą jednak zawierać dane biznesowe, dlatego katalog `logs/`
nie jest wersjonowany w Git.

## Adaptery

`AuditLogPort` oddziela generowanie zdarzeń od miejsca zapisu:

- `JsonlAuditLogAdapter` — domyślny zapis lokalny,
- `InMemoryAuditLogAdapter` — deterministyczne testy,
- `NullAuditLogAdapter` — audyt wyłączony.

Przyszły adapter bazodanowy powinien implementować ten sam port. Nie wymaga
to zmian w agencie, hooks ani dekoratorze `ContractPort`.

Log audytowy nie jest repozytorium aktywnego `ContractState` i nie służy
obecnie do automatycznego odtwarzania draftu po restarcie serwera.
