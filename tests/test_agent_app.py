from __future__ import annotations

import asyncio

from pydantic_ai import ModelResponse
from pydantic_ai.messages import TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from starlette.testclient import TestClient

from acdm.agent import create_agent
from acdm.models import ContractState
from acdm.settings import AppSettings


def test_agent_builds_pydantic_web_app() -> None:
    settings = AppSettings(
        model="test",
        contract_transport="inprocess",
        max_automatic_repair_attempts=2,
        host="127.0.0.1",
        port=7932,
    )
    agent, deps = create_agent(settings)

    app = agent.to_web(deps=deps)

    paths = {route.path for route in app.routes}
    assert "/api" in paths
    assert TestClient(app).get("/api/health").status_code == 200


def test_configure_scope_runs_without_deferred_approval() -> None:
    settings = AppSettings(
        model="test",
        contract_transport="inprocess",
        max_automatic_repair_attempts=2,
        host="127.0.0.1",
        port=7932,
    )
    agent, deps = create_agent(settings)
    request_count = 0

    def respond(_messages, _info) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="configure_contract_scope",
                        args={
                            "source_type": "csv",
                            "target_layers": ["bronze"],
                        },
                        tool_call_id="scope-1",
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Scope gotowy.")])

    result = asyncio.run(
        agent.run(
            "Źródło CSV, tylko Bronze.",
            deps=deps,
            model=FunctionModel(respond),
        )
    )

    assert result.output == "Scope gotowy."
    assert deps.store.get(str(result.conversation_id)).source_type == "csv"


def test_agent_accepts_object_patch_for_allowed_container() -> None:
    settings = AppSettings(
        model="test",
        contract_transport="inprocess",
        max_automatic_repair_attempts=2,
        host="127.0.0.1",
        port=7932,
    )
    agent, deps = create_agent(settings)
    request_count = 0

    def respond(_messages, _info) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="configure_contract_scope",
                        args={
                            "source_type": "csv",
                            "target_layers": ["bronze"],
                        },
                        tool_call_id="scope-1",
                    )
                ]
            )
        if request_count == 2:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="apply_contract_patch",
                        args={
                            "updates": [
                                {
                                    "path": "source.options",
                                    "value": {
                                        "delimiter": ";",
                                        "header": False,
                                        "file": {
                                            "encoding": "utf-8",
                                            "compression": "none",
                                        },
                                    },
                                    "evidence_text": (
                                        "Użytkownik podał opcje CSV."
                                    ),
                                }
                            ]
                        },
                        tool_call_id="patch-1",
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Opcje zapisane.")])

    result = asyncio.run(
        agent.run(
            "CSV do Bronze, separator średnik, bez nagłówka.",
            deps=deps,
            model=FunctionModel(respond),
        )
    )

    state = deps.store.get(str(result.conversation_id))
    assert result.output == "Opcje zapisane."
    assert state.draft["source"]["options"] == {
        "delimiter": ";",
        "header": False,
        "file": {"encoding": "utf-8", "compression": "none"},
    }


def test_final_yaml_is_approved_without_second_deferred_step() -> None:
    settings = AppSettings(
        model="test",
        contract_transport="inprocess",
        max_automatic_repair_attempts=2,
        host="127.0.0.1",
        port=7932,
    )
    agent, deps = create_agent(settings)
    conversation_id = "approval-conversation"
    deps.store.save(
        ContractState(
            conversation_id=conversation_id,
            pending_yaml="metadata:\n  id: example\n",
            pending_yaml_fingerprint="fingerprint-1",
        )
    )
    request_count = 0

    def respond(_messages, _info) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="approve_final_yaml",
                        args={"contract_fingerprint": "fingerprint-1"},
                        tool_call_id="approval-1",
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="YAML zatwierdzony.")])

    result = asyncio.run(
        agent.run(
            "Tak, zatwierdzam YAML.",
            conversation_id=conversation_id,
            deps=deps,
            model=FunctionModel(respond),
        )
    )

    state = deps.store.get(conversation_id)
    assert result.output == "YAML zatwierdzony."
    assert state.last_valid_yaml_fingerprint == "fingerprint-1"
