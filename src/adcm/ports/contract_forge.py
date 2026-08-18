from typing import Protocol

from adcm.domain.models import (
    ContractEvaluationResult,
    ContractInput,
    FinalValidationResult,
    RenderedContract,
    RenderRequest,
)


class ContractForgePort(Protocol):
    async def evaluate_draft(self, request: ContractInput) -> ContractEvaluationResult: ...

    async def validate_final(self, request: ContractInput) -> FinalValidationResult: ...

    async def render_yaml(self, request: RenderRequest) -> RenderedContract: ...
