from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic_ai import ModelMessagesTypeAdapter, RunContext
from pydantic_ai.messages import UserPromptPart
from pydantic_core import to_jsonable_python


def conversation_id(ctx: RunContext[Any]) -> str:
    return str(ctx.conversation_id or "local-default")


def run_id(ctx: RunContext[Any]) -> str | None:
    return str(ctx.run_id) if ctx.run_id else None


def model_label(model: Any) -> str:
    return str(
        getattr(model, "model_name", None)
        or getattr(model, "system", None)
        or type(model).__name__
    )


def serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    try:
        return ModelMessagesTypeAdapter.dump_python(
            messages, mode="json"
        )
    except Exception:
        return [{"unserializable": repr(message)} for message in messages]


def plain(value: Any) -> Any:
    return to_jsonable_python(
        value,
        serialize_unknown=True,
        fallback=lambda item: repr(item),
    )


def fingerprint(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def latest_user_text(ctx: RunContext[Any]) -> str | None:
    if isinstance(ctx.prompt, str):
        return ctx.prompt
    for message in reversed(ctx.messages):
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    return part.content
                return json.dumps(
                    plain(part.content),
                    ensure_ascii=False,
                )
    return None


def short(value: str | None, limit: int = 300) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def error_payload(error: BaseException) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": str(error),
    }
