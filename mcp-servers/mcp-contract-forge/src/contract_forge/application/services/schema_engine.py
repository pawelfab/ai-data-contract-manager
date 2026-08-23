from typing import Any
from contract_forge.domain.evaluation.models import Requirement, SuggestedValue, ValidationIssue
from contract_forge.utils.pointer import get_pointer, exists_pointer

NULL=object()

# Discovery annotation, deliberately separate from `minItems`:
#   minItems   -> how many elements the contract requires (validation)
#   EXPAND_ITEMS -> whether Forge may turn those into per-field requirements (discovery)
# The flag is permission, minItems is the count: a flag without minItems expands nothing.
# By default an array is atomic — the array itself is the requirement, filled as a whole.
EXPAND_ITEMS="x-requirement-expand-items"

def evaluate_schema(raw:dict, defs:dict, document:dict) -> tuple[list[Requirement],list[SuggestedValue],list[ValidationIssue]]:
    req=[]; sug=[]; issues=[]
    _walk(raw,"",document,defs,True,req,sug,issues)
    return _dedup_req(req),_dedup_sug(sug),issues

def _walk(schema:dict,path:str,document:dict,defs:dict,active:bool,req,sug,issues):
    if not active: return
    if "$ref" in schema:
        name=schema["$ref"].split("/")[-1]; target=defs.get(name)
        if target: _walk(target,path,document,defs,active,req,sug,issues)
        return
    # anyOf: choose non-null ref/object branch when the value exists, otherwise collect defaults only conservatively
    if "anyOf" in schema:
        value=get_pointer(document,path,NULL) if path else document
        branches=[b for b in schema["anyOf"] if b.get("type")!="null"]
        if value is not NULL and value is not None:
            for b in branches: _walk(b,path,document,defs,True,req,sug,issues)
        if "default" in schema and path and not exists_pointer(document,path): sug.append(SuggestedValue(path=path,value=schema["default"],source="default",priority=10))
        return
    if "default" in schema and path and not exists_pointer(document,path): sug.append(SuggestedValue(path=path,value=schema["default"],source="default",priority=10))
    required_names=set(schema.get("required",[])); props=schema.get("properties",{})
    for name,child in props.items():
        child_path=path+"/"+_esc(name)
        present=exists_pointer(document,child_path)
        if name in required_names and not present:
            req.append(Requirement(path=child_path,kind="schema",title=child.get("title"),description=child.get("description"),expectedType=_type(child)))
        # descend if child present. For required object refs, descend as well so subrequirements are discoverable.
        # Required arrays are entered too, so cardinality and expansion below can run at all.
        descend=present or (name in required_names and (_objectish(child) or child.get("type")=="array"))
        if descend: _walk(child,child_path,document,defs,True,req,sug,issues)
    if schema.get("type")=="array" and "items" in schema:
        # An absent array must stay distinguishable from a present but empty one.
        arr=get_pointer(document,path,NULL) if path else NULL
        have=arr if isinstance(arr,list) else []
        min_items=int(schema.get("minItems",0) or 0)
        for i in range(len(have)): _walk(schema["items"],f"{path}/{i}",document,defs,True,req,sug,issues)
        # Never invent an index just because the array is required; the contract has to say so.
        if schema.get(EXPAND_ITEMS):
            for i in range(len(have),min_items): _walk(schema["items"],f"{path}/{i}",document,defs,True,req,sug,issues)
        # An absent array already carries its own Requirement, so only report the present-but-short case.
        if arr is not NULL and isinstance(arr,list) and len(have)<min_items:
            issues.append(ValidationIssue(path=path,message=f"Array must contain at least {min_items} item(s), got {len(have)}"))
    # elementary type/enum checks only when present
    if path and exists_pointer(document,path):
        value=get_pointer(document,path)
        enum=schema.get("enum")
        if enum is not None and value not in enum: issues.append(ValidationIssue(path=path,message=f"Value must be one of {enum}"))
        const=schema.get("const")
        if const is not None and value != const: issues.append(ValidationIssue(path=path,message=f"Value must equal {const!r}"))

def _objectish(s):
    return s.get("type")=="object" or "$ref" in s or any("$ref" in b for b in s.get("anyOf",[]) if isinstance(b,dict))
def _type(s):
    if "type" in s: return s["type"]
    for b in s.get("anyOf",[]):
        if b.get("type") not in (None,"null"): return b.get("type")
    return "object" if "$ref" in s else None
def _esc(x): return x.replace("~","~0").replace("/","~1")
def _dedup_req(items):
    out={};
    for x in items: out[x.path]=x
    return list(out.values())
def _dedup_sug(items):
    out={};
    for x in items:
        if x.path not in out or out[x.path].priority<=x.priority: out[x.path]=x
    return list(out.values())
