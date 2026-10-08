"""Prospective internal draft gate, not a contract or audit completion."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_contract_draft_exercise import COMPANY, create, verify
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "contract-draft"
    create(root, repository=REPOSITORY, clean_branch="DRAFT-CLEAN", messy_branch="DRAFT-MESSY")
    return root


def test_native_draft_boundaries_causal_paths_and_three_clocks(tmp_path):
    root = _build(tmp_path)
    assert verify(root)["native_version_count"] == 12
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["final_states"] == {"CLEAN": "HOLD", "MESSY": "QUARANTINED"}
    assert receipt["open_exception_ids"] == {
        "CLEAN": [],
        "MESSY": ["EXC-CONTRACT-01-PREMATURE-CLEARANCE"],
    }
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["exception_event_row_counts"] == {"CLEAN": 0, "MESSY": 5}
    assert {
        (p["provider_id"], p["contract_id"], p["contract_status"])
        for p in receipt["provider_boundaries"]
    } == {("CP-SWITCH", "RT-SO-RENO", "DRAFT"), ("CP-IDACORE", "RT-SO-BOISE", "DRAFT")}
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,system,record").fetchall()
        assert len(rows) == 12
        assert all(r["event_at"] > r["imported_at"] for r in rows)
        events = [json.loads(r["content"]) for r in rows if r["system"] == "contract_event"]
        assert all(
            not e["signature"]
            and not e["legal_approval"]
            and not e["contract_execution"]
            and not e["actual_phi_processing"]
            and not e["external_communication"]
            for e in events
        )
        assert [e["missing_provider_ids"] for e in events if e["scenario"] == "MESSY"] == [
            ["CP-IDACORE"],
            ["CP-IDACORE"],
            ["CP-IDACORE"],
            [],
            [],
            [],
        ]
        assert [e["action"] for e in events if e["scenario"] == "MESSY"] == [
            "DRAFT_CLAUSE_MATRIX",
            "PREMATURE_LOCAL_CLEARANCE_MARKER",
            "LATE_INTERNAL_REVIEW",
            "DRAFT_BACKFILL",
            "PROPOSED_CURE_ROUTE",
            "UNRESOLVED_EXCEPTION_RECONCILE",
        ]
        late = next(
            r for r in rows if r["branch"] == "DRAFT-MESSY" and r["record"] == "DRAFT-01-E03"
        )
        assert late["event_at"] == "2027-05-03T09:00:00.000000+00:00"
        assert late["available_at"] == "2027-05-03T10:00:00.000000+00:00"
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_ordinary_read_requires_availability_not_just_event(tmp_path):
    root = _build(tmp_path)
    clone = tmp_path / "read-clone"
    shutil.copytree(root, clone)
    store = CompanyStore(clone)
    store.grant("LEARNER", "LOCAL-CHECK", COMPANY, "DRAFT-MESSY", "contract_event")
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "LEARNER",
            "LOCAL-CHECK",
            COMPANY,
            "DRAFT-MESSY",
            "contract_event",
            "DRAFT-01-E03",
            version=1,
            as_of="2027-05-03T09:59:59+00:00",
        )
    row = store.read_version(
        "LEARNER",
        "LOCAL-CHECK",
        COMPANY,
        "DRAFT-MESSY",
        "contract_event",
        "DRAFT-01-E03",
        version=1,
        as_of="2027-05-03T10:00:00+00:00",
    )
    assert json.loads(row["content"])["after"] == "QUARANTINED"
    assert verify(root)["audit_task_credit"] is False


def test_collision_and_resealed_false_approval_fail(tmp_path):
    invalid = tmp_path / "invalid"
    with pytest.raises(CompanyStoreError, match="Distinct branch"):
        create(invalid, repository=REPOSITORY, clean_branch="SAME", messy_branch="SAME")
    assert not invalid.exists()
    root = _build(tmp_path)
    with pytest.raises(CompanyStoreError, match="New private"):
        create(root, repository=REPOSITORY, clean_branch="NEXT-C", messy_branch="NEXT-M")
    with sqlite3.connect(root / "company.sqlite3") as db:
        row = db.execute(
            "SELECT content FROM versions WHERE branch='DRAFT-MESSY' AND record='DRAFT-01-E02'"
        ).fetchone()
        body = json.loads(row[0])
        body["legal_approval"] = True
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE branch='DRAFT-MESSY' AND record='DRAFT-01-E02'",
            (json.dumps(body).encode(),),
        )
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="Native contract source identity/content mismatch"):
        verify(root)


def test_resealed_receipt_cannot_invent_executed_provider_contract(tmp_path):
    root = _build(tmp_path)
    receipt_path = root / "RECEIPT.json"
    manifest_path = root / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["provider_boundaries"][0]["contract_executed"] = True
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(
        CompanyStoreError, match="Canonical provider boundary or contact pins differ"
    ):
        verify(root)
