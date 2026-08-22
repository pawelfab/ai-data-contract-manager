import json
from pathlib import Path

from contract_forge.domain.discovery.models import DiscoveryPolicy


class JsonDiscoveryPolicyRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_policy(self) -> DiscoveryPolicy:
        if not self.path.exists():
            return DiscoveryPolicy()
        return DiscoveryPolicy.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
