from adcm.domain.external import ExternalChecksStatus


class ExternalCheckCoordinator:
    """Extension point for optional Context MCPs. Baseline intentionally has no providers."""

    async def run(self, *, document: dict) -> ExternalChecksStatus:
        return ExternalChecksStatus()
