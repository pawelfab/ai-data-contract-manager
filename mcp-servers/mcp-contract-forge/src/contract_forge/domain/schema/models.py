from typing import Any
from pydantic import BaseModel, Field
class SchemaNode(BaseModel):
    path: str
    title: str|None=None
    description: str|None=None
    type: str|None=None
    required: bool=False
    default: Any=None
    has_default: bool=False
    enum: list[Any]|None=None
    const: Any=None
    ref: str|None=None
    children: list["SchemaNode"] = Field(default_factory=list)
    item: "SchemaNode|None"=None
    any_of: list["SchemaNode"] = Field(default_factory=list)
