"""The same nonpersonal object has separate, uncredited local identity ledgers."""

import copy
import json
import os
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_iam005_local_trace_2027 as trace
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def sealed(tmp_path_factory):
    parent = tmp_path_factory.mktemp("iam005-trace-private")
    os.chmod(parent, 0o700)
    destination = parent / "run-v1"
    trace.create(destination, repository=REPOSITORY, private_repository=PRIVATE)
    return destination


def test_separate_ledgers_share_exact_local_object_and_retain_denials(sealed):
    manifest = trace.verify(sealed, repository=REPOSITORY, private_repository=PRIVATE)
    receipt = json.loads((sealed / "RECEIPT.json").read_text())
    assert manifest["native_version_count"] == 29
    assert receipt["native_version_counts"] == {
        "CLEAN": {"human": 7, "service": 6},
        "MESSY": {"human": 8, "service": 8},
    }
    assert receipt["object_sha256"] == trace.sha(trace._context(REPOSITORY, PRIVATE)["raw"])
    assert receipt["authored_iam005_clause_support"] is False
    assert receipt["audit_task_credit"] is False
    assert receipt["selected_route_authority"]["A"] == receipt["selected_route_authority"]["B"]
    assert receipt["selected_route_authority"]["A"]["authored_clause_count"] == 2
    assert receipt["selected_route_authority"]["A"]["inferred_gate_count"] == 3
    selected = {}
    for ledger in ("human", "service"):
        with sqlite3.connect(sealed / ledger / "company.sqlite3") as db:
            selected[ledger] = {
                (branch, record): (event, available, imported, body)
                for branch, record, event, available, imported, body in db.execute(
                    "SELECT branch,record,event_at,available_at,imported_at,content FROM versions"
                )
            }
        assert all(
            event < available and imported < event
            for event, available, imported, _ in selected[ledger].values()
        )
        for branch in trace.BRANCHES.values():
            raw = selected[ledger][
                branch, trace._context(REPOSITORY, PRIVATE)["spec"]["object"]["id"]
            ][3]
            assert trace.sha(raw) == receipt["object_sha256"]
    human_denial = json.loads(selected["human"]["IAM005-TRACE-MESSY", "READ-EXPIRED-01"][3])
    human_session = json.loads(selected["human"]["IAM005-TRACE-MESSY", "SESSION-01"][3])
    human_read = json.loads(selected["human"]["IAM005-TRACE-MESSY", "READ-01"][3])
    assert human_session["session_id"] == human_read["session_id"]
    assert human_session["host_or_network_session_created"] is False
    service_excess = json.loads(selected["service"]["IAM005-TRACE-MESSY", "READ-EXCESS-01"][3])
    service_stale = json.loads(selected["service"]["IAM005-TRACE-MESSY", "READ-STALE-01"][3])
    assert all(
        x["result"] == "DENIED" and x["read_bytes"] == 0
        for x in (human_denial, service_excess, service_stale)
    )
    assert (
        json.loads(selected["service"]["IAM005-TRACE-MESSY", "SCOPE-CORRECTION-01"][3])[
            "original_excess_request_retained"
        ]
        is True
    )
    for ledger in ("human", "service"):
        late = json.loads(selected[ledger]["IAM005-TRACE-MESSY", "REVIEW-01"][3])
        assert late["review_timely"] is False
        assert late["open_timing_exception_id"]


def test_frozen_iam005_route_and_object_pin_drift_rejected(monkeypatch):
    matrix = json.loads((PRIVATE / trace.ROUTE_AUTHORITY["matrix_path"]).read_text())
    assert len(trace._check_routes(matrix)["A"]["task_ids"]) == 5
    for field, value in (
        ("current_status", "COMPLETE"),
        ("task_credit", True),
        ("authored_test_clause", "weaker substitute"),
    ):
        altered = copy.deepcopy(matrix)
        control = next(
            control
            for family in altered["sides"]["A"]["families"]
            for control in family["controls"]
            if control["control_id"] == "SH-IAM-005"
        )
        control["tasks"][0][field] = value
        with pytest.raises(CompanyStoreError, match="clause/status/credit"):
            trace._check_routes(altered)
    pins = dict(trace.SOURCE_PINS)
    pins[trace.SPEC] = "0" * 64
    monkeypatch.setattr(trace, "SOURCE_PINS", pins)
    with pytest.raises(CompanyStoreError, match="Pinned canon/spec/design bytes"):
        trace._context(REPOSITORY, PRIVATE)


def test_dangling_native_sidecar_fails_closed(sealed, tmp_path):
    copied = tmp_path / "copy"
    copied.mkdir(mode=0o700)
    for ledger in ("human", "service"):
        sub = copied / ledger
        sub.mkdir(mode=0o700)
        (sub / "company.sqlite3").write_bytes((sealed / ledger / "company.sqlite3").read_bytes())
        os.chmod(sub / "company.sqlite3", 0o600)
    for name in ("MANIFEST.json", "RECEIPT.json"):
        (copied / name).write_bytes((sealed / name).read_bytes())
        os.chmod(copied / name, 0o600)
    (copied / "service/company.sqlite3-shm").symlink_to("missing")
    with pytest.raises(CompanyStoreError, match="sidecar"):
        trace.verify(copied, repository=REPOSITORY, private_repository=PRIVATE)
