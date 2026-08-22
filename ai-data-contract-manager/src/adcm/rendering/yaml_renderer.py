import yaml

def render_yaml(document: dict) -> str:
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
