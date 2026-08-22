from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contract_forge.domain.enrichment.models import (
    EnrichmentCondition,
    EnrichmentContext,
    EnrichmentRule,
    EnrichmentScope,
)


class JsonEnrichmentRepository:
    """Declarative enrichment storage adapter.

    It maps storage data to EnrichmentRule only. Runtime matching belongs to
    EnrichmentResolver, never to the repository adapter.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_rules(self, context: EnrichmentContext) -> list[EnrichmentRule]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return self._parse(raw)

    def _parse(self, raw: dict[str, Any]) -> list[EnrichmentRule]:
        output: list[EnrichmentRule] = []
        for item in raw.get("rules", []):
            output.append(
                EnrichmentRule(
                    id=item["id"],
                    path=item.get("path"),
                    path_pattern=item.get("pathPattern"),
                    value=item.get("value"),
                    value_from=item.get("valueFrom"),
                    conditions=_conditions(item.get("when")),
                    scope=_scope(item),
                    priority=int(item.get("priority", 0)),
                    source_ref=item.get("sourceRef") or f"{self.path}#rules.{item['id']}",
                    system=item.get("system"),
                    user_id=str(item["userId"]) if item.get("userId") is not None else None,
                )
            )
        return output


EnrichmentJsonAdapter = JsonEnrichmentRepository
JsonEnrichmentAdapter = JsonEnrichmentRepository


def _conditions(raw: Any) -> list[EnrichmentCondition]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [EnrichmentCondition.model_validate(x) for x in raw]
    if isinstance(raw, dict) and "path" in raw:
        return [EnrichmentCondition.model_validate(raw)]
    raise ValueError("Unsupported enrichment 'when' format")


def _scope(item: dict[str, Any]) -> EnrichmentScope:
    explicit = item.get("scope")
    if explicit:
        return EnrichmentScope[explicit.upper()]
    if item.get("userId") is not None:
        return EnrichmentScope.USER
    if item.get("system") is not None:
        return EnrichmentScope.SYSTEM
    return EnrichmentScope.GLOBAL
