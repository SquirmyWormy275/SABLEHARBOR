"""An incomplete company export cannot become approved or audit-collected support."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_source_extraction_exercise import _frozen_db, create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "extraction"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_selected_query_keeps_incomplete_attempt_and_correction(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"] == 9
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {side: len(ids) for side, ids in receipt["selected_route_task_ids"].items()} == {
        "A": 6,
        "B": 6,
    }
    assert {
        scenario: len(refs) for scenario, refs in receipt["selected_source_population_refs"].items()
    } == {
        "CLEAN": 4,
        "MESSY": 6,
    }
    assert {scenario: len(refs) for scenario, refs in receipt["records"].items()} == {
        "CLEAN": 4,
        "MESSY": 5,
    }
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        bodies = {(row["branch"], row["system"]): json.loads(row["content"]) for row in rows}
        assert len(rows) == 9
        assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    clean = bodies[("EXTRACT-CLEAN", "extract_reconciliation")]
    first = bodies[("EXTRACT-MESSY", "extract_attempt")]
    discrepancy = bodies[("EXTRACT-MESSY", "extract_reconciliation")]
    correction = bodies[("EXTRACT-MESSY", "extract_correction")]
    pending = bodies[("EXTRACT-MESSY", "review_gate")]
    assert clean["returned_count"] == 4
    assert clean["excluded_count"] == 0
    assert first["returned_count"] == 5
    assert first["declared_source_population_count"] == 6
    assert first["excluded_refs"][0]["system"] == "local_label"
    assert discrepancy["local_query_reconciliation"] == "FAIL_MISSING_LOCAL_LABEL"
    assert correction["returned_count"] == 6
    assert correction["excluded_count"] == 0
    assert correction["initial_omission_preserved"] is True
    assert correction["output_kind"] == "SOURCE_VERSION_INDEX_NO_ORIGINAL_CONTENT_BYTES"
    assert correction["source_content_bytes_copied"] is False
    assert pending["initial_exception_disposition"] == "OPEN_PENDING_INDEPENDENT_REVIEW"
    assert all(
        body["independent_extraction_review"] == "PENDING"
        and body["approved_view"] is False
        and body["audit_collection"] is False
        and body["audit_artifact_retained"] is False
        and body["audit_task_credit"] is False
        and body["real_world_operation"] is False
        for body in bodies.values()
    )


def test_frozen_original_rejects_sidecar(tmp_path):
    source = PRIVATE / (
        "enterprise/generated/audit-suite/company-dataset-classification-2026-09-29/"
        "run-v1/company.sqlite3"
    )
    clone = tmp_path / "company.sqlite3"
    shutil.copy2(source, clone)
    assert _frozen_db(clone)[-1] == hashlib.sha256(source.read_bytes()).hexdigest()
    sidecar = tmp_path / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="active sidecar"):
        _frozen_db(clone)


def test_resealed_false_approval_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='EXTRACT-MESSY' AND system='review_gate'"
        ).fetchone()
        body = json.loads(row[0])
        body["independent_extraction_review"] = "APPROVED"
        body["approved_view"] = True
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='EXTRACT-MESSY' "
            "AND system='review_gate'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "review_gate":
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
