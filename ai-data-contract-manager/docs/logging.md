# Logging (planned stage 10)

Application logging and session/audit logging are separate concerns.

Local: app -> `logs/app.log`; session -> `logs/sessions/<id>.jsonl`.
GCP: app -> stdout/Cloud Logging; session -> BigQuery.
No logging implementation is required by stages 1-9.
