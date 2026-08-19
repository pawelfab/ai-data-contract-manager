from __future__ import annotations

import logging
from pathlib import Path

from contract_forge.engine import ContractForge
from .gateway import ForgeGateway, LocalForgeGateway, MCPForgeGateway
from .model_factory import build_pydantic_ai_model
from .orchestrator import ADCMOrchestrator
from .semantic import NoopSemanticResolver, PydanticAISemanticResolver
from .settings import ADCMSettings, load_settings, project_root

logger = logging.getLogger(__name__)

def build_local_forge(settings: ADCMSettings | None = None) -> ContractForge:
    settings = settings or load_settings()
    root = project_root()
    schema = settings.contract_schema_path or root / "config" / "contract.json"
    rules = settings.contract_rules_path or root / "config" / "ux_rules_contract_v1.json"
    if not schema.is_absolute():
        schema = root / schema
    if not rules.is_absolute():
        rules = root / rules
    return ContractForge.from_files(Path(schema), Path(rules), deploy_env=settings.deploy_env)


def build_gateway(local_forge: bool = False, settings: ADCMSettings | None = None) -> ForgeGateway:
    settings = settings or load_settings()
    if local_forge or settings.gateway == "local":
        return LocalForgeGateway(build_local_forge(settings))
    return MCPForgeGateway(settings.mcp_url)


def build_semantic(settings: ADCMSettings | None = None):
    settings = settings or load_settings()
    if settings.llm_mode == "pydantic":
        return PydanticAISemanticResolver(build_pydantic_ai_model(settings))
    return NoopSemanticResolver()


def build_orchestrator(
    local_forge: bool = False,
    settings: ADCMSettings | None = None,
) -> ADCMOrchestrator:
    settings = settings or load_settings()
    summary = settings.public_runtime_summary()
    logger.info(
        "ADCM runtime configured: deploy_env=%s forge_gateway=%s llm_mode=%s llm_provider=%s llm_model=%s",
        summary["deploy_env"],
        "local" if local_forge else summary["forge_gateway"],
        summary["llm_mode"],
        summary["llm_provider"],
        summary["llm_model"],
    )
    return ADCMOrchestrator(
        build_gateway(local_forge=local_forge, settings=settings),
        semantic=build_semantic(settings),
    )
