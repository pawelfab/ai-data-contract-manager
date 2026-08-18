"""Stateless reference Contract Forge adapter for tests and demo only."""

from __future__ import annotations

from typing import Any

import yaml

from adcm.domain.contract_path import ContractPath
from adcm.domain.models import (
    AllowedPath,
    CandidateScope,
    ContractEvaluationResult,
    ContractInput,
    CurrentSchemaView,
    EvaluationStatus,
    ExternalCandidate,
    FinalValidationResult,
    FinalValidationStatus,
    RenderedContract,
    RenderRequest,
    Requirement,
    ValueOrigin,
)


class MockContractForgeAdapter:
    schema_revision = "mock-schema-v2"

    @staticmethod
    def _value(draft: dict[str, Any], path: str) -> Any:
        return ContractPath.read(draft, path)

    def _check_revision(self, expected: str | None) -> None:
        if expected is not None and expected != self.schema_revision:
            raise RuntimeError(
                f"SCHEMA_CHANGED expected={expected!r} current={self.schema_revision!r}"
            )

    @staticmethod
    def _base_paths() -> list[AllowedPath]:
        return [AllowedPath(path="source.system", concepts=["source_system"])]

    async def evaluate_draft(self, request: ContractInput) -> ContractEvaluationResult:
        self._check_revision(request.expected_schema_revision)
        draft = request.draft

        paths = self._base_paths()
        if self._value(draft, "source.system") is None:
            return ContractEvaluationResult(
                status=EvaluationStatus.INCOMPLETE,
                schema_view=CurrentSchemaView(
                    schema_revision=self.schema_revision,
                    stage_id="source_system",
                    allowed_paths=paths,
                ),
                requirements=[Requirement(path="source.system", prompt_hint="What source system?")],
            )

        paths.append(AllowedPath(path="source.format", concepts=["source_format"]))
        if self._value(draft, "source.format") is None:
            return ContractEvaluationResult(
                status=EvaluationStatus.INCOMPLETE,
                schema_view=CurrentSchemaView(
                    schema_revision=self.schema_revision,
                    stage_id="source_format",
                    allowed_paths=paths,
                ),
                requirements=[Requirement(path="source.format")],
                candidates=[
                    ExternalCandidate(
                        path="source.format",
                        value="parquet",
                        origin=ValueOrigin.MCP_DEFAULT,
                        scope=CandidateScope.DEFAULT,
                        priority=10,
                        rule_id="default.source_format",
                        reason="contract default source format",
                    )
                ],
            )

        source_format = str(self._value(draft, "source.format")).lower()
        if source_format == "csv":
            paths.extend(
                [
                    AllowedPath(
                        path="source.delimited.delimiter",
                        concepts=["field_delimiter", "delimiter"],
                    ),
                    AllowedPath(path="source.delimited.encoding", concepts=["encoding"]),
                ]
            )
            if self._value(draft, "source.delimited.delimiter") is None:
                return ContractEvaluationResult(
                    status=EvaluationStatus.INCOMPLETE,
                    schema_view=CurrentSchemaView(
                        schema_revision=self.schema_revision,
                        stage_id="source_details",
                        allowed_paths=paths,
                    ),
                    requirements=[Requirement(path="source.delimited.delimiter")],
                    candidates=[
                        ExternalCandidate(
                            path="source.delimited.encoding",
                            value="UTF-8",
                            origin=ValueOrigin.MCP_DEFAULT,
                            scope=CandidateScope.DEFAULT,
                            priority=10,
                            rule_id="default.encoding",
                            reason="default text encoding",
                        )
                    ],
                )

            paths.extend(
                [
                    AllowedPath(path="preparator.enabled", concepts=["preparator_enabled"]),
                    AllowedPath(
                        path="preparator.encryption.enabled",
                        concepts=["encryption"],
                    ),
                ]
            )
            if self._value(draft, "preparator.enabled") is None:
                return ContractEvaluationResult(
                    status=EvaluationStatus.INCOMPLETE,
                    schema_view=CurrentSchemaView(
                        schema_revision=self.schema_revision,
                        stage_id="preparator",
                        allowed_paths=paths,
                    ),
                    candidates=[
                        ExternalCandidate(
                            path="preparator.enabled",
                            value=True,
                            origin=ValueOrigin.MCP_ENRICHMENT,
                            scope=CandidateScope.SOURCE_TYPE,
                            priority=60,
                            rule_id="csv.preparator.enabled",
                            reason="CSV requires preparator conversion",
                        ),
                        ExternalCandidate(
                            path="preparator.encryption.enabled",
                            value=True,
                            origin=ValueOrigin.MCP_DEFAULT,
                            scope=CandidateScope.DEFAULT,
                            priority=10,
                            rule_id="default.preparator.encryption",
                            reason="contract default for preparator encryption",
                        ),
                    ],
                )

        paths.append(AllowedPath(path="metadata.id", concepts=["feed_name", "metadata_id"]))
        if self._value(draft, "metadata.id") is None:
            return ContractEvaluationResult(
                status=EvaluationStatus.INCOMPLETE,
                schema_view=CurrentSchemaView(
                    schema_revision=self.schema_revision,
                    stage_id="metadata",
                    allowed_paths=paths,
                ),
                requirements=[Requirement(path="metadata.id", prompt_hint="What feed id/name?")],
            )

        return ContractEvaluationResult(
            status=EvaluationStatus.COMPLETE,
            schema_view=CurrentSchemaView(
                schema_revision=self.schema_revision,
                stage_id="complete",
                allowed_paths=paths,
            ),
        )

    async def validate_final(self, request: ContractInput) -> FinalValidationResult:
        self._check_revision(request.expected_schema_revision)
        missing = [
            path
            for path in ["source.system", "source.format", "metadata.id"]
            if self._value(request.draft, path) is None
        ]
        return FinalValidationResult(
            status=FinalValidationStatus.INVALID if missing else FinalValidationStatus.VALID,
            schema_revision=self.schema_revision,
        )

    async def render_yaml(self, request: RenderRequest) -> RenderedContract:
        self._check_revision(request.expected_schema_revision)
        return RenderedContract(
            content=yaml.safe_dump(request.draft, sort_keys=False, allow_unicode=True),
            mode=request.mode,
            schema_revision=self.schema_revision,
        )
