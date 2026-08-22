import re

from contract_forge.domain.contract.models import ContractSemanticPaths


_TOKEN = re.compile(r"^@([A-Za-z][A-Za-z0-9]*)$")


class UnknownSemanticPath(ValueError):
    pass


class SemanticPathResolver:
    def resolve(self, value: str, paths: ContractSemanticPaths) -> str:
        if not value.startswith("@"):
            return value
        match = _TOKEN.fullmatch(value)
        if not match:
            raise UnknownSemanticPath(f"Invalid semantic token: {value}")
        name = _camel_to_snake(match.group(1))
        if not hasattr(paths, name):
            raise UnknownSemanticPath(f"Unknown semantic token: {value}")
        resolved = getattr(paths, name)
        if not resolved:
            raise UnknownSemanticPath(f"Semantic token is not configured: {value}")
        return resolved


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
