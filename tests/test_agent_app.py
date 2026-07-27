from __future__ import annotations

import asyncio

from pydantic_ai import ModelResponse
from pydantic_ai.messages import TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from starlette.testclient import TestClient

from acdm.agent import create_agent
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
