from pydantic import BaseModel, ConfigDict, Field

from .contract import ContractState
from .forge import ContractStatus, Diagnostic, MissingRequirement


class TurnSnapshot(BaseModel):
    """Stan dokumentu po turze wraz z formalną oceną dokładnie tego stanu.

    Ocena jest kompaktowa i celowo nie jest całą `ForgeAnalysis`: `writable` i
    `proposals` opisują możliwe kolejne kroki, a nie stan, w którym sesja się zatrzymała.
    """

    model_config = ConfigDict(extra="forbid")
    turn_no: int
    revision: int
    document: dict
    contract_status: ContractStatus
    missing: list[MissingRequirement] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class SessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    contract: ContractState = Field(default_factory=ContractState)
    turn_no: int = 0
    snapshots: list[TurnSnapshot] = Field(default_factory=list)
