# Konfiguracja

Konfiguracja aplikacji jest ładowana z pliku `.env` w katalogu projektu.
`python-dotenv` nie nadpisuje wartości już ustawionych w środowisku procesu.

| Zmienna | Domyślnie | Znaczenie |
|---|---:|---|
| `OPENAI_API_KEY` | brak | klucz dostawcy zgodnego z OpenAI |
| `OPENAI_BASE_URL` | domyślne API | opcjonalny URL API modelu |
| `ACDM_MODEL` | `openai:gpt-5.2` | identyfikator modelu Pydantic AI |
| `ACDM_CONTRACT_TRANSPORT` | `stdio` | `stdio` albo `inprocess` |
| `ACDM_MCP_TIMEOUT_SECONDS` | `15` | timeout startu i pojedynczej operacji MCP |
| `ACDM_MAX_AUTOMATIC_REPAIR_ATTEMPTS` | `2` | limit napraw bez użytkownika |
| `ACDM_HOST` | `127.0.0.1` | host serwera webowego |
| `ACDM_PORT` | `7932` | port serwera webowego |
| `ACDM_AUDIT_ENABLED` | `true` | zapis zdarzeń audytowych |
| `ACDM_AUDIT_DIR` | `logs` | katalog logów, względny wobec `.env` |
| `ACDM_AUDIT_INCLUDE_MODEL_IO` | `true` | wejścia i odpowiedzi modelu |
| `ACDM_AUDIT_INCLUDE_MCP_PAYLOADS` | `true` | payloady request/response MCP |

Przykład znajduje się w `.env.example`.

## Transport MCP

`stdio` uruchamia jeden proces `python -m mcp_contract_forge.server`,
inicjalizuje jedną sesję i zamyka ją przy shutdown aplikacji.

`inprocess` wywołuje `ContractSchemaService` bez procesu MCP. Jest przeznaczony
do testów i szybkiego developmentu.

## Bezpieczeństwo

- `.env` i `logs/` nie powinny trafiać do Git;
- pełne model I/O oraz kontrakty mogą zawierać dane biznesowe;
- redakcja audytu usuwa typowe klucze i tokeny, ale nie zastępuje klasyfikacji
  danych ani polityki retencji;
- developerskiego `Agent.to_web()` nie należy wystawiać publicznie bez
  uwierzytelniania i dodatkowych zabezpieczeń.
