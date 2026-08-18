from pathlib import Path
from uuid import UUID
from adcm.domain.models import ConversationState


class JsonFileSessionRepository:
    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: UUID) -> Path:
        return self.directory / f"{session_id}.json"

    async def load(self, session_id: UUID) -> ConversationState | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        return ConversationState.model_validate_json(path.read_text(encoding="utf-8"))

    async def save(self, state: ConversationState) -> None:
        self._path(state.session_id).write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )
