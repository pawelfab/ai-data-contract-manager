from __future__ import annotations

from typing import Any

from .settings import ADCMSettings


def _openai_model_name(configured_model: str) -> str:
    prefix, separator, model_name = configured_model.partition(":")
    if separator and prefix in {"openai", "openai-chat", "openai-responses"}:
        return model_name
    return configured_model


def build_pydantic_ai_model(settings: ADCMSettings, *, openai_client: Any = None) -> Any:
    """Build the model used by the constrained semantic resolver."""
    provider = settings.resolved_llm_provider

    if provider == "vertex":
        try:
            from pydantic_ai.models.google import GoogleModel
        except ImportError as exc:  # pragma: no cover - depends on optional installation
            raise RuntimeError('Install Vertex extras: pip install -e ".[vertex]"') from exc
        return GoogleModel(settings.vertex_model, provider="google-cloud")

    if provider == "openai_compatible":
        try:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.profiles.openai import OpenAIModelProfile
            from pydantic_ai.providers.openai import OpenAIProvider
        except ImportError as exc:  # pragma: no cover - depends on optional installation
            raise RuntimeError('Install OpenAI extras: pip install -e ".[openai]"') from exc

        if openai_client is None:
            openai_provider = OpenAIProvider(
                base_url=settings.openai_base_url,
                api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            )
        else:
            openai_provider = OpenAIProvider(openai_client=openai_client)

        return OpenAIChatModel(
            _openai_model_name(settings.model),
            provider=openai_provider,
            profile=OpenAIModelProfile(
                default_structured_output_mode="prompted",
                supports_json_object_output=True,
                openai_supports_tool_choice_required=False,
                openai_supports_strict_tool_definition=False,
            ),
        )

    return settings.model
