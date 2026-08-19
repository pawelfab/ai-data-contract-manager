from __future__ import annotations

import logging

from .gateway import ForgeGateway, MCPForgeGateway
from .model_factory import build_pydantic_ai_model
from .orchestrator import ADCMOrchestrator
from .semantic import NoopSemanticResolver, PydanticAISemanticResolver
from .settings import ADCMSettings, load_settings

logger = logging.getLogger(__name__)


def build_gateway(settings: ADCMSettings | None = None) -> ForgeGateway:
    settings = settings or load_settings()
    return MCPForgeGateway(settings.mcp_url)


def build_semantic(settings: ADCMSettings | None = None):
    settings = settings or load_settings()
    if settings.llm_mode == "pydantic":
        return PydanticAISemanticResolver(build_pydantic_ai_model(settings))
    return NoopSemanticResolver()


def build_orchestrator(
    settings: ADCMSettings | None = None,
) -> ADCMOrchestrator:
    settings = settings or load_settings()
    summary = settings.public_runtime_summary()
    logger.info(
        "ADCM runtime configured: forge_gateway=%s llm_mode=%s llm_provider=%s llm_model=%s",
        summary["forge_gateway"],
        summary["llm_mode"],
        summary["llm_provider"],
        summary["llm_model"],
    )
    return ADCMOrchestrator(
        build_gateway(settings=settings),
        semantic=build_semantic(settings),
        semantic_confidence_threshold=settings.llm_confidence_threshold,
    )
