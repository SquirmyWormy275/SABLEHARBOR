import csv
import io
from dataclasses import asdict

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.population_lifecycle import handle, population
from enterprise.audit_suite.populations import create_population, select
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def context(tmp_path):
    artifacts = Artifacts(tmp_path / "private")
    scope = {
        "boundary_id": "corporate",
        "unit": "ticket",
        "timezone": "UTC",
        "period_start": "2027-01-01T00:00:00Z",
        "period_end": "2027-12-31T00:00:00Z",
    }
    artifact = artifacts.retain(
        "ENG-test",
        "source.csv",
        b"id,amount\na,10\nb,20\n",
        source={"kind": "UPLOADED"},
        coverage=scope,
        generated=False,
    )
    obj = create_population(
        "POP-a",
        1,
        [{"id": "a", "amount": 10}, {"id": "b", "amount": 20}],
        scope=scope,
        source={
            "source_id": "source-export",
            "query": "all supplied rows",
            "original_sha256": artifact["sha256"],
            "completeness_representation": "Owner claims complete",
        },
    )
    chosen = select(
        obj,
        selection_id="SEL-a",
        method="MANUAL",
        purpose="Access review",
        rationale="One targeted inspection",
        ids=["a"],
    )
    state = {
        "id": "ENG-test",
        "simulated_at": "2028-01-01T00:00:00Z",
        "populations": [
            {
                "id": obj.id,
                "title": "Tickets",
                "version": 1,
                "immutable": asdict(obj),
                "artifact_id": artifact["id"],
            }
        ],
        "selections": [{"id": chosen.id, "immutable": asdict(chosen)}],
        "artifacts": [artifact],
    }
    return state, artifacts, {"actor": "learner", "recorded_at": "2026-09-13T00:00:00Z"}


def test_reliability_is_new_version_and_does_not_rewrite_prior_sample(context):
    state, artifacts, stamp = context
    original = population(state["populations"][0])
    handle(
        state,
        "population.assess",
        {
            "population_id": original.id,
            "status": "READY_FOR_PURPOSE",
            "purpose": "Access review",
            "rationale": "Reconciled retained source rows and extraction settings",
            "observable_artifact_ids": [state["artifacts"][0]["id"]],
        },
        stamp,
        artifacts,
    )
    revised = population(state["populations"][1])
    assert revised.id != original.id and revised.version == 2
    assert revised.predecessor_digest == original.sha256
    assert state["populations"][1]["family_id"] == original.id
    assert population(state["populations"][0]).status == "PROVISIONAL"
    assert state["selections"][0]["immutable"]["population_status"] == "PROVISIONAL"


def test_unavailable_source_and_invented_delivery_rejected(context):
    state, artifacts, stamp = context
    with pytest.raises(DomainError, match="unavailable"):
        handle(
            state,
            "population.assess",
            {
                "population_id": "POP-a",
                "status": "READY_FOR_PURPOSE",
                "purpose": "Access review",
                "rationale": "Claim",
                "observable_artifact_ids": ["hidden-file"],
            },
            stamp,
            artifacts,
        )
    with pytest.raises(DomainError, match="unavailable"):
        handle(
            state,
            "selection.dispositions",
            {
                "selection_id": "SEL-a",
                "dispositions": {
                    "a": {"status": "DELIVERED", "rationale": "Claim", "artifact_ids": ["invented"]}
                },
            },
            stamp,
            artifacts,
        )


def test_export_uses_only_selected_observable_rows(context):
    state, artifacts, stamp = context
    handle(state, "selection.export", {"selection_id": "SEL-a"}, stamp, artifacts)
    data = artifacts.read(state["artifacts"][-1]).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(data)))
    assert rows == [{"id": "a", "amount": "10", "selection_basis": "SAMPLED"}]
