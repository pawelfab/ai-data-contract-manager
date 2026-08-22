from datetime import datetime, timezone
from pydantic import BaseModel, Field
from adcm.domain.contract.value import Authority


class EvidenceItem(BaseModel):
    id: str
    source_type: str
    content: str
    source_ref: str | None = None
    authority: Authority = Authority.USER_DIRECT
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    role: str
    content: str
