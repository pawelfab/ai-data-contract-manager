from __future__ import annotations

from pydantic_ai import Agent

from .audit import (
    AuditLogPort,
    AuditService,
    AuditedContractPort,
    JsonlAuditLogAdapter,
    NullAuditLogAdapter,
)
from .audit.capability import create_audit_hooks
from .contract_port import (
    ContractPort,
    InProcessContractPort,
    McpContractPort,
)
from .dependencies import AppDeps
from .instructions import BASE_INSTRUCTIONS
from .session_port import SessionStatePort
from .session_store import InMemorySessionStore
from .settings import AppSettings
from .tools.contract import register_contract_tools


def create_agent(
    settings: AppSettings | None = None,
    *,
    audit_port: AuditLogPort | None = None,
    session_store: SessionStatePort | None = None,
) -> tuple[Agent[AppDeps, str], AppDeps]:
    settings = settings or AppSettings.from_env()
    base_port: ContractPort
    if settings.contract_transport == "inprocess":
        base_port = InProcessContractPort()
    else:
        base_port = McpContractPort(
            timeout_seconds=settings.mcp_timeout_seconds
        )
    if audit_port is None:
        audit_port = (
            JsonlAuditLogAdapter(settings.audit_dir)
            if settings.audit_enabled
            else NullAuditLogAdapter()
        )
    audit = AuditService(
        audit_port,
        include_model_io=settings.audit_include_model_io,
        include_mcp_payloads=settings.audit_include_mcp_payloads,
    )
    port = AuditedContractPort(base_port, audit)
    deps = AppDeps(
        store=session_store or InMemorySessionStore(),
        contract_port=port,
        audit=audit,
        settings=settings,
    )
    agent: Agent[AppDeps, str] = Agent(
        settings.model,
        name="turn_orchestrator",
        deps_type=AppDeps,
        output_type=str,
        instructions=BASE_INSTRUCTIONS,
        defer_model_check=True,
        retries={"tools": 2, "output": 1},
        capabilities=[create_audit_hooks()],
    )
    register_contract_tools(agent)
    return agent, deps


# Compatibility alias for code importing the original registration function.
register_agent_behavior = register_contract_tools


__all__ = [
    "AppDeps",
    "BASE_INSTRUCTIONS",
    "create_agent",
    "register_agent_behavior",
]
