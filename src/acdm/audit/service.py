from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from pydantic_core import to_jsonable_python

from .models import AuditEvent
from .port import AuditLogPort


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditContext:
    conversation_id: str = "local-default"
    run_id: str | None = None


_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "client_secret",
    "access_token",
    "refresh_token",
    "connection_string",
    "database_url",
}
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


class AuditService:
    """Creates sanitized events and delegates persistence to an audit port."""

    def __init__(
        self,
        port: AuditLogPort,
        *,
        include_model_io: bool = True,
        include_mcp_payloads: bool = True,
    ) -> None:
        self.port = port
        self.include_model_io = include_model_io
        self.include_mcp_payloads = include_mcp_payloads
        self._context: ContextVar[AuditContext] = ContextVar(
            f"acdm_audit_context_{id(self)}",
            default=AuditContext(),
        )

    def bind_context(
        self, conversation_id: str, run_id: str | None
    ) -> None:
        self._context.set(
            AuditContext(
                conversation_id=conversation_id,
                run_id=run_id,
            )
        )

    def clear_context(self) -> None:
        self._context.set(AuditContext())

    async def record(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "acdm",
        conversation_id: str | None = None,
        run_id: str | None = None,
    ) -> AuditEvent:
        context = self._context.get()
        sanitized, redacted = sanitize(payload or {})
        event = AuditEvent(
            conversation_id=conversation_id or context.conversation_id,
            run_id=run_id if run_id is not None else context.run_id,
            event_type=event_type,
            source=source,
            payload=sanitized,
            redaction_applied=redacted,
        )
        try:
            return await self.port.append(event)
        except Exception:
            # Auditing must not make the interactive contract flow unavailable.
            logger.exception("Nie udało się zapisać zdarzenia audytowego.")
            return event


def sanitize(value: Any) -> tuple[Any, bool]:
    try:
        jsonable = to_jsonable_python(
            value,
            serialize_unknown=True,
            fallback=lambda item: repr(item),
        )
    except Exception:
        jsonable = repr(value)
    return _redact(jsonable)


def _redact(value: Any) -> tuple[Any, bool]:
    if isinstance(value, dict):
        redacted = False
        result: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if _is_sensitive_key(normalized):
                result[str(key)] = "[REDACTED]"
                redacted = True
                continue
            clean_child, child_redacted = _redact(child)
            result[str(key)] = clean_child
            redacted = redacted or child_redacted
        return result, redacted
    if isinstance(value, list):
        result = []
        redacted = False
        for child in value:
            clean_child, child_redacted = _redact(child)
            result.append(clean_child)
            redacted = redacted or child_redacted
        return result, redacted
    if isinstance(value, str):
        result = value
        for pattern in _SECRET_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result, result != value
    return value, False


def _is_sensitive_key(normalized: str) -> bool:
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        (
            "_api_key",
            "_password",
            "_secret",
            "_access_token",
            "_refresh_token",
        )
    )
