"""Selected physical-site source is causal, bounded and append-only."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_physical_site_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _created(tmp_path):
    destination = tmp_path / "physical-site"
    source.create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def test_native_selected_history_and_open_exception(tmp_path):
    root = _created(tmp_path)
    receipt = source.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert receipt["native_version_counts"] == {"CLEAN": 13, "MESSY": 18}
    assert receipt["messy_false_close_preserved"]
    assert receipt["messy_unescorted_entry_preserved"]
    assert receipt["messy_historical_exception_status"] == "OPEN"
    assert not receipt["provider_and_enterprise_population_complete"]
    assert not receipt["authored_clauses_satisfied"]
    assert not receipt["audit_task_credit"]
    assert len(receipt["selected_routes"]["A"]) == len(receipt["selected_routes"]["B"]) == 9
    for scenario in source.BRANCHES:
        assert receipt["upstream_native_refs"][scenario]["boise_release"]["sha256"]
        assert receipt["upstream_native_refs"][scenario]["bcm_result"]["sha256"]
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        assert len(rows) == 31
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )
    by_branch = {branch: {} for branch in source.BRANCHES.values()}
    for row in rows:
        body = json.loads(row["content"])
        assert row["imported_at"] < "2027-01-01"
        assert row["event_at"] < row["available_at"]
        assert (
            body["upstream_native_refs_available_at_event"]
            == receipt["upstream_native_refs"][body["scenario"]]
        )
        assert body["actual_personal_data"] is False
        assert body["actual_phi"] is False
        assert body["real_site_action"] is False
        assert body["network_packets"] == 0
        by_branch[row["branch"]][row["record"]] = body
    clean = by_branch[source.BRANCHES["CLEAN"]]
    messy = by_branch[source.BRANCHES["MESSY"]]
    assert clean["BOI-VISIT-01-CLOSE"]["detail"]["entry"] == "ESCORTED"
    assert clean["BADGE-BOI-TECH-01-REVOKE"]["detail"]["controller_state"] == "DISABLED"
    assert clean["SELECTED-OCT-RECON"]["detail"]["decision"] == "SELECTED_PASS"
    assert messy["BADGE-BOI-TECH-01-REVOKE"]["detail"]["controller_state"] == "ACTIVE"
    assert messy["BOI-DOOR-ADVERSE-01"]["detail"]["escort"] == "NONE"
    assert messy["SELECTED-OCT-RECON"]["detail"]["decision"] == "FALSE_CLEAN_PASS"
    assert messy["SOURCE-RECHECK-NOV"]["detail"]["self_review_of_october"] is True
    assert messy["EXC-PHYSICAL-BOISE-01"]["detail"]["status"] == "OPEN"
    assert messy["SELECTED-NOV-RECON"]["detail"]["historical_exception_status"] == "OPEN"
    assert messy["BOI-DOOR-ADVERSE-01"]["event_at"] < messy["SOURCE-RECHECK-NOV"]["event_at"]
    assert messy["SOURCE-RECHECK-NOV"]["event_at"] < messy["BADGE-BOI-TECH-01-CORRECT"]["event_at"]


def test_review_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(source.PRIVATE, source.TRANSITION_REVIEW, "0" * 64)
    with pytest.raises(CompanyStoreError, match="Reviewed private physical-site input differs"):
        source._context(REPOSITORY, PRIVATE)


def test_native_content_tamper_detected_even_with_unchanged_receipt(tmp_path):
    root = _created(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET content=? WHERE record='BOI-DOOR-ADVERSE-01'", (b"{}",))
    with pytest.raises(CompanyStoreError, match="receipt/manifest boundary"):
        source.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_native_sidecar_fails_closed(tmp_path):
    root = _created(tmp_path)
    (root / "company.sqlite3-wal").symlink_to(root / "missing")
    with pytest.raises(CompanyStoreError, match="three-file"):
        source.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
