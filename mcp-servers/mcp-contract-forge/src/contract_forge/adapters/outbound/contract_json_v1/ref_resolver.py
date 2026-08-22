def resolve_ref(ref: str, defs: dict) -> dict:
    prefix="#/$defs/"
    if not ref.startswith(prefix): raise ValueError(f"Unsupported ref: {ref}")
    return defs[ref[len(prefix):]]
