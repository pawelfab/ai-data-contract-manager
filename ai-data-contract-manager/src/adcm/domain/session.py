from pydantic import BaseModel, ConfigDict, Field

from .contract import ContractState


class TurnSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_no: int
    revision: int
    document: dict


class SessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    contract: ContractState = Field(default_factory=ContractState)
    turn_no: int = 0
    snapshots: list[TurnSnapshot] = Field(default_factory=list)
