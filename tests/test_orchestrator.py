from pathlib import Path

import pytest

from adcm.gateway import LocalForgeGateway
from adcm.orchestrator import ADCMOrchestrator
from contract_forge.engine import ContractForge

ROOT = Path(__file__).resolve().parents[1]


def build_service():
    forge = ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )
    return ADCMOrchestrator(LocalForgeGateway(forge))


@pytest.mark.asyncio
async def test_guided_loop_minimal():
    service = build_service()
    turn = await service.start()
    assert turn.pending_path == "metadata.sourceSystemGcpId"

    turn = await service.message(turn.session_id, "roket")
    assert turn.pending_path == "metadata.id"

    turn = await service.message(turn.session_id, "customer_accounts_daily")
    assert turn.pending_path == "metadata.owner"

    turn = await service.message(turn.session_id, "data-platform@example.com")
    assert turn.pending_path == "source.uri"

    turn = await service.message(turn.session_id, "gs://raw-zone/accounts/accounts.dat")
    assert turn.pending_path == "source.columns"

    turn = await service.message(
        turn.session_id,
        "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
    )
    assert turn.status == "complete"
    assert turn.contract["metadata"]["sourceSystemGcpId"] == "ROCKET"

class FakeSemanticResolver:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    async def extract_from_history(self, session_id, messages, requirements, contract):
        self.calls.append([r.path for r in requirements])
        return {
            r.path: self.answers[r.path]
            for r in requirements
            if r.path in self.answers
        }


@pytest.mark.asyncio
async def test_stair_step_loop_reuses_information_as_forge_reveals_requirements():
    forge = ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )
    semantic = FakeSemanticResolver({
        "metadata.id": "customer_accounts_daily",
        "metadata.owner": "data-platform@example.com",
        "source.uri": "gs://raw-zone/accounts/accounts.dat",
        "source.columns": [
            {"name": "account_id", "start": 0, "end": 8, "dataType": "STRING", "nullable": False},
            {"name": "balance", "start": 8, "end": 20, "dataType": "NUMERIC"},
        ],
    })
    service = ADCMOrchestrator(LocalForgeGateway(forge), semantic=semantic)
    turn = await service.start()

    # The user states everything up-front. Forge initially accepts only source-system;
    # the semantic resolver is re-run as each next requirement is revealed.
    turn = await service.message(
        turn.session_id,
        "Rocket. Chcę utworzyć customer accounts daily, owner data-platform, "
        "plik mam w raw zone i wkleiłem też definicję kolumn.",
    )

    assert turn.status == "complete"
    assert semantic.calls  # semantic loop really participated
    assert turn.contract["metadata"]["id"] == "customer_accounts_daily"
    assert turn.contract["source"]["uri"].startswith("gs://")
