"""Selected synthetic dataset classification remains local and un-enforced."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_dataset_classification_exercise import create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "dataset"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_one_marker_classification_separate_from_enforcement(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"]
        == 10
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {side: len(ids) for side, ids in receipt["selected_route_task_ids"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert {scenario: len(rows) for scenario, rows in receipt["records"].items()} == {
        "CLEAN": 4,
        "MESSY": 6,
    }
    assert {
        scenario: len(rows) for scenario, rows in receipt["selected_upstream_refs"].items()
    } == {"CLEAN": 3, "MESSY": 4}
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        bodies = {(row["branch"], row["system"]): json.loads(row["content"]) for row in rows}
        assert len(rows) == 10
        assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    clean = bodies[("DATASET-CLEAN", "classification_review")]
    messy = bodies[("DATASET-MESSY", "classification_review")]
    assert (
        clean["classification_recommendation"]
        == messy["classification_recommendation"]
        == "RESTRICTED_SCENARIO_METADATA"
    )
    assert clean["classification_decision_state"] == "LOCAL_RECOMMENDATION_NOT_DATA_OWNER_ACCEPTED"
    assert (
        bodies[("DATASET-MESSY", "local_label")]["classification_decision_state"]
        == "INVALID_LOCAL_LABEL_NOT_CLASSIFICATION_DECISION"
    )
    assert bodies[("DATASET-MESSY", "local_label")]["real_world_exposure_or_disclosure"] is False
    assert bodies[("DATASET-MESSY", "label_quarantine")]["local_label_quarantined"] is True
    assert bodies[("DATASET-MESSY", "enforcement_followup")]["invalid_label_history_open"] is True
    assert all(
        body["enforcement_status"] == "NOT_VERIFIED"
        for (branch, system), body in bodies.items()
        if system == "enforcement_followup"
    )
    assert all(
        body["actual_phi_applicability"] == "UNDETERMINED"
        and body["real_phi_payload"] is False
        and body["retention_rule_approved"] is False
        and body["audit_task_credit"] is False
        and body["real_world_processing"] is False
        for body in bodies.values()
    )


def test_frozen_ba_sidecar_rejected(tmp_path):
    clone = tmp_path / "private-copy"
    clone.mkdir(mode=0o700)
    for relative in (
        "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1/MANIFEST.json",
        "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1/RECEIPT.json",
        "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/run-v1/company.sqlite3",
        "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/independent-review-v1/REVIEW.json",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/MANIFEST.json",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/RECEIPT.json",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3/company.sqlite3",
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/independent-review-v3/REVIEW.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/independent-review-v2/REVIEW.json",
    ):
        path = clone / relative
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        shutil.copy2(PRIVATE / relative, path)
    sidecar = clone / (
        "enterprise/generated/audit-suite/company-phi-ba-2027-simulation-2026-09-29/"
        "run-v1/company.sqlite3-wal"
    )
    sidecar.write_bytes(b"uncheckpointed BA mutation")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        create(tmp_path / "rejected", repository=REPOSITORY, private_repository=clone)


def test_resealed_false_enforcement_and_phi_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='DATASET-CLEAN' "
            "AND system='enforcement_followup'"
        ).fetchone()
        body = json.loads(row[0])
        body["enforcement_status"] = "ENFORCED"
        body["actual_phi_applicability"] = "YES"
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='DATASET-CLEAN' "
            "AND system='enforcement_followup'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["CLEAN"]:
        if ref["system"] == "enforcement_followup":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="content or future clock"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)
