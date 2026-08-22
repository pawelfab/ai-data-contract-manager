from pydantic import BaseModel, Field


class AdvisoryIssue(BaseModel):
    severity: str = "warning"
    message: str
    paths: list[str] = Field(default_factory=list)
    requires_user_decision: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
