from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class Authority(StrEnum):
    """How strongly a value should be treated by ADCM.

    The numeric ordering is deliberately not encoded in the enum. Selection policy lives
    in application code so the domain vocabulary can stay stable.
    """

    USER_DIRECT = "user_direct"
    USER_REFERENCED = "user_referenced"
    SYSTEM_RULE = "system_rule"
    OBSERVED_CONVENTION = "observed_convention"
    DEFAULT = "default"


class Provenance(BaseModel):
    source_type: str
    source_ref: str | None = None
    evidence_id: str | None = None
    rule_id: str | None = None


class UserValueEvent(BaseModel):
    path: str
    value: Any
    authority: Authority = Authority.USER_DIRECT
    provenance: Provenance
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DerivedValue(BaseModel):
    path: str
    value: Any
    source: str
    priority: int = 0
    provenance: Provenance | None = None
