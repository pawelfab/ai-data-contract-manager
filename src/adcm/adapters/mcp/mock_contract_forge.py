"""Executable reference adapter that imitates staged Contract Forge behavior.

It deliberately exposes only one stage at a time and demonstrates:
- unknown source systems still work;
- defaults are lower priority than enrichment/user values;
- pre-path signals are bound only when a path becomes legal;
- CSV exposes delimiter/encoding and enables preparator through enrichment.
"""
from typing import Any

from adcm.domain.models import (
    AllowedPath,
    ExternalCandidate,
    Requirement,
    RequirementBundle,
    ValueOrigin,
)


class MockContractForgeAdapter:
    async def next_requirements(self, known_values: dict[str, Any]) -> RequirementBundle:
        if "source.system" not in known_values:
            return RequirementBundle(
                stage_id="source_system",
                allowed_paths=[
                    AllowedPath(path="source.system", concepts=["source_system"]),
                ],
                requirements=[Requirement(path="source.system", prompt_hint="What source system?")],
            )

        if "metadata.id" not in known_values:
            return RequirementBundle(
                stage_id="metadata",
                allowed_paths=[
                    AllowedPath(path="metadata.id", concepts=["feed_name", "metadata_id"]),
                ],
                requirements=[Requirement(path="metadata.id", prompt_hint="What feed id/name?")],
            )

        if "source.format" not in known_values:
            return RequirementBundle(
                stage_id="source_format",
                allowed_paths=[
                    AllowedPath(path="source.format", concepts=["source_format"]),
                ],
                requirements=[Requirement(path="source.format")],
                candidates=[
                    ExternalCandidate(
                        path="source.format",
                        value="parquet",
                        origin=ValueOrigin.MCP_DEFAULT,
                        reason="contract default source format",
                    )
                ],
            )

        source_format = str(known_values["source.format"]).lower()
        if source_format in {"csv", "fixed-width", "fixed_width"}:
            required_paths = ["source.delimited.delimiter"] if source_format == "csv" else []
            missing_delimiter = any(p not in known_values for p in required_paths)
            if missing_delimiter or "source.delimited.encoding" not in known_values:
                return RequirementBundle(
                    stage_id="source_details",
                    allowed_paths=[
                        AllowedPath(
                            path="source.delimited.delimiter",
                            concepts=["field_delimiter", "delimiter"],
                        ),
                        AllowedPath(
                            path="source.delimited.encoding",
                            concepts=["encoding"],
                        ),
                    ],
                    requirements=[Requirement(path=p) for p in required_paths],
                    candidates=[
                        ExternalCandidate(
                            path="source.delimited.encoding",
                            value="UTF-8",
                            origin=ValueOrigin.MCP_DEFAULT,
                            reason="default text encoding",
                        )
                    ],
                )

            if "preparator.enabled" not in known_values:
                return RequirementBundle(
                    stage_id="preparator",
                    allowed_paths=[
                        AllowedPath(path="preparator.enabled", concepts=["preparator_enabled"]),
                        AllowedPath(
                            path="preparator.encryption.enabled",
                            concepts=["encryption"],
                        ),
                    ],
                    candidates=[
                        ExternalCandidate(
                            path="preparator.enabled",
                            value=True,
                            origin=ValueOrigin.MCP_ENRICHMENT,
                            reason="non-Parquet files require preparator conversion",
                        ),
                        ExternalCandidate(
                            path="preparator.encryption.enabled",
                            value=True,
                            origin=ValueOrigin.MCP_DEFAULT,
                            reason="contract default for preparator encryption",
                        ),
                    ],
                )

        return RequirementBundle(
            stage_id="complete",
            allowed_paths=[],
            complete=True,
        )

    async def validate_partial(self, draft: dict[str, Any]) -> list[str]:
        return []

    async def validate_final(self, draft: dict[str, Any]) -> list[str]:
        missing = [p for p in ["source.system", "metadata.id", "source.format"] if p not in draft]
        return [f"missing:{path}" for path in missing]
