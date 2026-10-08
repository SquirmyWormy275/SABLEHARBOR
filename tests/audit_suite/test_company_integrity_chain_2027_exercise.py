"""Disposable C3 source must retain the failure before its corrected successor."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_integrity_chain_2027_exercise as integrity
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path: Path) -> Path:
    destination = tmp_path / "integrity-source"
    integrity.create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def test_clean_blocks_before_transform_and_messy_retains_partial_then_correction(tmp_path):
    source_db = PRIVATE / integrity.DQ_ROOT / "run-v1/a/company.sqlite3"
    original = integrity._private_file(source_db, db=True)
    root = _build(tmp_path)
    assert integrity._private_file(source_db, db=True) == original
    manifest = integrity.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert manifest["native_version_count"] == 29
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["counts"] == {"CLEAN": 12, "MESSY": 17}
    assert {side: len(ids) for side, ids in receipt["selected_route_task_ids"].items()} == {
        "A": 17,
        "B": 17,
    }
    assert all(len(items) == 3 for items in receipt["copies"].values())
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT branch,system,record,version,event_at,available_at,imported_at,content "
            "FROM versions ORDER BY branch,event_at,system"
        ).fetchall()
        assert len(rows) == 29
        assert all(row["imported_at"] < row["event_at"] < row["available_at"] for row in rows)
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )

        def body(branch, system, version=1):
            row = db.execute(
                "SELECT content,event_at FROM versions WHERE branch=? AND system=? AND version=?",
                (branch, system, version),
            ).fetchone()
            return json.loads(row["content"]), row["event_at"]

        clean_check, clean_check_at = body("INTEGRITY-CLEAN", "integrity_check")
        clean_report, clean_report_at = body("INTEGRITY-CLEAN", "transform_report")
        assert clean_check["result"] == "MISMATCH_DETECTED"
        assert clean_check["checked_before_first_transform"] is True
        assert clean_check_at < clean_report_at
        assert clean_report["dq_report"]["status"] == "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
        assert (
            body("INTEGRITY-CLEAN", "aggregate_report")[0]["dq_aggregate"][
                "accepted_rows_only_total"
            ]
            == 23
        )
        messy_report, first_report_at = body("INTEGRITY-MESSY", "transform_report")
        messy_check, messy_check_at = body("INTEGRITY-MESSY", "integrity_check")
        assert first_report_at < messy_check_at
        assert messy_report["integrity_state_at_transform"] == "NOT_CHECKED"
        assert messy_report["dq_report"]["status"] == "PARTIAL_UNRELIABLE"
        assert messy_report["dq_report"]["failed_rows"] == 1
        assert (
            body("INTEGRITY-MESSY", "aggregate_report")[0]["dq_aggregate"][
                "accepted_rows_only_total"
            ]
            == 14
        )
        visible, visible_at = body("INTEGRITY-MESSY", "internal_visibility")
        assert first_report_at < visible_at < messy_check_at
        assert visible["status"] == "PARTIAL_UNRELIABLE"
        assert visible["external_distribution"] is False
        successor, successor_at = body("INTEGRITY-MESSY", "transform_report", 2)
        assert messy_check_at < successor_at
        assert successor["dq_report"]["status"] == "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
        assert (
            body("INTEGRITY-MESSY", "aggregate_report", 2)[0]["dq_aggregate"][
                "accepted_rows_only_total"
            ]
            == 23
        )
        lineage, _ = body("INTEGRITY-MESSY", "correction_lineage")
        assert lineage["historical_partial_still_unreliable"] is True
        assert lineage["retroactive_rewrite"] is False
        assert all(
            json.loads(row["content"])["audit_task_credit"] is False
            for row in rows
            if row["system"] != "test_copy"
        )


def test_frozen_dq_reader_rejects_even_dangling_sidecar_symlink(tmp_path):
    copied = tmp_path / "company.sqlite3"
    shutil.copyfile(PRIVATE / integrity.DQ_ROOT / "run-v1/a/company.sqlite3", copied)
    copied.chmod(0o600)
    (tmp_path / "company.sqlite3-wal").symlink_to(tmp_path / "missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        integrity._private_file(copied, db=True)


def test_resealed_false_partial_result_cannot_pass_semantic_reperformance(tmp_path):
    root = _build(tmp_path)
    db_path = root / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='INTEGRITY-MESSY' "
            "AND system='transform_report' AND version=1"
        ).fetchone()
        body = json.loads(row[0])
        body["dq_report"]["status"] = "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        false_sha = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='INTEGRITY-MESSY' "
            "AND system='transform_report' AND version=1",
            (raw, false_sha),
        )
    receipt_path = root / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "transform_report" and ref["version"] == 1:
            ref["sha256"] = false_sha
    receipt_path.write_text(json.dumps(receipt, sort_keys=True))
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(db_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="content|hash|provenance"):
        integrity.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
