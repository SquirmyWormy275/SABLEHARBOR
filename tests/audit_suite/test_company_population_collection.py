"""Actual company bytes and the ordinary provisional population contract."""

from types import SimpleNamespace

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.company_population_collection import collect
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.populations import create_population
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_population import ROOT, prepare


@pytest.fixture
def setup(tmp_path):
    company = tmp_path / "company"
    company.mkdir()
    store = prepare(company)
    store.grant("READER", "AUDIT", "COMPANY", "base-branch", "commercial_changes")
    engine = SimpleNamespace(
        company_store=store,
        repository=ROOT,
        company_bindings={"AUDIT": {"company": "COMPANY", "branch": "base-branch"}},
        artifacts=Artifacts(tmp_path / "artifacts"),
    )
    state = {
        "id": "AUDIT",
        "simulated_at": "2027-03-01T00:00:00Z",
        "scope": {
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
            "boundaries": ["corporate"],
        },
        "requests": [{"id": "R1", "status": "ISSUED", "boundary_id": "corporate"}],
        "artifacts": [],
    }
    payload = {
        "request_id": "R1",
        "query": {
            "table": "commercial_changes",
            "source_scenario": "base",
            "month_start": 1,
            "month_end": 2,
            "units": ["foundry-field"],
        },
    }
    return engine, state, payload


def run(setup):
    return collect(*setup, {"actor": "READER", "recorded_at": "2027-03-01T00:00:00Z"}, "CMD")


def test_originals_manifest_and_explicit_provisional_import(setup):
    engine, state, _ = setup
    result = run(setup)
    assert result["source_versions"] == 2
    assert result["distinct_source_records"] == 1
    assert len(state["artifacts"]) == 4
    assert result["independent_review"] == "NOT_PERFORMED"
    for item in result["native_artifacts"]:
        a = next(a for a in state["artifacts"] if a["id"] == item["artifact_id"])
        assert a["sha256"] == item["source"]["sha256"]
        assert engine.artifacts.read(a)
    p = result["next_command"]["payload"]
    artifact = next(a for a in state["artifacts"] if a["id"] == p["artifact_id"])
    obj = create_population(
        "P1",
        1,
        p["rows"],
        scope=p["scope"],
        source={**p["source"], "original_sha256": artifact["sha256"]},
    )
    assert obj.status == "PROVISIONAL" and len(obj.ids) == 2
    state["populations"] = []
    state["phase"] = "ACTIVE"
    Engine._population_command(
        Engine.__new__(Engine),
        state,
        "population.import",
        p,
        {"actor": "READER", "recorded_at": state["simulated_at"]},
    )
    assert state["populations"][0]["count"] == 2
    assert state["populations"][0]["status"] == "PROVISIONAL"
    assert run(setup) == result
    assert len(state["artifacts"]) == 4


@pytest.mark.parametrize("mutation", ["clock", "period", "draft", "grant", "boundary"])
def test_rejects_scope_auth_and_unissued_requests_before_retention(setup, mutation):
    engine, state, payload = setup
    if mutation == "clock":
        payload["query"]["as_of"] = "2030-01-01T00:00:00Z"
    elif mutation == "period":
        state["scope"]["period_start"] = "2027-01-02"
    elif mutation == "draft":
        state["requests"][0]["status"] = "DRAFT"
    elif mutation == "boundary":
        state["requests"][0]["boundary_id"] = "unknown"
    else:
        engine.company_store.grant(
            "READER", "AUDIT", "COMPANY", "base-branch", "commercial_changes", active=False
        )
    with pytest.raises(DomainError):
        run(setup)
    assert not state["artifacts"]
