from typing import Any
from pydantic import BaseModel, Field
class NormalizedRule(BaseModel):
    id: str
    model_name: str
    local_path: str|None=None
    kind: str|None=None
    message: str|None=None
    severity: str="error"
    condition: dict[str,Any]|None=None
    assertion: dict[str,Any]|None=None
    capability: str="executable"
    source: dict[str,Any]=Field(default_factory=dict)
