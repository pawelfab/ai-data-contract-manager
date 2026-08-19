from adcm.domain.contract_path import ContractPath
from adcm.domain.models import AllowedPath, CandidateScope, Preference, ValueCandidate


class PreferenceExpander:
    """Expands cross-cutting preferences only onto currently authorized paths."""

    def expand(
        self,
        preferences: list[Preference],
        allowed_paths: list[AllowedPath],
    ) -> list[ValueCandidate]:
        result: list[ValueCandidate] = []
        for preference in preferences:
            if not preference.active:
                continue
            for allowed in allowed_paths:
                try:
                    ContractPath.parse(allowed.path)
                except ValueError:
                    continue
                if preference.concept in allowed.concepts:
                    result.append(
                        ValueCandidate(
                            path=allowed.path,
                            value=preference.value,
                            origin=preference.origin,
                            evidence_ids=list(preference.evidence_ids),
                            scope=CandidateScope.USER,
                            source_preference_id=preference.id,
                            created_revision=preference.created_revision,
                            reason=f"expanded preference:{preference.concept}",
                        )
                    )
        return result
