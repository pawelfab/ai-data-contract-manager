from __future__ import annotations

from copy import deepcopy
from typing import Any

from adcm.gateway import ForgeGateway
from adcm.models import ForgeState, Origin, Requirement


class FakeForgeGateway(ForgeGateway):
    """Deterministic MCP boundary fake; it intentionally contains no Forge imports."""

    def __init__(self) -> None:
        self.session_id = "forge-test-session"
        self.source_system: str | None = None
        self.contract: dict[str, Any] = {}

    async def start_session(self) -> ForgeState:
        return self._state()

    async def get_state(self, session_id: str) -> ForgeState:
        self._check_session(session_id)
        return self._state()

    async def submit_values(
        self,
        session_id: str,
        values: dict[str, Any],
        origin: Origin,
    ) -> ForgeState:
        self._check_session(session_id)
        allowed = {requirement.path for requirement in self._requirements()}
        for path, value in values.items():
            if path not in allowed:
                continue
            if path == "metadata.sourceSystemGcpId":
                candidate = str(value).lower()
                if candidate not in {"rocket", "sap"}:
                    continue
                self.source_system = candidate
                self._set(path, candidate.upper())
                self._set("source.sourceType", "fixed_width" if candidate == "rocket" else "csv")
            else:
                self._set(path, value)
        return self._state()

    def _state(self) -> ForgeState:
        pending = self._requirements()
        return ForgeState(
            session_id=self.session_id,
            source_system=self.source_system,
            contract=deepcopy(self.contract),
            status="needs_input" if pending else "complete",
            pending=pending,
        )

    def _requirements(self) -> list[Requirement]:
        if self.source_system is None:
            return [
                Requirement(
                    path="metadata.sourceSystemGcpId",
                    question="Jaki jest system źródłowy?",
                    reason="source_system",
                    input_mode="explicit",
                    allowed_values=["rocket", "sap"],
                    value_schema={"type": "string", "enum": ["rocket", "sap"]},
                )
            ]

        definitions = (
            ("metadata.id", "Jak ma się nazywać pipeline?", "explicit", {"type": "string"}),
            ("metadata.owner", "Kto jest właścicielem?", "semantic", {"type": "string"}),
            ("source.uri", "Gdzie znajduje się źródło?", "semantic", {"type": "string"}),
            ("source.columns", "Podaj kolumny.", "semantic", {"type": "array"}),
        )
        return [
            Requirement(path=path, question=question, input_mode=input_mode, value_schema=value_schema)
            for path, question, input_mode, value_schema in definitions
            if not self._has(path)
        ]

    def _has(self, path: str) -> bool:
        current: Any = self.contract
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def _set(self, path: str, value: Any) -> None:
        current = self.contract
        parts = path.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def _check_session(self, session_id: str) -> None:
        if session_id != self.session_id:
            raise KeyError(session_id)
