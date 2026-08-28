from copy import deepcopy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .mutations import MutationEvent
from .provenance import ValueProvenance


class ContractState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, ValueProvenance] = Field(default_factory=dict)
    revision: int = 0
    mutation_log: list[MutationEvent] = Field(default_factory=list)

    def snapshot_document(self) -> dict[str, Any]:
        return deepcopy(self.document)
