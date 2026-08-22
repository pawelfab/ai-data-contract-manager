from contract_forge.domain.rules.models import NormalizedRule

def parse_rules(raw: dict) -> list[NormalizedRule]:
    rules=[]
    for model_name, model in raw.get("$defs",{}).items():
        for r in model.get("x-contract-rules",[]):
            executable = bool(r.get("assertion"))
            rules.append(NormalizedRule(id=r.get("id",f"{model_name}.unnamed"),model_name=model_name,local_path=r.get("path"),kind=r.get("kind"),message=r.get("message") or r.get("notes"),severity=r.get("severity","error"),condition=r.get("condition"),assertion=r.get("assertion"),capability="executable" if executable else "unsupported",source=r.get("source",{})))
    return rules
