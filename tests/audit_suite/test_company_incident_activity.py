"""Paired incident sources are causal, immutable and explicitly fictional."""

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from enterprise.audit_suite.company_incident_activity import IncidentRecipe, generate_incident
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return IncidentRecipe(
        "SH",
        "incident-clean",
        "incident-messy",
        "INC-01",
        "SVC-compute",
        "2027-03-01T00:00:00Z",
        "2027-04-01T00:00:00Z",
        "2027-03-12T09:00:00Z",
    )


def test_paired_incident_timing_native_links_and_nonoperating_qualifiers(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    result = generate_incident(store, repository=ROOT, recipe=recipe())
    assert result["source_versions"] == 36
    assert generate_incident(store, repository=ROOT, recipe=recipe()) == result
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 20
    sources = {(r["branch"], r["system"], r["version"]): r for r in rows}
    for row in rows:
        assert sha(row["content"]) == row["sha256"]
        content = json.loads(row["content"])
        assert content["service_id"] == "SVC-compute"
        assert all(s["canonical_operating"] is False for s in content["sites"])
        assert all(
            s["canonical_status"] == "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            for s in content["sites"]
        )
        assert "no PHI/ePHI processing asserted" in content["data_scope"]
        assert "expected_answer" not in content and "grade" not in content
        for ref in content["source_refs"]:
            parent = sources[row["branch"], ref["system"], ref["version"]]
            assert ref["record"] == parent["record"] and ref["sha256"] == parent["sha256"]
            assert datetime.fromisoformat(parent["available_at"]) <= datetime.fromisoformat(
                row["event_at"]
            )
    for key in [("inventory", 1), ("monitoring", 1), ("incident_ticket", 1)]:
        assert (
            sources["incident-clean", *key]["sha256"] == sources["incident-messy", *key]["sha256"]
        )

    def content(branch, system, version):
        return json.loads(sources[branch, system, version]["content"])

    clean = content("incident-clean", "recovery", 2)
    messy = content("incident-messy", "recovery", 2)
    assert messy["elapsed_minutes_from_discovery"] - clean["elapsed_minutes_from_discovery"] == 30
    assert content("incident-messy", "escalation", 1)["delivery_state"] == "QUEUED"
    assert content("incident-clean", "escalation", 1)["delivery_state"] == "DELIVERED"
    for branch in ["incident-clean", "incident-messy"]:
        monitor = content(branch, "monitoring", 2)
        age = (
            datetime.fromisoformat(monitor["checkpoint_observed_at"])
            - datetime.fromisoformat(monitor["checkpoint_captured_at"])
        ).total_seconds() / 60
        assert age == content(branch, "recovery", 2)["checkpoint_age_minutes"]
        replay = content(branch, "dispatch_replay", 1)
        validation = content(branch, "action_validation", 1)
        assert validation["validated_by"] != replay["actor"]
        assert any(r["system"] == "dispatch_replay" for r in validation["source_refs"])
        assert content(branch, "corrective_action", 3)["state"] == "CLOSED_WITH_REPLAY_RECORD"


def test_future_escalation_confirmation_is_not_visible_early(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    generate_incident(store, repository=ROOT, recipe=recipe())
    store.grant("READER", "INSPECTION", "SH", "incident-messy", "escalation")
    args = ("READER", "INSPECTION", "SH", "incident-messy", "escalation", "INC-01-escalation")
    current = store.read_version(*args, version=1, as_of="2027-03-12T09:10:00Z")
    assert json.loads(current["content"])["delivery_state"] == "QUEUED"
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=2, as_of="2027-03-12T09:10:00Z")


@pytest.mark.parametrize(
    "changes",
    [
        {"clean_branch": "incident-messy"},
        {"error_count": 0},
        {"service_id": "SVC-email"},
        {"discovered_at": "2027-03-31T09:00:00Z"},
        {"request_count": True},
        {"error_count": 10, "local_error_threshold_percent": 90},
    ],
)
def test_invalid_incident_recipe_creates_no_source_records(tmp_path, changes):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    with pytest.raises(CompanyStoreError):
        generate_incident(store, repository=ROOT, recipe=replace(recipe(), **changes))
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 0
