from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic_ai import (
    AgentRunResult,
    ModelMessagesTypeAdapter,
    ModelResponse,
    RunContext,
)
from pydantic_ai.capabilities import ValidatedToolArgs
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.messages import (
    TextPart,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestContext
from pydantic_core import to_jsonable_python


def create_audit_hooks() -> Hooks[Any]:
    """Capture observable agent activity without requesting hidden reasoning."""

    hooks: Hooks[Any] = Hooks(
        id="acdm-audit",
        description="Append-only audit trail for ACDM agent runs.",
    )

    @hooks.on.before_run
    async def before_run(ctx: RunContext[Any]) -> None:
        conversation_id = _conversation_id(ctx)
        run_id = _run_id(ctx)
        audit = ctx.deps.audit
        audit.bind_context(conversation_id, run_id)
        history = _serialize_messages(ctx.messages)
        payload: dict[str, Any] = {
            "model": _model_label(ctx.model),
            "historyMessageCount": len(ctx.messages),
            "historyFingerprint": _fingerprint(history),
        }
        if audit.include_model_io:
            payload["prompt"] = _plain(ctx.prompt)
            payload["messageHistory"] = history
        await audit.record(
            "run_started",
            payload,
            source="pydantic-ai",
            conversation_id=conversation_id,
            run_id=run_id,
        )

    @hooks.on.after_run
    async def after_run(
        ctx: RunContext[Any],
        *,
        result: AgentRunResult[Any],
    ) -> AgentRunResult[Any]:
        audit = ctx.deps.audit
        try:
            state = ctx.deps.store.get(_conversation_id(ctx))
            state_payload = state.model_dump(mode="json")
            if not audit.include_model_io:
                state_payload.pop("chat_history", None)
            await audit.record(
                "contract_state_snapshot",
                state_payload,
                source="acdm-session",
            )
            payload: dict[str, Any] = {
                "usage": _plain(ctx.usage),
            }
            if audit.include_model_io:
                payload["output"] = _plain(result.output)
                payload["newMessages"] = _serialize_messages(
                    result.new_messages()
                )
            await audit.record(
                "run_completed",
                payload,
                source="pydantic-ai",
            )
            return result
        finally:
            audit.clear_context()

    @hooks.on.run_error
    async def run_error(
        ctx: RunContext[Any],
        *,
        error: BaseException,
    ) -> AgentRunResult[Any]:
        audit = ctx.deps.audit
        try:
            await audit.record(
                "run_failed",
                {"error": _error_payload(error)},
                source="pydantic-ai",
            )
        finally:
            audit.clear_context()
        raise error

    @hooks.on.before_model_request
    async def before_model_request(
        ctx: RunContext[Any],
        request_context: ModelRequestContext,
    ) -> ModelRequestContext:
        audit = ctx.deps.audit
        if audit.include_model_io:
            await audit.record(
                "model_request",
                {
                    "model": _model_label(request_context.model),
                    "messages": _serialize_messages(
                        request_context.messages
                    ),
                    "modelSettings": _plain(
                        request_context.model_settings
                    ),
                    "requestParameters": _plain(
                        request_context.model_request_parameters
                    ),
                },
                source="pydantic-ai",
            )
        return request_context

    @hooks.on.after_model_request
    async def after_model_request(
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        audit = ctx.deps.audit
        if audit.include_model_io:
            await audit.record(
                "model_response",
                {
                    "model": _model_label(request_context.model),
                    "message": _serialize_messages([response])[0],
                    "text": [
                        part.content
                        for part in response.parts
                        if isinstance(part, TextPart)
                    ],
                    # This contains only provider-visible ThinkingPart values.
                    "thinking": [
                        part.content
                        for part in response.parts
                        if isinstance(part, ThinkingPart)
                    ],
                    "toolCalls": [
                        {
                            "toolName": part.tool_name,
                            "arguments": part.args,
                            "toolCallId": part.tool_call_id,
                        }
                        for part in response.parts
                        if isinstance(part, ToolCallPart)
                    ],
                    "usage": _plain(response.usage),
                },
                source="pydantic-ai",
            )
        return response

    @hooks.on.model_request_error
    async def model_request_error(
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        error: Exception,
    ) -> ModelResponse:
        await ctx.deps.audit.record(
            "model_request_failed",
            {
                "model": _model_label(request_context.model),
                "error": _error_payload(error),
            },
            source="pydantic-ai",
        )
        raise error

    @hooks.on.tool_validate_error
    async def tool_validate_error(
        ctx: RunContext[Any],
        *,
        call: ToolCallPart,
        tool_def: Any,
        args: Any,
        error: Exception,
    ) -> ValidatedToolArgs:
        await ctx.deps.audit.record(
            "tool_call_failed",
            {
                "stage": "validation",
                "toolName": call.tool_name,
                "toolCallId": call.tool_call_id,
                "arguments": _plain(args),
                "error": _error_payload(error),
            },
            source="pydantic-ai",
        )
        raise error

    @hooks.on.tool_execute
    async def tool_execute(
        ctx: RunContext[Any],
        *,
        call: ToolCallPart,
        tool_def: Any,
        args: ValidatedToolArgs,
        handler: Any,
    ) -> Any:
        audit = ctx.deps.audit
        await audit.record(
            "tool_call_started",
            {
                "toolName": call.tool_name,
                "toolCallId": call.tool_call_id,
                "arguments": args,
            },
            source="pydantic-ai",
        )
        try:
            result = await handler(args)
        except Exception as exc:
            await audit.record(
                "tool_call_failed",
                {
                    "stage": "execution",
                    "toolName": call.tool_name,
                    "toolCallId": call.tool_call_id,
                    "arguments": args,
                    "error": _error_payload(exc),
                },
                source="pydantic-ai",
            )
            raise

        await audit.record(
            "tool_call_completed",
            {
                "toolName": call.tool_name,
                "toolCallId": call.tool_call_id,
                "arguments": args,
                "result": result,
            },
            source="pydantic-ai",
        )
        decision = _decision_trace(
            call.tool_name,
            args,
            result,
            _latest_user_text(ctx),
        )
        if decision:
            await audit.record(
                "decision_trace",
                decision,
                source="acdm-decision-trace",
            )
        return result

    return hooks


def _decision_trace(
    tool_name: str,
    args: ValidatedToolArgs,
    result: Any,
    user_text: str | None,
) -> dict[str, Any] | None:
    plain_args = _plain(args)
    plain_result = _plain(result)
    if not isinstance(plain_args, dict):
        plain_args = {}
    if not isinstance(plain_result, dict):
        plain_result = {"value": plain_result}

    if tool_name == "configure_contract_scope":
        source_type = plain_result.get(
            "sourceType", plain_args.get("source_type")
        )
        layers = plain_result.get(
            "targetLayers", plain_args.get("target_layers") or ["bronze"]
        )
        basis = (
            f' na podstawie wypowiedzi użytkownika: "{_short(user_text)}".'
            if user_text
            else "."
        )
        return {
            "decisionType": "contract_scope_selected",
            "summary": (
                f"Wybrano źródło {source_type!r} i warstwy {layers!r}"
                + basis
            ),
            "evidence": user_text,
            "details": {
                "sourceType": source_type,
                "targetLayers": layers,
            },
        }

    if tool_name == "apply_contract_patch":
        updates = plain_args.get("updates", [])
        paths = plain_result.get("changedPaths", [])
        return {
            "decisionType": "contract_patch_applied",
            "summary": "Zmieniono draft na ścieżkach: "
            + (", ".join(paths) if paths else "brak"),
            "evidence": [
                {
                    "path": update.get("path"),
                    "evidenceText": update.get("evidence_text"),
                }
                for update in updates
                if isinstance(update, dict)
            ],
            "details": {
                "origin": plain_args.get("origin", "user"),
                "changedPaths": paths,
                "updates": updates,
                "revision": plain_result.get("revision"),
            },
        }

    if tool_name == "set_optional_decisions":
        return {
            "decisionType": "optional_sections_selected",
            "summary": "Zapisano decyzje dotyczące sekcji opcjonalnych.",
            "evidence": user_text,
            "details": {
                "decisions": plain_args.get("decisions", []),
                "choices": plain_result.get("choices", {}),
            },
        }

    if tool_name == "validate_contract_draft":
        valid = plain_result.get("valid")
        if valid is True:
            summary = "Walidacja draftu przez MCP zakończyła się sukcesem."
        elif valid is False or plain_result.get("ok") is False:
            summary = "Walidacja draftu nie zakończyła się sukcesem."
        else:
            summary = "Wykonano próbę walidacji draftu przez MCP."
        return {
            "decisionType": "contract_validation_attempted",
            "summary": summary,
            "evidence": "Wynik walidacji zwrócony przez MCP.",
            "details": plain_result,
        }

    if tool_name == "prepare_yaml_preview":
        return {
            "decisionType": "yaml_preview_generated",
            "summary": "Wygenerowano YAML preview z poprawnego draftu.",
            "evidence": "Bieżący draft przeszedł walidację MCP.",
            "details": {
                "contractFingerprint": plain_result.get(
                    "contractFingerprint"
                )
            },
        }

    if tool_name == "approve_final_yaml":
        return {
            "decisionType": "yaml_approval_recorded",
            "summary": (
                "Zapisano zatwierdzenie końcowego YAML."
                if plain_result.get("accepted")
                else "Końcowy YAML nie został zatwierdzony."
            ),
            "evidence": user_text,
            "details": plain_result,
        }

    return None


def _conversation_id(ctx: RunContext[Any]) -> str:
    return str(ctx.conversation_id or "local-default")


def _run_id(ctx: RunContext[Any]) -> str | None:
    return str(ctx.run_id) if ctx.run_id else None


def _model_label(model: Any) -> str:
    return str(
        getattr(model, "model_name", None)
        or getattr(model, "system", None)
        or type(model).__name__
    )


def _serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    try:
        return ModelMessagesTypeAdapter.dump_python(
            messages, mode="json"
        )
    except Exception:
        return [{"unserializable": repr(message)} for message in messages]


def _plain(value: Any) -> Any:
    return to_jsonable_python(
        value,
        serialize_unknown=True,
        fallback=lambda item: repr(item),
    )


def _fingerprint(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _latest_user_text(ctx: RunContext[Any]) -> str | None:
    if isinstance(ctx.prompt, str):
        return ctx.prompt
    for message in reversed(ctx.messages):
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    return part.content
                return json.dumps(
                    _plain(part.content),
                    ensure_ascii=False,
                )
    return None


def _short(value: str | None, limit: int = 300) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _error_payload(error: BaseException) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": str(error),
    }
