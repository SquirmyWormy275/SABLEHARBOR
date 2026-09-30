"""Bounded fictional purpose routing, source clocks and fail-closed receipts."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_processing_purpose_2027_simulation as purpose
from enterprise.audit_suite.company_store import CompanyStoreError


def _context():
    result = {"phi": {}, "dataset": {}, "terms_sha256": "a" * 64}
    for scenario in purpose.BRANCHES:
        result["phi"][scenario] = {}
        result["dataset"][scenario] = {}
        for system, record in (
            ("contract_register", "BAA-CUST-01"),
            ("contract_register", "BAA-SUB-01"),
            ("flow_register", "FLOW-RECON-01"),
            ("exception_register", "EXC-01"),
        ):
            result["phi"][scenario][system, record] = {
                "ref": {
                    "company": purpose.COMPANY,
                    "branch": purpose.UPSTREAM["PHI"]["branches"][scenario],
                    "system": system,
                    "record": record,
                    "version": 1,
                    "sha256": "b" * 64,
                    "event_at": "2027-07-28T20:00:00.000000+00:00",
                    "available_at": "2027-07-28T20:00:00.000000+00:00",
                    "imported_at": "2026-09-29T20:00:00.000000+00:00",
                }
            }
        for system in (
            "dataset_inventory",
            "label_quarantine",
            "classification_review",
            "enforcement_followup",
        ):
            result["dataset"][scenario][system, purpose.DATASET] = {
                "ref": {
                    "company": purpose.COMPANY,
                    "branch": purpose.UPSTREAM["DATASET"]["branches"][scenario],
                    "system": system,
                    "record": purpose.DATASET,
                    "version": 1,
                    "sha256": "c" * 64,
                    "event_at": "2027-07-30T09:00:00.000000+00:00",
                    "available_at": "2027-07-30T09:00:00.000000+00:00",
                    "imported_at": "2026-09-29T20:00:00.000000+00:00",
                }
            }
    return result


def test_contract_match_stays_pending_and_ai_reuse_is_refused():
    context = _context()
    clean = purpose._expected_rows(context, "CLEAN")
    messy = purpose._expected_rows(context, "MESSY")
    assert len(clean) == len(messy) == 4
    assert clean[1]["body"]["decision"] == "SCENARIO_CONTRACT_PURPOSE_MATCH_EXECUTION_PENDING"
    assert clean[1]["body"]["execution_gate"] == "PENDING_DATA_OWNER_CLASSIFICATION_AND_ENFORCEMENT"
    assert messy[0]["body"]["requested_purpose"] == "AI_MODEL_TRAINING_REUSE"
    assert messy[0]["body"]["attempted_request_only"] is True
    assert messy[1]["body"]["decision"] == "REFUSED_UNAPPROVED_AI_REUSE"
    assert messy[2]["body"]["case_status"] == "QUARANTINED_REFUSED_REQUEST"
    assert messy[2]["body"]["upstream_ba_exception_id"] == purpose.phi_ba.EXCEPTION_ID
    assert messy[2]["body"]["purpose_exception_id"] != purpose.phi_ba.EXCEPTION_ID
    for rows in (clean, messy):
        assert (
            rows[0]["event_at"]
            > context["dataset"]["CLEAN"]["enforcement_followup", purpose.DATASET]["ref"][
                "available_at"
            ]
        )
        assert rows[1]["body"]["source_previous"]["sha256"] == rows[0]["sha256"]
        assert rows[2]["body"]["source_previous"]["sha256"] == rows[1]["sha256"]
        assert rows[3]["body"]["source_previous"]["sha256"] == rows[2]["sha256"]
        assert all(r["body"]["payload_bytes"] == 0 for r in rows)
        assert [r["body"]["actor_person_id"] for r in rows] == [
            "AS-P014",
            "AS-P003",
            "AS-P003",
            "AS-P014",
        ]
        assert all(r["body"]["real_world_processing_or_transfer"] is False for r in rows)
        assert all(r["available_at"] > r["event_at"] for r in rows)
        assert rows[3]["body"]["approved_execution_count"] == 0


def test_create_verify_and_receipt_tamper(tmp_path: Path, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(
        purpose, "_input_context", lambda repository, private_repository: _context()
    )
    output = parent / "run"
    purpose.create(output, repository=tmp_path, private_repository=tmp_path)
    assert (
        purpose.verify(output, repository=tmp_path, private_repository=tmp_path)[
            "native_version_count"
        ]
        == 8
    )
    receipt = output / "RECEIPT.json"
    body = json.loads(receipt.read_text())
    assert body["approved_execution_count_per_branch"] == {"CLEAN": 0, "MESSY": 0}
    assert body["open_purpose_exception_ids"]["MESSY"] == [purpose.EXCEPTION_ID]
    body["refused_request_count_per_branch"]["MESSY"] = 0
    receipt.write_text(json.dumps(body))
    with pytest.raises(CompanyStoreError):
        purpose.verify(output, repository=tmp_path, private_repository=tmp_path)


def test_dangling_wal_is_rejected(tmp_path: Path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    db = private / "company.sqlite3"
    receipt = private / "RECEIPT.json"
    db.write_bytes(b"fixture")
    receipt.write_bytes(b"{}")
    db.chmod(0o600)
    receipt.chmod(0o600)
    (private / "company.sqlite3-wal").symlink_to("missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        purpose._frozen({"database": db, "receipt": receipt})
