from uuid import uuid4

from pydantic import BaseModel, Field

from adcm.domain.contract.state import ContractState
from adcm.domain.evidence.models import EvidenceItem, Message


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    messages: list[Message] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    contract: ContractState = Field(default_factory=ContractState)
