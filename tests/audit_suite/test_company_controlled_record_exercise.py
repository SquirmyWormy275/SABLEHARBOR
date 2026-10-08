"""A selected source pointer cannot become accepted policy or audit evidence."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_controlled_record_exercise import _frozen_db, create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "record"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_selected_original_clean_and_messy_alias_history(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"] == 9
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {side: len(ids) for side, ids in receipt["selected_route_task_ids"].items()} == {
        "A": 3,
        "B": 3,
    }
    assert {scenario: len(rows) for scenario, rows in receipt["records"].items()} == {
        "CLEAN": 4,
        "MESSY": 5,
    }
    assert {scenario: len(refs) for scenario, refs in receipt["selected_source_refs"].items()} == {
        "CLEAN": 2,
        "MESSY": 3,
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
    clean = bodies[("RECORD-CLEAN", "record_registration")]
    messy_alias = bodies[("RECORD-MESSY", "local_alias_marker")]
    messy_retrieval = bodies[("RECORD-MESSY", "controlled_retrieval")]
    assert clean["source_original_locator"]["system"] == "classification_review"
    assert messy_alias["source_original_locator"] is None
    assert messy_alias["invalid_alias_has_source_version_or_hash"] is False
    assert messy_retrieval["source_original_locator"]["system"] == "classification_review"
    assert messy_retrieval["invalid_alias_history_open"] is True
    assert messy_retrieval["retrieval_uses_authoritative_original"] is True
    assert all(
        body["approved_retention_schedule"] == "UNDETERMINED"
        and body["legal_hold_disposition"] == "UNDETERMINED"
        and body["disposition_executed"] is False
        and body["copied_source_bytes_as_audit_pack"] is False
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


def test_resealed_false_disposition_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='RECORD-CLEAN' "
            "AND system='disposition_screen'"
        ).fetchone()
        body = json.loads(row[0])
        body["approved_retention_schedule"] = "APPROVED"
        body["disposition_executed"] = True
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='RECORD-CLEAN' "
            "AND system='disposition_screen'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["CLEAN"]:
        if ref["system"] == "disposition_screen":
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
