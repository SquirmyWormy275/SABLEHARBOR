"""Prospective local flow exercise only; no active company or audit workroom."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_data_flow_exercise import COMPANY, create, verify
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.company_store import _json as store_json
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "data-flow"
    create(root, repository=REPOSITORY, clean_branch="FLOW-CLEAN", messy_branch="FLOW-MESSY")
    return root


def test_company_native_clean_and_messy_causality_and_timestamp_separation(tmp_path):
    root = _build(tmp_path)
    assert verify(root)["native_version_count"] == 13
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["final_states"] == {"CLEAN": "BLOCKED", "MESSY": "QUARANTINED"}
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 5}
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT branch,system,record,event_at,available_at,imported_at,content "
            "FROM versions ORDER BY branch,system,record"
        ).fetchall()
        assert len(rows) == 13
        assert all(
            r["event_at"] == r["available_at"] and r["imported_at"] != r["event_at"] for r in rows
        )
        events = [json.loads(r["content"]) for r in rows if r["system"] == "flow_event"]
        assert all(
            r["data_bytes"] == 0 and r["actual_transfer"] is False and r["deployed_site"] is False
            for r in events
        )
        assert [
            e["outcome"]
            for e in events
            if e["scenario"] == "CLEAN" and e["action"] == "REPLICATION_REQUEST"
        ] == ["DENY_NO_AUTHORITY_OR_DEPLOYED_ROUTE"]
        assert [
            e["outcome"]
            for e in events
            if e["scenario"] == "MESSY" and e["action"] == "RECORD_RECONCILE"
        ] == ["DESTINATION_ACK_UNVERIFIED_EXCEPTION_OPEN"]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert not list(root.glob("*-wal")) and not list(root.glob("*-shm"))


def test_ordinary_current_grant_collection_reaches_native_source_only_after_event(tmp_path):
    root = _build(tmp_path)
    clone = tmp_path / "collection-clone"
    shutil.copytree(root, clone)
    store = CompanyStore(clone)
    store.grant("LEARNER-01", "EXERCISE-ENG", COMPANY, "FLOW-CLEAN", "flow_event")
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "LEARNER-01",
            "EXERCISE-ENG",
            COMPANY,
            "FLOW-CLEAN",
            "flow_event",
            "FLOW-01-E02",
            version=1,
            as_of="2027-02-01T10:04:59+00:00",
        )
    row = store.read_version(
        "LEARNER-01",
        "EXERCISE-ENG",
        COMPANY,
        "FLOW-CLEAN",
        "flow_event",
        "FLOW-01-E02",
        version=1,
        as_of="2027-02-01T10:05:00+00:00",
    )
    assert json.loads(row["content"])["outcome"] == "REJECT_UNVERIFIED_RESTRICTED_CANDIDATE"
    receipt = store.collect(
        "LEARNER-01",
        "EXERCISE-ENG",
        COMPANY,
        "FLOW-CLEAN",
        "flow_event",
        "FLOW-01-E02",
        version=1,
        as_of="2027-02-01T10:05:00+00:00",
        command_id="TEST-COLLECT-01",
    )
    assert receipt["source"]["sha256"] == row["sha256"]
    assert receipt["source"]["event_at"] == row["event_at"]
    assert verify(root)["audit_task_credit"] is False


def test_fails_closed_on_scope_collision_and_privileged_tamper(tmp_path):
    root = tmp_path / "invalid"
    with pytest.raises(CompanyStoreError, match="Distinct branch"):
        create(root, repository=REPOSITORY, clean_branch="SAME", messy_branch="SAME")
    assert not root.exists()
    root = _build(tmp_path)
    with pytest.raises(CompanyStoreError, match="New canonical destination"):
        create(root, repository=REPOSITORY, clean_branch="OTHER-A", messy_branch="OTHER-B")
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE branch=? AND system=? AND record=?",
            (b"{}", "FLOW-MESSY", "flow_event", "FLOW-01-E03"),
        )
    with pytest.raises(CompanyStoreError, match="receipt pin mismatch"):
        verify(root)


def test_resealed_false_transfer_does_not_pass_causal_verification(tmp_path):
    root = _build(tmp_path)
    receipt_path, manifest_path = root / "RECEIPT.json", root / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT * FROM versions WHERE branch=? AND system=? AND record=?",
            ("FLOW-MESSY", "flow_event", "FLOW-01-E03"),
        ).fetchone()
        body = json.loads(row["content"])
        body["actual_transfer"] = True
        raw = encoded(body)
        digest = sha(raw)
        provenance = json.loads(row["provenance"])
        key = [row[k] for k in ("company", "branch", "system", "record")]
        input_digest = sha(
            store_json(
                [key, 0, row["event_at"], row["available_at"], row["origin"], provenance, digest]
            ).encode()
        )
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=?,sha256=?,input_digest=? "
            "WHERE branch=? AND system=? AND record=?",
            (raw, digest, input_digest, "FLOW-MESSY", "flow_event", "FLOW-01-E03"),
        )
    receipt["records"]["MESSY"][3]["sha256"] = digest
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="Causal flow trace differs"):
        verify(root)
