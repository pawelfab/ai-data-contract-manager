import pytest

from adcm.adapters.mcp.mock_contract_forge import MockContractForgeAdapter
from adcm.domain.models import ContractInput, RenderMode, RenderRequest


@pytest.mark.asyncio
async def test_mock_contract_forge_rejects_an_unexpected_schema_revision_for_every_operation() -> None:
    forge = MockContractForgeAdapter()
    input_request = ContractInput(draft={}, expected_schema_revision="unexpected-revision")
    render_request = RenderRequest(
        draft={},
        expected_schema_revision="unexpected-revision",
        mode=RenderMode.DRAFT,
    )

    with pytest.raises(RuntimeError, match="SCHEMA_CHANGED"):
        await forge.evaluate_draft(input_request)
    with pytest.raises(RuntimeError, match="SCHEMA_CHANGED"):
        await forge.validate_final(input_request)
    with pytest.raises(RuntimeError, match="SCHEMA_CHANGED"):
        await forge.render_yaml(render_request)
