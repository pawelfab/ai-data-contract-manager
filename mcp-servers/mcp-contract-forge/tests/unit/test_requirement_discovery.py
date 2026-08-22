from contract_forge.application.services.requirement_discovery import RequirementDiscovery
from contract_forge.domain.contract.models import ContractSemanticPaths
from contract_forge.domain.discovery.models import DiscoveryPolicy
from contract_forge.domain.evaluation.models import Requirement

SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": {
            "type": "object",
            "properties": {
                "sourceSystemGcpId": {"type": "string"},
                "id": {"type": "string"},
                "version": {"type": "string"},
            },
        },
        "orchestration": {"type": "object", "properties": {"schedule": {"type": "string"}}},
    },
}
PATHS = ContractSemanticPaths(source_system="/metadata/sourceSystemGcpId")
REQ = [Requirement(path="/metadata/sourceSystemGcpId"), Requirement(path="/metadata/id"), Requirement(path="/metadata/version"), Requirement(path="/orchestration/schedule")]


def policy():
    return DiscoveryPolicy.model_validate({"steps": [
        {"id": "source", "whenMissing": ["@sourceSystem"], "expose": ["@sourceSystem"]},
        {"id": "metadata", "whenPresent": ["@sourceSystem"], "whenAnyMissing": ["/metadata/id", "/metadata/version"], "expose": ["/metadata/id", "/metadata/version"]},
        {"id": "rest", "whenPresent": ["@sourceSystem", "/metadata/id", "/metadata/version"], "exposeMatchingSchemaRequirements": True},
    ]})


def test_progressive_three_step_policy():
    d = RequirementDiscovery(policy(), PATHS, SCHEMA, strict=True)
    assert [r.path for r in d.discover(document={}, requirements=REQ).requirements] == ["/metadata/sourceSystemGcpId"]
    p2 = {r.path for r in d.discover(document={"metadata": {"sourceSystemGcpId": "sap"}}, requirements=REQ).requirements}
    assert p2 == {"/metadata/id", "/metadata/version"}
    p3 = {r.path for r in d.discover(document={"metadata": {"sourceSystemGcpId": "sap", "id": "sap", "version": "1"}}, requirements=REQ).requirements}
    assert p3 == {r.path for r in REQ}


def test_unknown_semantic_token_is_configuration_error_in_strict_mode():
    bad = DiscoveryPolicy.model_validate({"steps": [{"id": "bad", "whenMissing": ["@sourceSytem"], "expose": ["@sourceSytem"]}]})
    try:
        RequirementDiscovery(bad, PATHS, SCHEMA, strict=True).discover(document={}, requirements=REQ)
    except ValueError as exc:
        assert "sourceSytem" in str(exc)
    else:
        raise AssertionError("strict discovery should fail")
