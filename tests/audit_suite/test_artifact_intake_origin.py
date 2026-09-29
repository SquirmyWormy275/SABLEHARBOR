"""Intake classification follows a trusted adapter, not uploaded source claims."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_source_census_collection import envelope
from tests.audit_suite.test_company_source_census_collection import workspace as census_workspace


def test_generic_source_claim_does_not_promote_uploaded_intake(tmp_path):
    artifacts = Artifacts(tmp_path)
    source = {"kind": "COLLECTED_COMPANY_SOURCE", "origin": "AUTHORED_TRAINING_SOURCE"}
    legacy = artifacts.retain("E", "record.json", b"{}", source=source, coverage={})
    original = deepcopy(legacy)
    assert legacy["origin"] == "LEARNER_SUBMITTED"
    collected = artifacts.retain_company("E", "record.json", b"{}", source=source, coverage={})
    assert collected["origin"] == "COLLECTED_COMPANY_SOURCE"
    assert collected["source"]["origin"] == "AUTHORED_TRAINING_SOURCE"
    assert collected["sha256"] == legacy["sha256"]
    assert artifacts.read(legacy) == b"{}"
    assert legacy == original  # Old metadata is never silently reclassified.


@pytest.mark.parametrize(
    "kind",
    [
        "COMPANY_CENSUS_QUERY",
        "COMPANY_CENSUS_DERIVATION",
        "COMPANY_POPULATION_QUERY",
        "COMPANY_POPULATION_DERIVATION",
    ],
)
def test_company_query_derivations_are_not_native_originals(tmp_path, kind):
    artifact = Artifacts(tmp_path).retain_company(
        "E", "query.json", b"{}", source={"kind": kind}, coverage={}
    )
    assert artifact["origin"] == "COMPANY_SOURCE_DERIVED"
    assert artifact["source"]["kind"] == kind


def test_trusted_company_path_rejects_upload_before_retention(tmp_path):
    artifacts = Artifacts(tmp_path)
    with pytest.raises(DomainError, match="intake kind"):
        artifacts.retain_company(
            "E", "upload.json", b"{}", source={"kind": "LEARNER_UPLOAD"}, coverage={}
        )
    assert list(artifacts.root.iterdir()) == []
    generated = artifacts.retain(
        "E", "generated.json", b"{}", source={"kind": "CLEAN_BASELINE"}, coverage={}, generated=True
    )
    assert generated["origin"] == "SYNTHETIC"


def test_actual_census_classifies_originals_and_derivations_without_testing_credit(tmp_path):
    engine, actor, state = census_workspace.__wrapped__(tmp_path)
    command = envelope(state)
    result = engine.command(actor, state["id"], command)
    natives = [a for a in result["artifacts"] if a["source"]["kind"] == "COLLECTED_COMPANY_SOURCE"]
    derived = [a for a in result["artifacts"] if a not in natives]
    assert len(natives) == len(derived) == 2
    assert {a["origin"] for a in natives} == {"COLLECTED_COMPANY_SOURCE"}
    assert {a["origin"] for a in derived} == {"COMPANY_SOURCE_DERIVED"}
    assert {a["source"]["receipt"]["source"]["origin"] for a in natives} == {
        "AUTHORED_TRAINING_SOURCE",
        "REPOSITORY_SYNTHETIC_DOCUMENT",
    }
    assert result["populations"] == result["workpapers"] == result["tasks"] == []
    assert engine.command(actor, state["id"], command) == result
