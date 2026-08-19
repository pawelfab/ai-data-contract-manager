import json

import httpx
import pytest

pytest.importorskip("pydantic_ai")
openai = pytest.importorskip("openai")

from adcm.model_factory import build_pydantic_ai_model
from adcm.models import ChatMessage
from adcm.semantic import PydanticAISemanticResolver
from adcm.settings import ADCMSettings
from contract_forge.models import Requirement


@pytest.mark.asyncio
async def test_openai_compatible_factory_uses_gateway_json_mode() -> None:
    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        return httpx.Response(
            200,
            request=request,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "auto",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "values": [
                                        {
                                            "path": "metadata.id",
                                            "value": "customer_daily",
                                            "confidence": 0.99,
                                            "evidence": "customer_daily",
                                        }
                                    ]
                                }
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                },
            },
        )

    settings = ADCMSettings(
        _env_file=None,
        llm_mode="pydantic",
        llm_provider="openai_compatible",
        model="openai-chat:auto",
        openai_base_url="http://gateway.test/v1",
        openai_api_key="test-secret",
    )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        openai_client = openai.AsyncOpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
            http_client=http_client,
        )
        model = build_pydantic_ai_model(settings, openai_client=openai_client)
        resolver = PydanticAISemanticResolver(model)
        values = await resolver.extract_from_history(
            session_id="gateway-test",
            messages=[ChatMessage(role="user", content="Nazwa pipeline to customer_daily.")],
            requirements=[
                Requirement(
                    path="metadata.id",
                    question="Jak ma się nazywać pipeline?",
                    value_schema={"type": "string"},
                )
            ],
            contract={},
        )
        await resolver.close()

    assert values == {"metadata.id": "customer_daily"}
    assert captured_request["model"] == "auto"
    assert captured_request["response_format"] == {"type": "json_object"}
    assert "tool_choice" not in captured_request
