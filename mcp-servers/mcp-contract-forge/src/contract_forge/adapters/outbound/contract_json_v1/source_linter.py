from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class SourceProblem:
    code: str
    location: str
    message: str

def lint_source(raw: dict[str, Any]) -> list[SourceProblem]:
    defs=raw.get("$defs",{})
    out: list[SourceProblem]=[]
    def walk(value: Any, location: str) -> None:
        if isinstance(value,dict):
            ref=value.get("$ref")
            if isinstance(ref,str) and ref.startswith("#/$defs/"):
                name=ref.split("/")[-1]
                if name not in defs:
                    out.append(SourceProblem("dangling_ref",location,f"Missing $defs entry: {name}"))
            for k,v in value.items(): walk(v,f"{location}.{k}")
        elif isinstance(value,list):
            for i,v in enumerate(value): walk(v,f"{location}[{i}]")
    walk(raw,"$")
    return out
