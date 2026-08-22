import json
from pathlib import Path
from typing import Any


class JsonFileContractSource:
    """Filesystem source adapter. It knows JSON I/O, not the contract schema."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_raw(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))
