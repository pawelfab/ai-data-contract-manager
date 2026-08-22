from pydantic import BaseModel, Field

from contract_forge.domain.rules.models import NormalizedRule
from contract_forge.domain.schema.models import SchemaNode


class ContractSemanticPaths(BaseModel):
    """Small set of domain anchors whose concrete JSON pointers belong to a contract adapter."""

    source_system: str
    pipeline_id: str | None = None
    source_table: str | None = None
    silver_dataset: str | None = None


class NormalizedContract(BaseModel):
    root: SchemaNode
    rules: list[NormalizedRule] = Field(default_factory=list)
    raw_schema: dict = Field(default_factory=dict)
    defs: dict = Field(default_factory=dict)
    rules_spec_version: str | None = None
    semantic_paths: ContractSemanticPaths
