import re
from typing import Any

REDACTED = "***REDACTED***"

_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "credentials",
    "cookie",
    "cookies",
    "private_key",
    "client_secret",
}
_TOKEN = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
_ASSIGNMENT_TO_END = re.compile(
    r"(?is)([\"']?\b(?:authorization|api[_-]?key|apikey|password|secret|access[_-]?token|"
    r"refresh[_-]?token|client[_-]?secret|credentials|private[_-]?key|cookies?|service[_ -]?account)"
    r"\b[\"']?\s*[:=]\s*)(.*)\Z"
)


def _is_secret_key(key: Any) -> bool:
    raw = str(key).lower()
    if raw in _SECRET_KEYS:
        return True
    normalized = re.sub(r"[^a-z0-9]", "", raw)
    return normalized.endswith(
        ("authorization", "apikey", "password", "secret", "token", "credentials", "privatekey")
    )


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: REDACTED if _is_secret_key(key) else sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        value = _TOKEN.sub(lambda match: f"{match.group(1)} {REDACTED}", value)
        return _ASSIGNMENT_TO_END.sub(lambda match: f"{match.group(1)}{REDACTED}", value)
    return value
