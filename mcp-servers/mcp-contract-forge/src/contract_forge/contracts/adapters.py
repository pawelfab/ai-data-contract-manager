from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class JsonFileContractAdapter:
    """Read and parse a JSON contract from a filesystem path."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_contract(self) -> dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"Contract JSON must contain an object at the root: {self.path}")
        return parsed


class InMemoryContractAdapter:
    """Adapter useful for tests and programmatic embedding."""

    def __init__(self, contract: dict[str, Any]):
        self._contract = deepcopy(contract)

    def load_contract(self) -> dict[str, Any]:
        return deepcopy(self._contract)
