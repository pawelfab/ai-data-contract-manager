from adcm.domain.contract_path import ContractPath
from adcm.domain.models import ContractDraft, CurrentSchemaView, ResolvedValue


class DraftProjector:
    """Rebuilds the draft from resolved values and the CURRENT schema view."""

    def project(
        self,
        resolved: dict[str, ResolvedValue],
        schema_view: CurrentSchemaView,
        revision: int,
    ) -> ContractDraft:
        document: dict = {}
        for path, item in resolved.items():
            if schema_view.is_path_allowed(path):
                ContractPath.write(document, path, item.value)
        return ContractDraft(values=document, revision=revision)
