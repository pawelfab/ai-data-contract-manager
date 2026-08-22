from typing import Any
_MISSING=object()
def parts(pointer:str):
    if pointer=="": return []
    return [p.replace("~1","/").replace("~0","~") for p in pointer.lstrip("/").split("/")]
def get_pointer(doc:Any,pointer:str,default=None):
    cur=doc
    try:
        for p in parts(pointer): cur=cur[int(p)] if isinstance(cur,list) else cur[p]
        return cur
    except (KeyError,IndexError,TypeError,ValueError): return default
def exists_pointer(doc,pointer): return get_pointer(doc,pointer,_MISSING) is not _MISSING

def join(base:str,local:str|None):
    if not local: return base
    tokens=local.replace("[*]","/*").split(".")
    return (base.rstrip("/")+"/"+"/".join(tokens)).replace("//","/")
