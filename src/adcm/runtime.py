from __future__ import annotations

import os
from pathlib import Path

from contract_forge.engine import ContractForge
from .gateway import ForgeGateway, LocalForgeGateway, MCPForgeGateway
from .orchestrator import ADCMOrchestrator
from .semantic import NoopSemanticResolver, PydanticAISemanticResolver


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_local_forge() -> ContractForge:
    root = project_root()
    schema = Path(os.getenv("CONTRACT_SCHEMA_PATH", root / "config" / "contract.json"))
    rules = Path(os.getenv("CONTRACT_RULES_PATH", root / "config" / "ux_rules_contract_v1.json"))
    deploy_env = os.getenv("ADCM_DEPLOY_ENV", "dev")
    return ContractForge.from_files(schema, rules, deploy_env=deploy_env)


def build_gateway(local_forge: bool = False) -> ForgeGateway:
    if local_forge or os.getenv("ADCM_GATEWAY", "mcp").lower() == "local":
        return LocalForgeGateway(build_local_forge())
    return MCPForgeGateway(os.getenv("ADCM_MCP_URL", "http://127.0.0.1:8001/mcp"))


def build_semantic():
    if os.getenv("ADCM_LLM_MODE", "local").lower() == "pydantic":
        return PydanticAISemanticResolver()
    return NoopSemanticResolver()


def build_orchestrator(local_forge: bool = False) -> ADCMOrchestrator:
    return ADCMOrchestrator(build_gateway(local_forge=local_forge), semantic=build_semantic())
