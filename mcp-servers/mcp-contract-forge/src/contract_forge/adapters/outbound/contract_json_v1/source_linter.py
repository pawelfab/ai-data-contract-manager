from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from contract_forge.application.services.union_branch_selector import (
    DISCRIMINATOR,
    discriminator_values,
)

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
            out.extend(_lint_union(value,location,defs))
            for k,v in value.items(): walk(v,f"{location}.{k}")
        elif isinstance(value,list):
            for i,v in enumerate(value): walk(v,f"{location}[{i}]")
    walk(raw,"$")
    return out

def _lint_union(node: dict[str, Any], location: str, defs: dict[str, Any]) -> list[SourceProblem]:
    """A discriminated union must be decidable from the contract alone.

    Both defects here are static properties of the schema, so they fail at load time rather
    than surfacing later as a puzzling problem with the user's document.
    """
    annotation=node.get(DISCRIMINATOR)
    branches=node.get("oneOf")
    if not isinstance(annotation,dict) or not isinstance(branches,list):
        return []
    relative=str(annotation.get("path") or "")
    if not relative:
        return [SourceProblem("discriminator_without_path",location,f"{DISCRIMINATOR} needs a 'path'")]
    problems: list[SourceProblem]=[]
    seen: dict[Any,int]={}
    for index,branch in enumerate(branches):
        values=discriminator_values(branch,relative,defs)
        if not values:
            problems.append(SourceProblem(
                "discriminator_without_values",
                f"{location}.oneOf[{index}]",
                f"Branch declares no const/enum for discriminator {relative!r}",
            ))
            continue
        for value in values:
            if value in seen:
                problems.append(SourceProblem(
                    "ambiguous_discriminator",
                    f"{location}.oneOf[{index}]",
                    f"Discriminator value {value!r} is already claimed by branch {seen[value]}",
                ))
            else:
                seen[value]=index
    return problems
