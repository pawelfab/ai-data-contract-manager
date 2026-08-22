from typing import Any
from contract_forge.domain.evaluation.models import Requirement, SuggestedValue, ValidationIssue
from contract_forge.utils.pointer import get_pointer, exists_pointer

NULL=object()

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
        descend=present or (name in required_names and _objectish(child))
        if descend: _walk(child,child_path,document,defs,True,req,sug,issues)
    # arrays: walk existing elements
    if schema.get("type")=="array" and "items" in schema:
        arr=get_pointer(document,path,[]) if path else []
        if isinstance(arr,list):
            for i,_ in enumerate(arr): _walk(schema["items"],f"{path}/{i}",document,defs,True,req,sug,issues)
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
