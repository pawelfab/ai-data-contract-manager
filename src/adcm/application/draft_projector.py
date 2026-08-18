from adcm.domain.models import ContractDraft, ResolvedValue


class DraftProjector:
    """Hard schema-authority boundary."""

    def project(
        self,
        resolved: dict[str, ResolvedValue],
        allowed_paths: set[str],
        revision: int,
    ) -> ContractDraft:
        values = {
            path: item.value
            for path, item in resolved.items()
            if path in allowed_paths
        }
        return ContractDraft(values=values, revision=revision)
