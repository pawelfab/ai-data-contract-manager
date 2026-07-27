from __future__ import annotations

from typing import Any

from pydantic_ai import AgentRunResult, ModelResponse, RunContext
from pydantic_ai.capabilities import ValidatedToolArgs
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.messages import TextPart, ThinkingPart, ToolCallPart
from pydantic_ai.models import ModelRequestContext

from .decision_trace import build_decision_trace
from .serialization import (
    conversation_id,
    error_payload,
    fingerprint,
    latest_user_text,
    model_label,
    plain,
    run_id,
    serialize_messages,
)


def create_audit_hooks() -> Hooks[Any]:
    """Capture observable agent activity without requesting hidden reasoning."""

    hooks: Hooks[Any] = Hooks(
        id="acdm-audit",
        description="Append-only audit trail for ACDM agent runs.",
    )

    @hooks.on.before_run
    async def before_run(ctx: RunContext[Any]) -> None:
        current_conversation_id = conversation_id(ctx)
        current_run_id = run_id(ctx)
        audit = ctx.deps.audit
        audit.bind_context(current_conversation_id, current_run_id)
        history = serialize_messages(ctx.messages)
        payload: dict[str, Any] = {
            "model": model_label(ctx.model),
            "historyMessageCount": len(ctx.messages),
            "historyFingerprint": fingerprint(history),
        }
        if audit.include_model_io:
            payload["prompt"] = plain(ctx.prompt)
            payload["messageHistory"] = history
        await audit.record(
            "run_started",
            payload,
            source="pydantic-ai",
            conversation_id=current_conversation_id,
            run_id=current_run_id,
        )

    @hooks.on.after_run
    async def after_run(
        ctx: RunContext[Any],
        *,
        result: AgentRunResult[Any],
    ) -> AgentRunResult[Any]:
        audit = ctx.deps.audit
        try:
            state = await ctx.deps.store.get(conversation_id(ctx))
            state_payload = state.model_dump(mode="json")
            if not audit.include_model_io:
                state_payload.pop("chat_history", None)
            await audit.record(
                "contract_state_snapshot",
                state_payload,
                source="acdm-session",
            )
            payload: dict[str, Any] = {
                "usage": plain(ctx.usage),
            }
            if audit.include_model_io:
                payload["output"] = plain(result.output)
                payload["newMessages"] = serialize_messages(
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
                {"error": error_payload(error)},
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
                    "model": model_label(request_context.model),
                    "messages": serialize_messages(
                        request_context.messages
                    ),
                    "modelSettings": plain(
                        request_context.model_settings
                    ),
                    "requestParameters": plain(
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
                    "model": model_label(request_context.model),
                    "message": serialize_messages([response])[0],
                    "text": [
                        part.content
                        for part in response.parts
                        if isinstance(part, TextPart)
                    ],
                    # Only provider-visible ThinkingPart values are recorded.
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
                    "usage": plain(response.usage),
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
                "model": model_label(request_context.model),
                "error": error_payload(error),
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
                "arguments": plain(args),
                "error": error_payload(error),
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
                    "error": error_payload(exc),
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
        decision = build_decision_trace(
            call.tool_name,
            args,
            result,
            latest_user_text(ctx),
        )
        if decision:
            await audit.record(
                "decision_trace",
                decision,
                source="acdm-decision-trace",
            )
        return result

    return hooks
