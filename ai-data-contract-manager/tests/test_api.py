from fastapi.testclient import TestClient

from adcm.api import create_app
from adcm.orchestrator import ADCMOrchestrator
from support import FakeForgeGateway


def test_api_session_starts_with_source_system_question():
    app = create_app(ADCMOrchestrator(FakeForgeGateway()))
    with TestClient(app) as client:
        health = client.get('/health')
        assert health.status_code == 200
        assert health.json() == {'status': 'ok'}

        started = client.post('/sessions')
        assert started.status_code == 200
        body = started.json()
        assert body['status'] == 'needs_input'
        assert body['pending_path'] == 'metadata.sourceSystemGcpId'
        assert body['pending_requirement']['value_schema']['enum'] == ['rocket', 'sap']

        answered = client.post(
            f"/sessions/{body['session_id']}/messages",
            json={'message': 'roket'},
        )
        assert answered.status_code == 200
        next_body = answered.json()
        assert next_body['pending_path'] == 'metadata.id'
        assert next_body['contract']['metadata']['sourceSystemGcpId'] == 'ROCKET'
        assert next_body['contract']['source']['sourceType'] == 'fixed_width'
