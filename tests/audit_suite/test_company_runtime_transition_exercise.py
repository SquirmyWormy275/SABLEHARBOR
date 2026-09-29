"""Fictional transition preserves the 2026 baseline and causal 2027 defects."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_runtime_transition_exercise import (
    COMPANY,
    DECISION_SHA256,
    EXCEPTION_ID,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "runtime-transition"
    create(root, repository=REPOSITORY, clean_branch="TRANS-CLEAN", messy_branch="TRANS-MESSY")
    return root


def test_exact_contract_commission_recovery_and_exception_history(tmp_path):
    root = _build(tmp_path)
    assert verify(root, repository=REPOSITORY)["native_version_count"] == 22
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert (
        receipt["source_pins"][
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        ]
        == DECISION_SHA256
    )
    assert receipt["local_denominators"] == {
        "selected_sites": 2,
        "provider_contracts": 2,
        "site_installations": 2,
        "final_commissioning_decisions": 2,
        "final_recovery_exercises": 1,
        "final_site_releases": 2,
    }
    for counts in receipt["observed_local_counts"].values():
        assert {key: counts[key] for key in receipt["local_denominators"]} == receipt[
            "local_denominators"
        ]
    assert receipt["observed_local_counts"]["MESSY"]["failed_commissioning_versions"] == 1
    assert receipt["observed_local_counts"]["MESSY"]["failed_recovery_attempts"] == 1
    assert receipt["observed_local_counts"]["MESSY"]["invalid_ready_markers"] == 1
    assert receipt["open_exception_ids"] == {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
    assert all(
        site["source_status_2026"] == "PROVIDER_SELECTED_PROCUREMENT_PENDING"
        and site["source_operating_2026"] is False
        and site["source_contract_executed_2026"] is False
        for site in receipt["site_baseline"].values()
    )
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        assert len(rows) == 22
        assert all(r["event_at"] > r["imported_at"] for r in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
        bodies = {(r["branch"], r["record"], r["version"]): json.loads(r["content"]) for r in rows}
        assert all(
            b["real_external_signature"] is False
            and b["real_world_provider_operation"] is False
            and b["actual_real_world_phi_processing"] is False
            and b["business_associate_role"] == "UNDETERMINED_SEPARATE_SCENARIO"
            for b in bodies.values()
        )
        clean = bodies[("TRANS-CLEAN", "RL-BOISE", 1)]
        messy = bodies[("TRANS-MESSY", "RL-BOISE", 1)]
        assert clean["event_at"] == "2027-07-28T14:00:00.000000+00:00"
        assert messy["event_at"] == "2027-08-10T14:00:00.000000+00:00"
        assert messy["exception_id"] == EXCEPTION_ID and messy["exception_open"] is True
        first_commission = bodies[("TRANS-MESSY", "CM-BOISE", 1)]
        corrected = bodies[("TRANS-MESSY", "CM-BOISE", 2)]
        assert (first_commission["status"], first_commission["local_checks_passed"]) == (
            "HOLD_KEY_DEPENDENCY",
            3,
        )
        assert (corrected["status"], corrected["local_checks_passed"]) == (
            "PASS_AFTER_CORRECTION",
            4,
        )
        failed = bodies[("TRANS-MESSY", "RX-BOISE", 1)]
        passed = bodies[("TRANS-MESSY", "RX-BOISE", 2)]
        assert failed["status"] == "FAIL_KEY_DEPENDENCY"
        assert failed["restored_fixture_sha256"] is None
        assert passed["status"] == "PASS_AFTER_RETRY"
        assert passed["restored_fixture_sha256"] == passed["fixture_metadata_sha256"]
        assert {b["exception_id"] for b in bodies.values() if b["exception_open"]} == {EXCEPTION_ID}


def test_failed_recovery_availability_and_new_destination_gate(tmp_path):
    root = _build(tmp_path)
    with pytest.raises(CompanyStoreError, match="New private"):
        create(root, repository=REPOSITORY, clean_branch="NEXT-C", messy_branch="NEXT-M")
    clone = tmp_path / "read-clone"
    shutil.copytree(root, clone)
    store = CompanyStore(clone)
    store.grant("LEARNER", "LOCAL-CHECK", COMPANY, "TRANS-MESSY", "recovery_exercise")
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "LEARNER",
            "LOCAL-CHECK",
            COMPANY,
            "TRANS-MESSY",
            "recovery_exercise",
            "RX-BOISE",
            version=1,
            as_of="2027-07-20T10:59:59+00:00",
        )
    row = store.read_version(
        "LEARNER",
        "LOCAL-CHECK",
        COMPANY,
        "TRANS-MESSY",
        "recovery_exercise",
        "RX-BOISE",
        version=1,
        as_of="2027-07-20T11:00:00+00:00",
    )
    assert json.loads(row["content"])["status"] == "FAIL_KEY_DEPENDENCY"


def test_resealed_false_real_operation_and_bypass_cure_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        raw = db.execute(
            "SELECT content FROM versions WHERE branch='TRANS-MESSY' "
            "AND system='site_release' AND record='RL-BOISE'"
        ).fetchone()[0]
        body = json.loads(raw)
        body["real_world_provider_operation"] = True
        body["exception_open"] = False
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE branch='TRANS-MESSY' "
            "AND system='site_release' AND record='RL-BOISE'",
            (json.dumps(body).encode(),),
        )
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="Native transition source identity differs"):
        verify(root, repository=REPOSITORY)
