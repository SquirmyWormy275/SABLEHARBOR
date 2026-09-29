import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_activity import TransferRecipe, generate_pair
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return TransferRecipe(
        "SH",
        "activity-clean",
        "activity-messy",
        "MOVE-01",
        "P014",
        "2027-04-15T09:00:00-07:00",
        "Scenario support",
        "Scenario coordinator",
        "support-read",
        "coordination-read",
        "room-a",
        "room-b",
    )


def test_paired_cause_precedes_audit_and_preserves_initial_sources(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    result = generate_pair(store, repository=ROOT, recipe=recipe())
    assert generate_pair(store, repository=ROOT, recipe=recipe()) == result
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
    assert len(rows) == 20
    clean = {(r["system"], r["version"]): r for r in rows if r["branch"] == "activity-clean"}
    messy = {(r["system"], r["version"]): r for r in rows if r["branch"] == "activity-messy"}
    for key in clean:
        if key not in [("application", 2), ("access_review", 1)]:
            assert clean[key]["sha256"] == messy[key]["sha256"]
    assert json.loads(clean["application", 2]["content"])["rights"] == ["coordination-read"]
    assert json.loads(messy["application", 2]["content"])["rights"] == [
        "support-read",
        "coordination-read",
    ]
    for branch in [clean, messy]:
        for row in branch.values():
            content = json.loads(row["content"])
            assert content["cause_id"] == "MOVE-01" and content["person_id"] == "P014"
            assert "expected_answer" not in content
        assert (
            branch["hr", 2]["event_at"]
            < branch["hr", 3]["event_at"]
            < branch["directory", 2]["event_at"]
        )
        assert branch["application", 2]["event_at"] < branch["access_review", 1]["event_at"]
    assert json.loads(messy["access_review", 1]["content"])["unapproved_remaining_rights"] == [
        "support-read"
    ]


@pytest.mark.parametrize(
    "change",
    [
        {"clean_branch": "activity-messy"},
        {"employee_id": "UNKNOWN"},
        {"effective_at": "2027-04-15"},
        {"old_right": "coordination-read"},
    ],
)
def test_invalid_inputs_create_no_sources(tmp_path, change):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    with pytest.raises((CompanyStoreError, ValueError)):
        generate_pair(store, repository=ROOT, recipe=replace(recipe(), **change))
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0
