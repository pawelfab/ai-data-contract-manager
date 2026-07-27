from __future__ import annotations

from dataclasses import dataclass

from .audit import AuditService
from .contract_port import ContractPort
from .session_port import SessionStatePort
from .settings import AppSettings


@dataclass
class AppDeps:
    store: SessionStatePort
    contract_port: ContractPort
    audit: AuditService
    settings: AppSettings
