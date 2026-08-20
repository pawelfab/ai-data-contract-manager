from __future__ import annotations

from typing import Any, Protocol


class ContractSourcePort(Protocol):
    """Port used by Contract Forge to obtain the parsed contract definition.

    The Forge engine does not know whether the contract came from a local file,
    an HTTP API, object storage, database, or another source. Adapters own I/O
    and JSON parsing; Forge owns interpretation and validation.
    """

    def load_contract(self) -> dict[str, Any]: ...
