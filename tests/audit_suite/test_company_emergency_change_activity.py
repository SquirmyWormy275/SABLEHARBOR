"""Bounded source-native emergency-change exercise, without audit or deployment."""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from enterprise.audit_suite.company_emergency_change_activity import (
    BASELINE,
    CANDIDATE,
    EmergencyRecipe,
    LocalFixture,
    generate_pair,
)
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPO = Path(__file__).resolve().parents[2]


def recipe(**changes):
    value = dict(
        company="SABLEHARBOR",
        clean_branch="eng005-clean",
        messy_branch="eng005-messy",
        exercise_id="ENG005-LOCAL-001",
        start_at="2027-04-10T09:00:00+00:00",
        local_rule=(
            "Block without evidenced emergency authority; retain an invalid local bypass "
            "and open exception."
        ),
    )
    value.update(changes)
    return EmergencyRecipe(**value)


def test_pair_preserves_blocked_clean_and_invalid_messy_causality(tmp_path):
    tmp_path.chmod(0o700)
    target = tmp_path / "native-pair"
    receipt = generate_pair(target, repository=REPO, recipe=recipe())
    assert receipt["record_count"] == 19
    assert receipt["clean_gate"] == "BLOCKED_UNVERIFIED_AUTHORITY"
    assert receipt["messy_exception"] == "LOCAL-ENG005-EXC-001_OPEN_AFTER_IN_MEMORY_ROLLBACK"
    assert not receipt["actual_2027_operation"] and not receipt["deployed_service_change"]
    assert not receipt["corporate_emergency_approval_asserted"]
    assert not receipt["audit_task_credit"]
    assert not receipt["active_A_B_P1_mutated"]
    assert (target.stat().st_mode & 0o777) == 0o700
    assert (target / "SOURCE_RECEIPT.json").stat().st_mode & 0o777 == 0o600
    assert json.loads((target / "SOURCE_RECEIPT.json").read_text()) == receipt

    dbpath = target / "company.sqlite3"
    manifest_path = target / "RUN-MANIFEST.json"
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_receipt_sha256"] == sha((target / "SOURCE_RECEIPT.json").read_bytes())
    assert manifest["native_db_sha256"] == sha(dbpath.read_bytes())
    assert manifest["record_count"] == 19 and manifest["audit_task_credit"] is False
    assert dbpath.stat().st_mode & 0o777 == 0o600
    db = sqlite3.connect(dbpath.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    try:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 19
        assert db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM collections").fetchone()[0] == 0
        for branch, expected in (("eng005-clean", 8), ("eng005-messy", 11)):
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM versions WHERE branch=? ORDER BY event_at", (branch,)
                )
            ]
            assert len(rows) == expected
            previous = None
            for row in rows:
                assert sha(row["content"]) == row["sha256"]
                body = json.loads(row["content"])
                assert body["previous_source"] == previous
                assert body["classification"].startswith("FUTURE_LOCAL_EMERGENCY_CHANGE_FIXTURE")
                assert body["corporate_emergency_authority"] == "UNVERIFIED_NOT_ASSERTED"
                assert body["target"] == "IN_MEMORY_REFERENCE_CONFIGURATION_ONLY"
                assert datetime.fromisoformat(row["event_at"]).year == 2027
                assert datetime.fromisoformat(row["imported_at"]).year == 2026
                assert row["origin"] == "AUTHORED_TRAINING_SOURCE"
                previous = {
                    "system": row["system"],
                    "record": row["record"],
                    "version": row["version"],
                    "sha256": row["sha256"],
                }
            by_record = {r["record"]: json.loads(r["content"]) for r in rows}
            assert by_record["AUTHORITY-CHECK"]["contact_assignment_is_approval"] is False
            assert by_record["GATE"]["decision"] == "BLOCKED_UNVERIFIED_AUTHORITY"
            assert by_record["FINAL"]["active_sha256"] == sha(encoded(BASELINE))
            assert by_record["FINAL"]["baseline_restored"] is True
            assert by_record["FINAL"]["deployed"] is False
            assert by_record["REVIEW"]["corporate_retroactive_approval"] is False
            if branch == "eng005-clean":
                assert "INVALID-BYPASS" not in by_record
                assert by_record["BLOCKED-STATE"]["candidate_applied"] is False
                assert by_record["FINAL"]["open_exception_ids"] == []
            else:
                assert (
                    by_record["INVALID-BYPASS"]["decision"]
                    == "SIMULATED_INVALID_LOCAL_BYPASS_PENDING_AUTHORITY"
                )
                assert by_record["LOCAL-APPLY"]["applied_config"] == CANDIDATE
                assert by_record["LOCAL-APPLY"]["deployed"] is False
                assert by_record["ROLLBACK"]["restored_config"] == BASELINE
                assert by_record["FINAL"]["open_exception_ids"] == ["LOCAL-ENG005-EXC-001"]
    finally:
        db.close()
    assert not list(target.rglob("*-wal")) and not list(target.rglob("*-shm"))


def test_local_fixture_changes_only_in_memory_state():
    fixture = LocalFixture()
    assert fixture.config == BASELINE
    transition = fixture.apply_simulated_invalid_bypass(CANDIDATE)
    assert transition == {
        "before_sha256": sha(encoded(BASELINE)),
        "after_sha256": sha(encoded(CANDIDATE)),
    }
    assert fixture.rollback() == {
        "before_sha256": sha(encoded(CANDIDATE)),
        "after_sha256": sha(encoded(BASELINE)),
    }
    assert fixture.config == BASELINE


def test_invalid_or_nonprospective_recipe_creates_no_root(tmp_path):
    tmp_path.chmod(0o700)
    for bad in (
        recipe(messy_branch="eng005-clean"),
        recipe(start_at="2026-09-28T09:00:00+00:00"),
        recipe(local_rule=""),
    ):
        target = tmp_path / ("bad-" + sha(encoded(bad.__dict__))[:8])
        with pytest.raises(CompanyStoreError):
            generate_pair(target, repository=REPO, recipe=bad)
        assert not target.exists()


def test_operator_cli_works_outside_checkout_cwd(tmp_path):
    tmp_path.chmod(0o700)
    config = tmp_path / "recipe.json"
    config.write_text(json.dumps(recipe().__dict__))
    config.chmod(0o600)
    target = tmp_path / "cli-pair"
    script = REPO / "tools/audit_suite/emergency_change_exercise.py"
    result = subprocess.run(
        [sys.executable, str(script), "--config", str(config), "--output", str(target)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["record_count"] == 19
    assert (target / "RUN-MANIFEST.json").is_file()
