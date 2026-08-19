import json

import httpx
import pytest

pytest.importorskip("pydantic_ai")
openai = pytest.importorskip("openai")

from adcm.model_factory import build_pydantic_ai_model
from adcm.models import (
    ChatMessage,
    ExtractionMethod,
    Origin,
    Requirement,
    UserFact,
)
from adcm.semantic import CandidateValue, ExtractionResult, PydanticAISemanticResolver
from adcm.settings import ADCMSettings


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
                                            "path": "metadata.owner",
                                            "value": "FinOps",
                                            "confidence": 0.99,
                                            "evidence": "Opiekunem jest FinOps.",
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
        result = await resolver.extract_from_history(
            session_id="gateway-test",
            messages=[
                ChatMessage(
                    role="user",
                    content="Opiekunem jest FinOps.",
                    message_sequence=1,
                )
            ],
            pending=[
                Requirement(
                    path="metadata.owner",
                    question="Kto jest właścicielem?",
                    value_schema={
                        "type": "string",
                        "description": "Zespół odpowiedzialny za pipeline.",
                        "examples": ["FinOps"],
                    },
                )
            ],
            overridable=[
                Requirement(
                    path="orchestration.schedule",
                    question="Podaj harmonogram.",
                    value_schema={"type": "string", "description": "Linux cron."},
                    current_value="0 0 * * *",
                    current_origin=Origin.SYSTEM_ENRICHMENT,
                )
            ],
            user_facts=[
                UserFact(
                    path="metadata.id",
                    value="customer_daily",
                    message_sequence=2,
                    extraction_method=ExtractionMethod.DETERMINISTIC,
                )
            ],
        )
        await resolver.close()

    assert result == ExtractionResult(
        values=[
            CandidateValue(
                path="metadata.owner",
                value="FinOps",
                confidence=0.99,
                evidence="Opiekunem jest FinOps.",
            )
        ]
    )
    assert captured_request["model"] == "auto"
    assert captured_request["response_format"] == {"type": "json_object"}
    assert "tool_choice" not in captured_request
    request_text = json.dumps(captured_request["messages"], ensure_ascii=False)
    assert "PENDING REQUIREMENTS" in request_text
    assert "ALLOWED PATHS" in request_text
    assert "orchestration.schedule" in request_text
    assert "system_enrichment" in request_text
    assert "EXISTING USER FACTS" in request_text
    assert "CURRENT CONTRACT" not in request_text
