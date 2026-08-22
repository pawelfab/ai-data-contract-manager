from typing import Any, Protocol


class ContractSourcePort(Protocol):
    """Loads raw contract data only. It does not understand contract structure."""

    def load_raw(self) -> dict[str, Any]: ...
