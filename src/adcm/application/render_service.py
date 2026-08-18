from __future__ import annotations

from dataclasses import dataclass

from adcm.domain.models import (
    ContractDraft,
    FinalValidationReceipt,
    FinalValidationStatus,
    RenderMode,
    RenderRequest,
    RenderedContract,
)
from adcm.ports.contract_forge import ContractForgePort


@dataclass(frozen=True)
class RenderCacheKey:
    draft_hash: str
    schema_revision: str
    render_mode: RenderMode


class ContractRenderService:
    """Renders stable drafts and caches by draft hash + schema revision + mode."""

    def __init__(self, forge: ContractForgePort) -> None:
        self.forge = forge
        self._cache: dict[RenderCacheKey, RenderedContract] = {}

    async def render(
        self,
        draft: ContractDraft,
        schema_revision: str,
        mode: RenderMode,
        *,
        final_validation: FinalValidationReceipt | None = None,
    ) -> RenderedContract:
        draft_hash = draft.canonical_hash()
        if mode == RenderMode.FINAL:
            if final_validation is None or final_validation.status != FinalValidationStatus.VALID:
                raise ValueError("FINAL rendering requires VALID final validation")
            if final_validation.draft_hash != draft_hash:
                raise ValueError("FINAL validation belongs to a different draft")
            if final_validation.schema_revision != schema_revision:
                raise ValueError("FINAL validation belongs to a different schema revision")

        key = RenderCacheKey(draft_hash, schema_revision, mode)
        if key not in self._cache:
            self._cache[key] = await self.forge.render_yaml(
                RenderRequest(
                    draft=draft.values,
                    expected_schema_revision=schema_revision,
                    mode=mode,
                )
            )
        return self._cache[key]
