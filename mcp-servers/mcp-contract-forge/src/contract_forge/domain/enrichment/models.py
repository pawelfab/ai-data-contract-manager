from __future__ import annotations

from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class EnrichmentScope(IntEnum):
    """Precedence inside Forge-derived suggestions only."""

    GLOBAL = 10
    SYSTEM = 20
    USER = 30


class EnrichmentCondition(BaseModel):
    path: str
    equals: Any | None = None
    exists: bool | None = None


class EnrichmentRule(BaseModel):
    id: str
    path: str | None = None
    path_pattern: str | None = None
    value: Any = None
    value_from: str | None = None
    conditions: list[EnrichmentCondition] = Field(default_factory=list)
    scope: EnrichmentScope = EnrichmentScope.GLOBAL
    priority: int = 0
    source_ref: str | None = None
    system: str | None = None
    user_id: str | None = None


class EnrichmentContext(BaseModel):
    user_id: str | None = None
    source_system: str | None = None
