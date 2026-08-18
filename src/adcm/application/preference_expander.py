from adcm.domain.models import AllowedPath, Preference, ValueCandidate, ValueOrigin


class PreferenceExpander:
    """Maps cross-cutting user preferences to any currently legal path declaring the concept."""

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
                if preference.concept in allowed.concepts:
                    result.append(
                        ValueCandidate(
                            path=allowed.path,
                            value=preference.value,
                            origin=ValueOrigin.USER_PREFERENCE,
                            evidence_ids=preference.evidence_ids,
                            reason=f"expanded preference:{preference.concept}",
                        )
                    )
        return result
