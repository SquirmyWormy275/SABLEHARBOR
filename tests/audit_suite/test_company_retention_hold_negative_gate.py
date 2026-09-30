"""A pending held-copy disposition request must preserve the disposable copy."""

import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_retention_hold_negative_gate import _frozen_db, create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _build(tmp_path):
    root = tmp_path / "held"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def test_clean_denial_and_messy_attempt_cure_preserve_copies(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"] == 8
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["fixture_identity_before"] == receipt["fixture_identity_after"]
    assert {
        side: {control: len(ids) for control, ids in controls.items()}
        for side, controls in receipt["selected_route_task_ids"].items()
    } == {
        "A": {"SH-DAT-003": 6, "SH-REC-004": 7},
        "B": {"SH-DAT-003": 6, "SH-REC-004": 7},
    }
    assert {scenario: len(refs) for scenario, refs in receipt["records"].items()} == {
        "CLEAN": 3,
        "MESSY": 5,
    }
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        bodies = {(row["branch"], row["system"]): json.loads(row["content"]) for row in rows}
        assert len(rows) == 8
        assert all(row["imported_at"] < row["event_at"] == row["available_at"] for row in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert bodies[("HOLD-CLEAN", "disposition_gate")]["status"] == "DENIED_PENDING_AUTHORITY"
    assert bodies[("HOLD-MESSY", "premature_attempt")]["status"] == (
        "PREMATURE_LOCAL_DISPOSITION_REQUEST"
    )
    assert bodies[("HOLD-MESSY", "disposition_gate")]["status"] == (
        "DENIED_PENDING_AUTHORITY_AND_HOLD"
    )
    assert bodies[("HOLD-MESSY", "cure_notice")]["status"] == (
        "REQUEST_WITHDRAWN_HOLD_REVIEW_STILL_OPEN"
    )
    assert all(
        body["legal_decision"] == "PENDING"
        and body["data_owner_decision"] == "PENDING"
        and body["unlink_executed"] is False
        and body["legal_hold_release"] == "NOT_AUTHORIZED"
        and body["audit_task_credit"] is False
        and body["real_world_operation"] is False
        for body in bodies.values()
    )
    for scenario in ("CLEAN", "MESSY"):
        path = root / "copies" / f"{scenario}.bin"
        assert path.exists()
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == (receipt["fixture_identity_after"][scenario]["sha256"])
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


def test_resealed_false_unlink_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='HOLD-MESSY' AND system='cure_notice'"
        ).fetchone()
        body = json.loads(row[0])
        body["unlink_executed"] = True
        body["legal_hold_release"] = "APPROVED"
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='HOLD-MESSY' "
            "AND system='cure_notice'",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["MESSY"]:
        if ref["system"] == "cure_notice":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="negative gate or clock differs"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_fixture_replacement_rejected_even_when_bytes_match(tmp_path):
    root = _build(tmp_path)
    path = root / "copies" / "CLEAN.bin"
    raw = path.read_bytes()
    replacement = root / "copies" / "replacement.bin"
    replacement.write_bytes(raw)
    replacement.chmod(0o600)
    os.replace(replacement, path)
    with pytest.raises(CompanyStoreError, match="unchanged copy differs"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)
