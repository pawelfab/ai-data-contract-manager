from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ValueSource(StrEnum):
    SYSTEM = "system"
    USER_EXPLICIT = "user_explicit"
    USER_RULE = "user_rule"
    APP_RULE = "app_rule"
    FORGE_ENRICHMENT = "forge_enrichment"
    FORGE_DEFAULT = "forge_default"


AUTHORITY: dict[ValueSource, int] = {
    ValueSource.SYSTEM: 100,
    ValueSource.FORGE_DEFAULT: 10,
    ValueSource.FORGE_ENRICHMENT: 20,
    ValueSource.APP_RULE: 30,
    ValueSource.USER_RULE: 40,
    ValueSource.USER_EXPLICIT: 50,
}


class ValueProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: ValueSource
    producer_id: str | None = None
    revision: int
    derived_from: list[str] = Field(default_factory=list)
