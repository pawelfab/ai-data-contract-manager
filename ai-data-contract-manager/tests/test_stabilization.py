from pathlib import Path

import pytest

from adcm.adapters.rules_file import FileRulesRepository
from adcm.application.document_engine import DocumentEngine
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.domain.contract import ContractState
from adcm.domain.forge import ContractStatus, ForgeAnalysis, ForgeDescription
from adcm.domain.mutations import MutationCommand, MutationOperation
from adcm.domain.provenance import ValueSource


RULES = Path(__file__).parents[1] / "resources" / "ux_rules.json"


class FakeForge:
    async def describe(self) -> ForgeDescription:
        return ForgeDescription(protocol_version="1.0", definition_version="fake")

    async def analyze(self, document: dict) -> ForgeAnalysis:
        missing = []
        return ForgeAnalysis(
            protocol_version="1.0",
            definition_version="fake",
            status=ContractStatus(valid=True, complete=not missing, clean=True),
        )


@pytest.mark.asyncio
async def test_sap_rules_reach_fixed_point_and_user_override_survives() -> None:
    state = ContractState()
    document_engine = DocumentEngine()
    document_engine.apply(
        state,
        [
            MutationCommand(
                operation=MutationOperation.ADD,
                path="/metadata/sourceSystemGcpId",
                value="sap",
                source=ValueSource.USER_EXPLICIT,
            )
        ],
    )
    rules = await FileRulesRepository(str(RULES)).load("s")
    stabilizer = StabilizationEngine(
        FakeForge(),
        document_engine,
        ConventionRulesEngine(),
        ProposalReconciler(),
        max_rounds=8,
    )
    _, report = await stabilizer.stabilize(state, rules)

    assert report.converged is True
    assert state.document["metadata"]["id"] == "sap"
    assert state.document["source"]["sourceType"] == "csv"
    assert state.document["source"]["systemZrodlowy"] == "sap"
    assert state.document["converter"]["outputFilename"] == "sap_{{data_danych}}.csv"

    document_engine.apply(
        state,
        [
            MutationCommand(
                operation=MutationOperation.REPLACE,
                path="/converter/outputFilename",
                value="custom.txt",
                source=ValueSource.USER_EXPLICIT,
            )
        ],
    )
    _, report = await stabilizer.stabilize(state, rules)
    assert report.converged is True
    assert state.document["converter"]["outputFilename"] == "custom.txt"

@pytest.mark.asyncio
async def test_changing_system_retracts_old_derived_values() -> None:
    state = ContractState()
    document_engine = DocumentEngine()
    rules = await FileRulesRepository(str(RULES)).load("s")
    stabilizer = StabilizationEngine(
        FakeForge(),
        document_engine,
        ConventionRulesEngine(),
        ProposalReconciler(),
        max_rounds=8,
    )
    document_engine.apply(
        state,
        [MutationCommand(operation=MutationOperation.ADD, path="/metadata/sourceSystemGcpId", value="sap", source=ValueSource.USER_EXPLICIT)],
    )
    await stabilizer.stabilize(state, rules)
    assert state.document["converter"]["outputFilename"].endswith(".csv")

    document_engine.apply(
        state,
        [MutationCommand(operation=MutationOperation.REPLACE, path="/metadata/sourceSystemGcpId", value="rocket", source=ValueSource.USER_EXPLICIT)],
    )
    _, report = await stabilizer.stabilize(state, rules)
    assert report.converged is True
    assert state.document["metadata"]["id"] == "rocket"
    assert "source" not in state.document
    assert "converter" not in state.document
