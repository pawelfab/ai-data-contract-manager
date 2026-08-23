# Logging — planned

Application logging and session/audit logging are separate concerns.

Planned adapters:

```text
application logging
local → file/stdout
GCP   → stdout / Cloud Logging

session audit
local → JSONL
GCP   → BigQuery
```

Logging must remain infrastructure/adapters and must not be merged into domain state or `SessionRepository`.

No production logging implementation is documented here as completed.
