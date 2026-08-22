from typing import Any

from pydantic import BaseModel, Field

from .path import set_pointer
from .value import Authority, DerivedValue, Provenance, UserValueEvent


class ContractState(BaseModel):
    user_events: list[UserValueEvent] = Field(default_factory=list)
    derived_values: dict[str, DerivedValue] = Field(default_factory=dict)

    def set_user(
        self,
        path: str,
        value: Any,
        *,
        authority: Authority = Authority.USER_DIRECT,
        provenance: Provenance | None = None,
    ) -> None:
        provenance = provenance or Provenance(source_type="chat")
        self.user_events.append(
            UserValueEvent(path=path, value=value, authority=authority, provenance=provenance)
        )

    def latest_user_values(self) -> dict[str, UserValueEvent]:
        result: dict[str, UserValueEvent] = {}
        for event in self.user_events:
            result[event.path] = event
        return result


    def set_derived(self, item: DerivedValue) -> bool:
        existing = self.derived_values.get(item.path)
        if existing and existing.priority > item.priority:
            return False
        changed = existing != item
        self.derived_values[item.path] = item
        return changed

    def replace_derived(self, values: dict[str, DerivedValue]) -> bool:
        changed = self.derived_values != values
        self.derived_values = values
        return changed

    def clear_derived(self) -> None:
        self.derived_values.clear()

    def user_document(self) -> dict[str, Any]:
        doc: dict[str, Any] = {}
        for event in self.latest_user_values().values():
            doc = set_pointer(doc, event.path, event.value)
        return doc

    def effective_document(self) -> dict[str, Any]:
        doc: dict[str, Any] = {}
        for item in sorted(self.derived_values.values(), key=lambda x: x.priority):
            doc = set_pointer(doc, item.path, item.value)
        for event in self.latest_user_values().values():
            doc = set_pointer(doc, event.path, event.value)
        return doc
