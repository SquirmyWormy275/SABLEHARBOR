"""The selected conduct history never stands in for approved enterprise evidence."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_eth001_conduct_attestation import (
    BRANCHES,
    CANON_RECONCILIATION,
    EXCEPTION,
    MATRIX,
    PEOPLE,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _source(tmp_path: Path) -> Path:
    tmp_path.chmod(0o700)
    destination = tmp_path / "selected-source"
    create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def _change_receipt(destination: Path, change) -> None:
    source = destination / "SOURCE_RECEIPT.json"
    receipt = json.loads(source.read_text())
    change(receipt)
    source.write_bytes(encoded(receipt))
    source.chmod(0o600)
    manifest = destination / "RUN-MANIFEST.json"
    row = json.loads(manifest.read_text())
    row["source_receipt_sha256"] = sha(source.read_bytes())
    manifest.write_bytes(encoded(row))
    manifest.chmod(0o600)


def test_selected_attribution_and_messy_false_clean_remain_bounded(tmp_path):
    destination = _source(tmp_path)
    receipt = verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert receipt["native_count"] == len(receipt["native_originals"]) == 19
    assert receipt["branch_counts"] == {"CLEAN": 8, "MESSY": 11}
    assert receipt["selected_person_ids"] == list(PEOPLE)
    assert receipt["canon_reconciliation"] == CANON_RECONCILIATION
    assert receipt["real_enterprise_code_approved"] is False
    assert receipt["fictional_local_approval_only"] is True
    assert receipt["actual_workforce_population_complete"] is False
    assert receipt["substantiated_case_evidence_present"] is False
    assert receipt["no_case_population_decision"] is False
    assert receipt["sanctions_or_performance_review_conclusion"] is False
    assert receipt["actual_distribution_or_attestation"] is False
    assert receipt["source_complete"] is receipt["audit_task_credit"] is False
    assert receipt["route_sha256"][MATRIX]
    assert {side: len(rows) for side, rows in receipt["route_disposition"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert all(
        row["current_status"] == "NOT_STARTED"
        and row["current_conclusion"] == "NOT_RUN"
        and row["task_credit"] is False
        for routes in receipt["route_disposition"].values()
        for row in routes
    )
    assert all(
        "An acknowledgment without enforcement evidence cannot pass"
        in next(row for row in rows if row["task_id"].endswith("ACTION-H-SANCTIONS"))[
            "authored_test_clause"
        ]
        for rows in receipt["route_disposition"].values()
    )
    with closing(
        sqlite3.connect(
            (destination / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as db:
        rows = db.execute(
            "SELECT branch,record,content,event_at,available_at,imported_at "
            "FROM versions ORDER BY rowid"
        ).fetchall()
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )
    bodies = {(branch, record): json.loads(content) for branch, record, content, *_ in rows}
    clean = BRANCHES["CLEAN"]
    messy = BRANCHES["MESSY"]
    originals = {(row["branch"], row["record"]): row for row in receipt["native_originals"]}
    assert (
        bodies[(clean, "DISTRIBUTION-AS-P005")]["fictional_approval_original"]["sha256"]
        == originals[(clean, "FICTIONAL-LOCAL-APPROVAL")]["sha256"]
    )
    assert (
        bodies[(clean, "ACK-AS-P005")]["distribution_original"]["sha256"]
        == originals[(clean, "DISTRIBUTION-AS-P005")]["sha256"]
    )
    assert (
        bodies[(messy, "LATE-ACK-AS-P013")]["distribution_original"]["sha256"]
        == originals[(messy, "DISTRIBUTION-AS-P013")]["sha256"]
    )
    assert all(
        row["command_id"].startswith("ETH1-") and len(row["input_digest"]) == 64
        for row in receipt["native_originals"]
    )
    assert (clean, "FALSE-CLEAN") not in bodies
    assert bodies[(clean, "FINAL")]["open_exception_ids"] == []
    assert bodies[(clean, "FINAL")]["selected_late_count"] == 0
    assert bodies[(messy, "FALSE-CLEAN")]["claimed_selected_acknowledgments"] == 2
    assert len(bodies[(messy, "FALSE-CLEAN")]["actual_originals_available"]) == 1
    assert (
        bodies[(messy, "MISSING-DISCOVERY")]["false_clean_original"]
        == bodies[(messy, "CORRECTION")]["false_clean_original"]
    )
    assert bodies[(messy, "LATE-ACK-AS-P013")]["late_against_selected_due"] is True
    assert bodies[(messy, "CORRECTION")]["historical_false_clean_erased"] is False
    assert bodies[(messy, "FINAL")]["open_exception_ids"] == [EXCEPTION]
    assert bodies[(messy, "FINAL")]["selected_late_count"] == 1
    assert all(
        event.startswith("2027-")
        and available >= event
        and imported.startswith("2026-")
        and body["real_enterprise_code_approved"] is False
        and body["actual_employee_action_or_signature"] is False
        for _, _, content, event, available, imported in rows
        for body in (json.loads(content),)
    )


def test_repacked_approval_claim_still_fails_closed(tmp_path):
    destination = _source(tmp_path)
    _change_receipt(destination, lambda row: row.__setitem__("real_enterprise_code_approved", True))
    with pytest.raises(CompanyStoreError, match="overclaims authority"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_repacked_original_version_tamper_still_fails_closed(tmp_path):
    destination = _source(tmp_path)
    _change_receipt(
        destination,
        lambda row: row["native_originals"][0].__setitem__("sha256", "0" * 64),
    )
    with pytest.raises(CompanyStoreError, match="original-version receipt differs"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)


def test_sidecar_and_existing_destination_fail_closed(tmp_path):
    destination = _source(tmp_path)
    original = (destination / "SOURCE_RECEIPT.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private conduct destination"):
        create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    assert (destination / "SOURCE_RECEIPT.json").read_bytes() == original
    sidecar = destination / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed fictional source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="sidecar"):
        verify(destination, repository=REPOSITORY, private_repository=PRIVATE)
