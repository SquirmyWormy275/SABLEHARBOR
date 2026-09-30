"""Exact selected fictional SEC-005 operating population and causal regressions."""

import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_sec005_operated_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")
TRANSITION = (
    PRIVATE_REPOSITORY
    / "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
)


def _created(tmp_path):
    root = tmp_path / "operated"
    source.create(
        root,
        repository=REPOSITORY,
        private_repository=PRIVATE_REPOSITORY,
        transition_root=TRANSITION,
    )
    return root


def test_exact_company_native_population_clocks_and_limits(tmp_path):
    root = _created(tmp_path)
    assert source.verify(
        root,
        repository=REPOSITORY,
        private_repository=PRIVATE_REPOSITORY,
        transition_root=TRANSITION,
    ) == {
        "status": "VERIFIED_FICTIONAL_SELECTED_OPERATION_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 17, "MESSY": 23},
    }
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["selected_service_id"] == "SVC-compute"
    assert len(receipt["selected_asset_ids"]) == 4
    assert len(receipt["selected_logical_interface_ids"]) == 6
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["network_packets_sent"] == receipt["executables_created_or_run"] == 0
    assert receipt["full_year_or_enterprise_population_complete"] is False
    assert receipt["authored_sec005_clause_satisfied"] is False
    assert receipt["audit_task_credit"] is False
    for side in "AB":
        assert len(receipt["selected_route_authority"][side]["task_ids"]) == 5
        assert receipt["selected_route_authority"][side]["authored_unsupported"] == 2
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 40
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        assert all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in ("grants", "collections", "access_events")
        )
    by_branch = {branch: {} for branch in source.BRANCHES.values()}
    for row in rows:
        body = json.loads(row["content"])
        assert row["event_at"] < row["available_at"]
        assert row["imported_at"] < "2027-01-01"
        assert body["actual_network_packets"] == 0
        assert body["actual_executable_bytes_or_runs"] == 0
        assert body["real_deployment"] is False
        assert body["actual_phi"] is False
        assert body["audit_task_credit"] is False
        by_branch[row["branch"]][row["record"]] = body
    clean = by_branch[source.BRANCHES["CLEAN"]]
    messy = by_branch[source.BRANCHES["MESSY"]]
    assert clean["AUTH-SEC005-COMPUTE-2027"]["actor_id"] == "P001"
    assert clean["AUTH-SEC005-COMPUTE-2027"]["delegation"]["grantee_person_id"] == "AS-P007"
    assert set(clean["AUTH-SEC005-COMPUTE-2027"]["upstream_site_release_refs"]) == {"RENO", "BOISE"}
    assert clean["APPLY-BASELINE-01"]["event_at"] < clean["OCT-APPROVED-EGRESS-01"]["event_at"]
    assert len(clean["INVENTORY-SELECTED-01"]["assets"]) == 4
    assert len(clean["INVENTORY-SELECTED-01"]["logical_interfaces"]) == 6
    assert clean["OCT-UNAUTHORIZED-EGRESS-01"]["decision"] == "DENIED_DATA_ONLY"
    assert clean["OCT-UNAPPROVED-EXEC-01"]["decision"] == ("DENIED_UNAPPROVED_MANIFEST_DATA_ONLY")
    assert messy["OCT-UNAUTHORIZED-EGRESS-01"]["decision"] == "WOULD_ALLOW_DATA_ONLY"
    assert messy["OCT-UNAPPROVED-EXEC-01"]["decision"] == (
        "NO_POLICY_DECISION_COVERAGE_NO_EXECUTION"
    )
    assert messy["MONITOR-OCT-01"]["received_probe_record_ids"] == [
        "OCT-APPROVED-EGRESS-01",
        "OCT-UNAUTHORIZED-ADMIN-01",
    ]
    assert "publisher_probe_record_ids" not in messy["MONITOR-OCT-01"]
    assert messy["RECON-OCT-01"]["reviewed_native_selected_inventory"] is False
    assert len(messy["RECON-OCT-01"]["reviewed_asset_ids"]) == 3
    assert len(messy["RECON-OCT-01"]["reviewed_interface_ids"]) == 5
    assert messy["INDEPENDENT-NOV-01"]["late_missing_publisher_ids"] == [
        "OCT-UNAPPROVED-EXEC-01",
        "OCT-UNAUTHORIZED-EGRESS-01",
    ]
    assert messy["RECON-OCT-01"]["recorded_result"] == "RECORDED_PASS_ON_INCOMPLETE_INPUTS"
    assert messy["INDEPENDENT-NOV-01"]["finding_count"] == 2
    assert messy["EXC-SEC005-Q4-01"]["status"] == ("OPEN_HISTORICAL_CAUSE_AND_MONITORING_GAP")
    assert messy["APPROVE-CORRECTION-01"]["event_at"] < messy["CORRECT-BOI-EGRESS-01"]["event_at"]
    assert messy["RECON-NOV-01"]["historical_exception_open"] is True


def test_data_only_evaluators_are_exact_and_fail_closed():
    rules = {"IF-BOI-EGRESS": ["NONPERSONAL-METADATA-SERVICE"]}
    assert source.evaluate_boundary(rules, "IF-BOI-EGRESS", "UNAPPROVED") == ("DENIED_DATA_ONLY")
    assert source.evaluate_boundary(rules, "IF-BOI-EGRESS", "NONPERSONAL-METADATA-SERVICE") == (
        "WOULD_ALLOW_DATA_ONLY"
    )
    with pytest.raises(CompanyStoreError, match="not declared"):
        source.evaluate_boundary(rules, "UNKNOWN", "UNAPPROVED")
    assert source.evaluate_endpoint(["SIM-BOI-OPS-01"], "SIM-BOI-OPS-01") == (
        "DENIED_UNAPPROVED_MANIFEST_DATA_ONLY"
    )
    assert source.evaluate_endpoint([], "SIM-BOI-OPS-01") == (
        "NO_POLICY_DECISION_COVERAGE_NO_EXECUTION"
    )


def test_reviewed_transition_pin_drift_fails_closed(monkeypatch):
    monkeypatch.setitem(source.TRANSITION_PINS, "company.sqlite3", "0" * 64)
    with pytest.raises(CompanyStoreError, match="transition V3 bytes differ"):
        source._context(REPOSITORY, PRIVATE_REPOSITORY, TRANSITION)


def test_dangling_native_sidecar_fails_closed(tmp_path):
    root = _created(tmp_path)
    (root / "company.sqlite3-shm").symlink_to(root / "missing-target")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        source.verify(
            root,
            repository=REPOSITORY,
            private_repository=PRIVATE_REPOSITORY,
            transition_root=TRANSITION,
        )


def test_receipt_exception_count_tamper_fails_closed(tmp_path):
    root = _created(tmp_path)
    path = root / "RECEIPT.json"
    data = json.loads(path.read_text())
    data["open_exception_counts"]["MESSY"] = 0
    path.write_text(json.dumps(data))
    with pytest.raises(CompanyStoreError, match="manifest/receipt"):
        source.verify(
            root,
            repository=REPOSITORY,
            private_repository=PRIVATE_REPOSITORY,
            transition_root=TRANSITION,
        )
