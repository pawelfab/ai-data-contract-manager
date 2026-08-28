from copy import deepcopy

from adcm.domain.contract import ContractState
from adcm.domain.mutations import MutationCommand, MutationEvent, MutationOperation
from adcm.domain.provenance import ValueProvenance

from .json_pointer import JsonPointerError, exists, get, parent_and_token


class DocumentEngine:
    def apply(self, state: ContractState, commands: list[MutationCommand]) -> list[MutationEvent]:
        events: list[MutationEvent] = []
        for command in commands:
            event = self._apply_one(state, command)
            if event is not None:
                events.append(event)
        return events

    def _apply_one(self, state: ContractState, command: MutationCommand) -> MutationEvent | None:
        old_exists = exists(state.document, command.path)
        old_value = deepcopy(get(state.document, command.path)) if old_exists else None

        if command.operation == MutationOperation.ADD:
            self._add(state.document, command.path, deepcopy(command.value))
        elif command.operation == MutationOperation.REPLACE:
            if not old_exists:
                raise JsonPointerError(f"replace target does not exist: {command.path}")
            self._replace(state.document, command.path, deepcopy(command.value))
        elif command.operation == MutationOperation.REMOVE:
            if not old_exists:
                return None
            self._remove(state.document, command.path)
        else:  # pragma: no cover
            raise ValueError(command.operation)

        new_exists = exists(state.document, command.path)
        new_value = deepcopy(get(state.document, command.path)) if new_exists else None
        if old_exists == new_exists and old_value == new_value:
            return None

        before = state.revision
        state.revision += 1
        self._drop_provenance_at_or_below(state, command.path)
        if command.operation == MutationOperation.REMOVE:
            self._prune_empty_ancestors(state, command.path)
        else:
            state.provenance[command.path] = ValueProvenance(
                source=command.source,
                producer_id=command.producer_id,
                revision=state.revision,
                derived_from=command.derived_from,
            )

        event = MutationEvent(
            mutation_id=command.id,
            revision_before=before,
            revision_after=state.revision,
            operation=command.operation,
            path=command.path,
            old_exists=old_exists,
            old_value=old_value,
            new_exists=new_exists,
            new_value=new_value,
            source=command.source,
            producer_id=command.producer_id,
            reason=command.reason,
        )
        state.mutation_log.append(event)
        return event

    @staticmethod
    def _add(document: dict, path: str, value) -> None:
        parent, token = parent_and_token(document, path)
        if isinstance(parent, dict):
            parent[token] = value
            return
        if isinstance(parent, list):
            if token == "-":
                parent.append(value)
                return
            idx = int(token)
            if idx > len(parent):
                raise JsonPointerError(f"list add index {idx} is greater than length {len(parent)}")
            parent.insert(idx, value)
            return
        raise JsonPointerError(f"cannot add to scalar parent: {path}")

    @staticmethod
    def _replace(document: dict, path: str, value) -> None:
        parent, token = parent_and_token(document, path)
        if isinstance(parent, dict):
            if token not in parent:
                raise JsonPointerError(f"replace target does not exist: {path}")
            parent[token] = value
            return
        if isinstance(parent, list):
            idx = int(token)
            if idx >= len(parent):
                raise JsonPointerError(f"replace index out of range: {path}")
            parent[idx] = value
            return
        raise JsonPointerError(f"cannot replace in scalar parent: {path}")

    @staticmethod
    def _remove(document: dict, path: str) -> None:
        parent, token = parent_and_token(document, path)
        if isinstance(parent, dict):
            del parent[token]
            return
        if isinstance(parent, list):
            idx = int(token)
            del parent[idx]
            return
        raise JsonPointerError(f"cannot remove from scalar parent: {path}")


    def _prune_empty_ancestors(self, state: ContractState, path: str) -> None:
        raw_tokens = path[1:].split("/") if path.startswith("/") else []
        # Walk from the immediate parent toward the root. Never prune a container
        # that has its own provenance (e.g. an intentionally activated empty section).
        for size in range(len(raw_tokens) - 1, 0, -1):
            parent_path = "/" + "/".join(raw_tokens[:size])
            if parent_path in state.provenance or not exists(state.document, parent_path):
                continue
            value = get(state.document, parent_path)
            if value not in ({}, []):
                break
            self._remove(state.document, parent_path)

    @staticmethod
    def _drop_provenance_at_or_below(state: ContractState, path: str) -> None:
        prefix = path + "/"
        for key in [key for key in state.provenance if key == path or key.startswith(prefix)]:
            state.provenance.pop(key, None)
