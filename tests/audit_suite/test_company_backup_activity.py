import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from enterprise.audit_suite.company_backup_activity import BackupRecipe, generate_backup_pair
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return BackupRecipe(
        "SH",
        "backup-clean",
        "backup-messy",
        "BACKUP-01",
        "SVC-compute",
        "2027-03-01T00:00:00Z",
        "2027-04-01T00:00:00Z",
        "2027-03-12T00:00:00Z",
    )


def generate(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    result = generate_backup_pair(store, repository=ROOT, recipe=recipe())
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
    return store, result, {(r["branch"], r["system"], r["version"]): r for r in rows}


def test_native_copies_reconcile_to_independent_source_and_preserve_failed_restore(tmp_path):
    store, result, rows = generate(tmp_path)
    assert generate_backup_pair(store, repository=ROOT, recipe=recipe()) == result
    assert result["audit_created"] is result["grants_created"] is False
    assert len(rows) == result["source_versions"]
    for branch in ("backup-clean", "backup-messy"):

        def data(system, version, branch=branch):
            return json.loads(rows[branch, system, version]["content"])

        initial = data("reconciliation", 1)
        retest = data("reconciliation", 2)
        source = data("source_dataset", 2)["records"]
        recovered = data("restored_dataset", 1)["records"]
        expected = {r["id"]: r for r in source}
        actual = {r["id"]: r for r in recovered}
        assert initial["missing_ids"] == sorted(expected.keys() - actual.keys())
        assert initial["changed_ids"] == sorted(
            k for k in actual.keys() & expected.keys() if expected[k] != actual[k]
        )
        assert initial["restore_sha256"] == sha(rows[branch, "restored_dataset", 1]["content"])
        assert initial["byte_copy_matches_selected_object"] is True
        assert retest["missing_ids"] == retest["changed_ids"] == retest["unexpected_ids"] == []
        assert (
            rows[branch, "restored_dataset", 2]["content"]
            == rows[branch, "source_dataset", 2]["content"]
        )
        assert data("review", 1)["reviewed_by"] != initial["performed_by"]
        assert data("review", 1)["whole_control_effectiveness"] == "NOT_ASSESSED"
        if branch == "backup-messy":
            assert initial["missing_ids"] == ["OBJ-03"]
            assert initial["changed_ids"] == ["OBJ-02"]
            assert data("credential_event", 2)["permission_state"] == "EXPIRED"
            assert data("backup_job", 2)["state"] == "FAILED"
            assert data("backup_job", 2)["copied_bytes"] == 0
            assert data("failure_ticket", 1)["state"] == "OPEN"
            assert initial["checkpoint_age_at_restore_start_minutes"] == 1480
            assert (
                rows[branch, "restored_dataset", 1]["content"]
                == rows[branch, "source_dataset", 1]["content"]
            )
        else:
            assert initial["missing_ids"] == initial["changed_ids"] == []
            assert initial["checkpoint_age_at_restore_start_minutes"] == 40
            assert data("backup_job", 2)["state"] == "COMPLETED"
    for system, version in [
        ("inventory", 1),
        ("schedule", 1),
        ("source_dataset", 1),
        ("source_dataset", 2),
        ("backup_object", 1),
    ]:
        assert (
            rows["backup-clean", system, version]["sha256"]
            == rows["backup-messy", system, version]["sha256"]
        )


def test_hash_lineage_chronology_qualifiers_and_current_authority(tmp_path):
    store, _, rows = generate(tmp_path)
    for row in rows.values():
        assert sha(row["content"]) == row["sha256"]
        provenance = json.loads(row["provenance"])
        assert provenance["classification"] == "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT"
        assert all(site["canonical_operating"] is False for site in provenance["sites"])
        assert all(
            site["canonical_status"] == "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            for site in provenance["sites"]
        )
        for ref in provenance["source_refs"]:
            parent = rows[row["branch"], ref["system"], ref["version"]]
            assert ref["record"] == parent["record"]
            assert ref["sha256"] == parent["sha256"]
            assert datetime.fromisoformat(parent["available_at"]) <= datetime.fromisoformat(
                row["event_at"]
            )
    row = rows["backup-messy", "restored_dataset", 2]
    store.grant("auditor", "engagement", "SH", "backup-messy", "restored_dataset")
    args = ("auditor", "engagement", "SH", "backup-messy", "restored_dataset", row["record"])
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=2, as_of=recipe().first_job_at)
    actual = store.read_version(*args, version=2, as_of="2027-04-01T00:00:00Z")
    assert actual["content"] == row["content"]
    store.grant("auditor", "engagement", "SH", "backup-messy", "restored_dataset", active=False)
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=2, as_of="2027-04-01T00:00:00Z")


@pytest.mark.parametrize(
    "changes",
    [
        {"messy_branch": "backup-clean"},
        {"service_id": "unknown"},
        {"first_job_at": "2027-03-01T00:00:00Z"},
        {"period_end_exclusive": "2027-03-13T00:00:00Z"},
    ],
)
def test_invalid_recipe_writes_no_operational_rows(tmp_path, changes):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    with pytest.raises(CompanyStoreError):
        generate_backup_pair(store, repository=ROOT, recipe=replace(recipe(), **changes))
    with store._db() as db:
        assert db.execute("SELECT count(*) FROM systems").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 0


def test_changed_recipe_cannot_rewrite_or_extend_existing_history(tmp_path):
    store, _, rows = generate(tmp_path)
    with pytest.raises(CompanyStoreError, match="exact-replay"):
        generate_backup_pair(
            store, repository=ROOT, recipe=replace(recipe(), first_job_at="2027-03-13T00:00:00Z")
        )
    with store._db() as db:
        assert {r["sha256"] for r in db.execute("SELECT * FROM versions")} == {
            r["sha256"] for r in rows.values()
        }
