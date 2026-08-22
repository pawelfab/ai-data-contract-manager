from typing import Any
from contract_forge.domain.schema.models import SchemaNode

def parse_schema(raw: dict[str,Any]) -> SchemaNode:
    return _node(raw,"",False)

def _node(raw: dict[str,Any], path: str, required: bool) -> SchemaNode:
    typ=raw.get("type")
    if not typ and "$ref" in raw: typ="object"
    n=SchemaNode(path=path,title=raw.get("title"),description=raw.get("description"),type=typ,required=required,default=raw.get("default"),has_default="default" in raw,enum=raw.get("enum"),const=raw.get("const"),ref=raw.get("$ref"))
    required_names=set(raw.get("required",[]))
    for name,spec in raw.get("properties",{}).items():
        child_path=path+"/"+_esc(name)
        n.children.append(_node(spec,child_path,name in required_names))
    if "items" in raw and isinstance(raw["items"],dict): n.item=_node(raw["items"],path+"/*",False)
    for alt in raw.get("anyOf",[]):
        if isinstance(alt,dict): n.any_of.append(_node(alt,path,required))
    return n

def _esc(x): return x.replace("~","~0").replace("/","~1")
