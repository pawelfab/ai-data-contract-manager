import json
from pathlib import Path

from adcm.domain.rules import RulesDocument


class FileRulesRepository:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    async def load(self, session_id: str | None = None) -> RulesDocument:
        # Baseline: only default rules. User-specific overlay will be added behind this port.
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return RulesDocument.model_validate(data)
