from __future__ import annotations

from dataclasses import replace

from pydantic_ai import ModelResponse
from pydantic_ai.messages import TextPart, ThinkingPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from acdm.agent import create_agent
from acdm.audit import (
    AuditEvent,
    AuditService,
    AuditedContractPort,
    InMemoryAuditLogAdapter,
    JsonlAuditLogAdapter,
)
from acdm.contract_port import InProcessContractPort
from acdm.settings import AppSettings


def _settings() -> AppSettings:
    return AppSettings(
        model="test",
        contract_transport="inprocess",
        max_automatic_repair_attempts=2,
        host="127.0.0.1",
        port=7932,
    )


async def test_jsonl_adapter_continues_sequence_after_restart(
    tmp_path,
) -> None:
    first_adapter = JsonlAuditLogAdapter(tmp_path / "logs")
    first = await first_adapter.append(
        AuditEvent(
            conversation_id="../unsafe-session",
            event_type="run_started",
            source="test",
        )
    )

    second_adapter = JsonlAuditLogAdapter(tmp_path / "logs")
    second = await second_adapter.append(
        AuditEvent(
            conversation_id="../unsafe-session",
            event_type="run_completed",
            source="test",
        )
    )
    events = await second_adapter.list_session_events("../unsafe-session")

    assert first.sequence == 1
    assert second.sequence == 2
    assert [event.event_type for event in events] == [
        "run_started",
        "run_completed",
    ]
    assert not (tmp_path / "unsafe-session").exists()


async def test_audit_service_redacts_secrets_without_redacting_usage() -> None:
    adapter = InMemoryAuditLogAdapter()
    audit = AuditService(adapter)

    event = await audit.record(
        "model_request",
        {
            "api_key": "secret-value",
            "nested": {"Authorization": "Bearer abc.def.ghi"},
            "description": "token usage is safe",
            "input_tokens": 42,
            "raw": "call with sk-abcdefghijklmnop",
        },
    )

    assert event.redaction_applied is True
    assert event.payload["api_key"] == "[REDACTED]"
    assert event.payload["nested"]["Authorization"] == "[REDACTED]"
    assert event.payload["input_tokens"] == 42
    assert event.payload["raw"] == "call with [REDACTED]"


async def test_agent_audits_thinking_tools_mcp_and_decisions() -> None:
    adapter = InMemoryAuditLogAdapter()
    agent, deps = create_agent(_settings(), audit_port=adapter)
    request_count = 0

    def respond(_messages, _info) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return ModelResponse(
                parts=[
                    ThinkingPart(
                        content="Rozpoznano źródło CSV i warstwę Bronze."
                    ),
                    ToolCallPart(
                        tool_name="configure_contract_scope",
                        args={
                            "source_type": "csv",
                            "target_layers": ["bronze"],
                        },
                        tool_call_id="scope-1",
                    ),
                ]
            )
        if request_count == 2:
            return ModelResponse(
                parts=[
                    ThinkingPart(
                        content="Mapuję opcje CSV na source.options."
                    ),
                    ToolCallPart(
                        tool_name="apply_contract_patch",
                        args={
                            "updates": [
                                {
                                    "path": "source.options",
                                    "value": {
                                        "delimiter": ";",
                                        "header": False,
                                    },
                                    "evidence_text": (
                                        "Użytkownik podał separator ; "
                                        "i brak nagłówka."
                                    ),
                                }
                            ]
                        },
                        tool_call_id="patch-1",
                    ),
                ]
            )
        return ModelResponse(
            parts=[
                ThinkingPart(content="Zmiany zostały zapisane."),
                TextPart(content="Konfiguracja została zaktualizowana."),
            ]
        )

    result = await agent.run(
        "Chcę CSV do Bronze, separator ; i bez nagłówka.",
        conversation_id="audit-conversation",
        deps=deps,
        model=FunctionModel(respond),
    )
    events = await adapter.list_session_events("audit-conversation")

    assert result.output == "Konfiguracja została zaktualizowana."
    assert [event.sequence for event in events] == list(
        range(1, len(events) + 1)
    )
    response_events = [
        event for event in events if event.event_type == "model_response"
    ]
    assert response_events[0].payload["thinking"] == [
        "Rozpoznano źródło CSV i warstwę Bronze."
    ]
    assert response_events[-1].payload["text"] == [
        "Konfiguracja została zaktualizowana."
    ]

    started_tools = [
        event.payload
        for event in events
        if event.event_type == "tool_call_started"
    ]
    assert started_tools[0]["toolName"] == "configure_contract_scope"
    assert started_tools[0]["arguments"]["source_type"] == "csv"
    assert {
        event.payload["operation"]
        for event in events
        if event.event_type == "mcp_request"
    } >= {"get_onboarding_requirements"}

    decisions = [
        event.payload
        for event in events
        if event.event_type == "decision_trace"
    ]
    scope_decision = next(
        item
        for item in decisions
        if item["decisionType"] == "contract_scope_selected"
    )
    assert "Wybrano źródło 'csv'" in scope_decision["summary"]
    assert "separator ;" in scope_decision["evidence"]

    patch_decision = next(
        item
        for item in decisions
        if item["decisionType"] == "contract_patch_applied"
    )
    assert patch_decision["details"]["changedPaths"] == [
        "source.options.delimiter",
        "source.options.header",
    ]
    assert patch_decision["evidence"][0]["evidenceText"] == (
        "Użytkownik podał separator ; i brak nagłówka."
    )
    assert any(
        event.event_type == "contract_state_snapshot"
        for event in events
    )
    assert events[-1].event_type == "run_completed"


async def test_agent_records_tool_errors() -> None:
    adapter = InMemoryAuditLogAdapter()
    agent, deps = create_agent(_settings(), audit_port=adapter)
    request_count = 0

    def respond(_messages, _info) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="apply_contract_patch",
                        args={
                            "updates": [
                                {
                                    "path": "metadata.id",
                                    "value": "example",
                                    "evidence_text": "Użytkownik podał id.",
                                }
                            ]
                        },
                        tool_call_id="invalid-patch-1",
                    )
                ]
            )
        return ModelResponse(
            parts=[TextPart(content="Najpierw skonfiguruję scope.")]
        )

    await agent.run(
        "Ustaw id na example.",
        conversation_id="tool-error-conversation",
        deps=deps,
        model=FunctionModel(respond),
    )
    events = await adapter.list_session_events(
        "tool-error-conversation"
    )
    failures = [
        event
        for event in events
        if event.event_type == "tool_call_failed"
    ]

    assert failures
    assert failures[0].payload["stage"] == "execution"
    assert failures[0].payload["toolName"] == "apply_contract_patch"
    assert "Najpierw" in failures[0].payload["error"]["message"]


async def test_full_history_is_recorded_for_each_run() -> None:
    adapter = InMemoryAuditLogAdapter()
    agent, deps = create_agent(_settings(), audit_port=adapter)
    model = FunctionModel(
        lambda _messages, _info: ModelResponse(
            parts=[TextPart(content="Odpowiedź.")]
        )
    )

    first = await agent.run(
        "Pierwsza wiadomość.",
        conversation_id="history-conversation",
        deps=deps,
        model=model,
    )
    await agent.run(
        "Druga wiadomość.",
        conversation_id="history-conversation",
        message_history=first.all_messages(),
        deps=deps,
        model=model,
    )
    events = await adapter.list_session_events("history-conversation")
    starts = [
        event for event in events if event.event_type == "run_started"
    ]

    assert len(starts) == 2
    assert starts[0].payload["prompt"] == "Pierwsza wiadomość."
    assert starts[1].payload["prompt"] == "Druga wiadomość."
    assert starts[1].payload["historyMessageCount"] > 0
    assert starts[1].payload["messageHistory"]


async def test_agent_writes_complete_run_to_jsonl(tmp_path) -> None:
    settings = replace(
        _settings(),
        audit_enabled=True,
        audit_dir=tmp_path / "logs",
    )
    agent, deps = create_agent(settings)
    model = FunctionModel(
        lambda _messages, _info: ModelResponse(
            parts=[
                ThinkingPart(content="Jawna część reasoning."),
                TextPart(content="Gotowe."),
            ]
        )
    )

    await agent.run(
        "Test zapisu.",
        conversation_id="jsonl-conversation",
        deps=deps,
        model=model,
    )
    adapter = JsonlAuditLogAdapter(tmp_path / "logs")
    events = await adapter.list_session_events("jsonl-conversation")

    assert events[0].event_type == "run_started"
    assert events[-1].event_type == "run_completed"
    response = next(
        event for event in events if event.event_type == "model_response"
    )
    assert response.payload["thinking"] == ["Jawna część reasoning."]
    assert response.payload["text"] == ["Gotowe."]


async def test_each_mcp_validation_attempt_is_logged() -> None:
    adapter = InMemoryAuditLogAdapter()
    audit = AuditService(adapter)
    port = AuditedContractPort(InProcessContractPort(), audit)
    audit.bind_context("validation-conversation", "validation-run")

    await port.validate_contract({})
    await port.validate_contract({})
    events = await adapter.list_session_events(
        "validation-conversation"
    )
    validation_requests = [
        event
        for event in events
        if event.event_type == "mcp_request"
        and event.payload["operation"] == "validate_contract"
    ]
    validation_responses = [
        event
        for event in events
        if event.event_type == "mcp_response"
        and event.payload["operation"] == "validate_contract"
    ]

    assert len(validation_requests) == 2
    assert len(validation_responses) == 2
