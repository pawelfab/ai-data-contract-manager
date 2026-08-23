"""Live Contract Forge MCP checks — real transport, no LLM.

This is the isolation layer for the conversation test: it replays the same document sequence
straight through `ForgeMcpAdapter`, so a red result here means the fault is in Forge or the MCP
hop, not in the model. It is fully deterministic and costs nothing.
"""

from __future__ import annotations

import pytest

from adcm.adapters.outbound.forge_mcp.client import ForgeMcpAdapter

SAP_METADATA = {
    "id": "sap",
    "sourceSystemGcpId": "sap",
    "version": "1.0.1",
    "dataFileId": "sap_pipeline",
}
SAP_ORCHESTRATION = {"schedule": "@daily", "startDate": "2025-01-01"}

# (document, expected requirement paths, suggestion pairs that must be present)
STAGES = [
    (
        {},
        {"/metadata/sourceSystemGcpId"},
        set(),
    ),
    (
        {"metadata": {"sourceSystemGcpId": "sap"}},
        {"/metadata/id", "/metadata/version", "/metadata/dataFileId"},
        {("/metadata/id", "sap")},
    ),
    (
        {"metadata": SAP_METADATA},
        {"/orchestration/schedule", "/orchestration/startDate"},
        {("/metadata/id", "sap")},
    ),
    (
        {"metadata": SAP_METADATA, "orchestration": SAP_ORCHESTRATION},
        {"/source/sourceType"},
        {("/metadata/id", "sap")},
    ),
    (
        {
            "metadata": SAP_METADATA,
            "orchestration": SAP_ORCHESTRATION,
            "source": {"systemZrodlowy": "sap", "sourceType": "txt"},
        },
        {"/source/dataDanych", "/source/encoding"},
        {
            ("/metadata/id", "sap"),
            ("/source/systemZrodlowy", "sap"),
            ("/converter/enabled", True),
            ("/preparator/enabled", True),
        },
    ),
]


@pytest.fixture
def forge(live_settings) -> ForgeMcpAdapter:
    return ForgeMcpAdapter(live_settings.forge_mcp_url)


@pytest.mark.parametrize(
    "document, expected_requirements, expected_suggestions",
    STAGES,
    ids=["empty", "source-system", "metadata", "orchestration", "source-type-txt"],
)
async def test_requirement_sequence_is_deterministic(
    forge: ForgeMcpAdapter,
    document: dict,
    expected_requirements: set[str],
    expected_suggestions: set[tuple],
):
    evaluation = await forge.evaluate(document)

    assert {r.path for r in evaluation.requirements} == expected_requirements
    assert expected_suggestions <= {(s.path, s.value) for s in evaluation.suggestions}
    assert evaluation.valid is False


async def test_complete_source_scaffolds_bronze(forge: ForgeMcpAdapter):
    """A complete source branch is what unlocks the bronze layer — the phase separation that
    `docs/active-tasks/2026-08-23-source-bronze-silver-gold-flow` exists to guarantee."""

    evaluation = await forge.evaluate(
        {
            "metadata": SAP_METADATA,
            "orchestration": SAP_ORCHESTRATION,
            "source": {
                "systemZrodlowy": "sap",
                "sourceType": "txt",
                "dataDanych": "{date}",
                "encoding": "utf-8",
            },
        }
    )

    suggestions = {s.path: s.value for s in evaluation.suggestions}
    assert suggestions.get("/bronzeTable") == {}
    assert not evaluation.requirements


async def test_source_system_drives_layer_names(forge: ForgeMcpAdapter):
    """Layer identifiers are a global convention, not a per-system rule (DECISIONS D-23)."""

    evaluation = await forge.evaluate(
        {
            "metadata": {
                "id": "rocket",
                "sourceSystemGcpId": "rocket",
                "version": "1.0.0",
                "dataFileId": "rocket_pipeline",
            },
            "orchestration": SAP_ORCHESTRATION,
            "source": {
                "systemZrodlowy": "rocket",
                "sourceType": "json",
                "dataDanych": "{date}",
            },
            "bronzeTable": {},
        }
    )

    suggestions = {s.path: s.value for s in evaluation.suggestions}
    assert suggestions["/bronzeTable/table/project"] == "rocket_bronze"
    assert suggestions["/bronzeTable/columns"] == []
    # Rocket is not a configured system, so no converter/preparator activation.
    assert "/converter/enabled" not in suggestions
