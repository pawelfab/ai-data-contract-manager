from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContractDefinition(BaseModel):
    """Transport-neutral wrapper around the externally owned contract definition."""

    model_config = ConfigDict(extra="forbid")
    version: str
    schema_document: dict[str, Any]
    enrichments: list[dict[str, Any]] = Field(default_factory=list)
