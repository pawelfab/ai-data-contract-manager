from typing import Any
from contract_forge.domain.rules.models import NormalizedRule
from contract_forge.domain.evaluation.models import Requirement, ValidationIssue
from contract_forge.utils.pointer import get_pointer, exists_pointer, join

def evaluate_rules(rules:list[NormalizedRule], raw_schema:dict, document:dict) -> tuple[list[Requirement],list[ValidationIssue]]:
    req=[]; issues=[]
    scopes=_find_model_scopes(raw_schema,document)
    for rule in rules:
        if rule.capability != "executable": continue
        for scope in scopes.get(rule.model_name,[]):
            if rule.condition and not _expr(rule.condition,scope,document): continue
            assertion=rule.assertion or {}
            if rule.kind=="conditional_required" and assertion.get("exists") is True:
                p=join(scope,assertion.get("path") or rule.local_path)
                if not exists_pointer(document,p): req.append(Requirement(path=p,kind="conditional"))
                continue
            if not _expr(assertion,scope,document):
                issues.append(ValidationIssue(path=join(scope,rule.local_path) if rule.local_path else scope,severity=rule.severity,message=rule.message or rule.id,ruleId=rule.id))
    return _uniq_req(req),issues

def _expr(e:dict,scope:str,doc:dict)->bool:
    if "anyOf" in e: return any(_expr(x,scope,doc) for x in e["anyOf"])
    if "allOf" in e: return all(_expr(x,scope,doc) for x in e["allOf"])
    if "not" in e: return not _expr(e["not"],scope,doc)
    path=join(scope,e.get("path")) if e.get("path") else scope
    value=get_pointer(doc,path)
    if "exists" in e: return exists_pointer(doc,path)==bool(e["exists"])
    if "equals" in e: return value==e["equals"]
    if "notEquals" in e: return value!=e["notEquals"]
    if "gtePath" in e:
        other=get_pointer(doc,join(scope,e["gtePath"])); return value is not None and other is not None and value>=other
    if "notIn" in e:
        vals=_wildcard_values(doc,join(scope,e["notIn"])); return value not in vals
    if "existsIn" in e:
        vals=_wildcard_values(doc,join(scope,e["existsIn"]));
        targets=_wildcard_values(doc,path) if "*" in path else [value]
        return all(x in vals for x in targets if x is not None)
    if "equalsPath" in e and "formula" in e:
        # v1 deliberately supports only the formula present in the supplied contract.
        if e["formula"] != "end - start + 1": return False
        start=get_pointer(doc,join(scope,"start")); end=get_pointer(doc,join(scope,"end")); actual=get_pointer(doc,join(scope,e["equalsPath"]))
        return actual is None or (start is not None and end is not None and actual==end-start+1)
    return True

def _wildcard_values(doc,pointer):
    if "/*" not in pointer: return [get_pointer(doc,pointer)]
    pre,post=pointer.split("/*",1); arr=get_pointer(doc,pre,[]); out=[]
    if isinstance(arr,list):
        for i in range(len(arr)): out.append(get_pointer(doc,f"{pre}/{i}{post}"))
    return out

def _find_model_scopes(raw_schema:dict,doc:dict)->dict[str,list[str]]:
    result={}
    def walk(schema,path):
        if "$ref" in schema:
            name=schema["$ref"].split("/")[-1]; result.setdefault(name,[]).append(path)
            target=raw_schema.get("$defs",{}).get(name,{})
            walk(target,path); return
        for name,ch in schema.get("properties",{}).items():
            cp=path+"/"+name
            if exists_pointer(doc,cp) or name in schema.get("required",[]): walk(ch,cp)
        if schema.get("type")=="array" and "items" in schema:
            arr=get_pointer(doc,path,[])
            if isinstance(arr,list):
                for i in range(len(arr)): walk(schema["items"],f"{path}/{i}")
        if "anyOf" in schema and (path=="" or exists_pointer(doc,path)):
            for alt in schema["anyOf"]:
                if alt.get("type")!="null": walk(alt,path)
    walk(raw_schema,""); return result

def _uniq_req(items):
    out={x.path:x for x in items}; return list(out.values())
