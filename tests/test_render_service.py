import pytest

from adcm.adapters.mcp.mock_contract_forge import MockContractForgeAdapter
from adcm.application.render_service import ContractRenderService
from adcm.domain.models import (
    ContractDraft,
    FinalValidationReceipt,
    FinalValidationStatus,
    RenderMode,
)


@pytest.mark.asyncio
async def test_render_cache_key_includes_schema_revision_and_mode():
    service = ContractRenderService(MockContractForgeAdapter())
    draft = ContractDraft(values={"metadata": {"id": "x"}})
    rendered = await service.render(draft, "mock-schema-v2", RenderMode.DRAFT)
    assert "metadata:" in rendered.content
    assert rendered.mode == RenderMode.DRAFT


@pytest.mark.asyncio
async def test_final_render_requires_validation_for_same_draft_and_schema():
    service = ContractRenderService(MockContractForgeAdapter())
    draft = ContractDraft(values={"metadata": {"id": "x"}})

    with pytest.raises(ValueError):
        await service.render(draft, "mock-schema-v2", RenderMode.FINAL)

    valid = FinalValidationReceipt(
        status=FinalValidationStatus.VALID,
        draft_hash=draft.canonical_hash(),
        schema_revision="mock-schema-v2",
    )
    rendered = await service.render(
        draft,
        "mock-schema-v2",
        RenderMode.FINAL,
        final_validation=valid,
    )
    assert rendered.mode == RenderMode.FINAL

    changed = ContractDraft(values={"metadata": {"id": "y"}})
    with pytest.raises(ValueError):
        await service.render(
            changed,
            "mock-schema-v2",
            RenderMode.FINAL,
            final_validation=valid,
        )
