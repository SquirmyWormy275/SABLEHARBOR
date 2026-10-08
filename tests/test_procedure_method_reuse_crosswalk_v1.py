"""Method-only reuse and frozen-pair invariants."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from enterprise.audit_suite import procedure_method_reuse_crosswalk_v1 as crosswalk

REPO = Path(__file__).resolve().parents[1]
PRIVATE = Path(os.environ.get("SABLEHARBOR_PRIVATE_ROOT", REPO))


@pytest.fixture(scope="module")
def inputs():
    if not (PRIVATE / crosswalk.PINS["old_packet"][1]).exists():
        pytest.skip("Private reviewed packet is not mounted")
    packet = json.loads(crosswalk._read_pinned(REPO, PRIVATE, "old_packet"))
    route = json.loads(crosswalk._read_pinned(REPO, PRIVATE, "route_ledger"))
    tasks = crosswalk._p1_tasks(PRIVATE / crosswalk.PINS["p1_a_db"][1])
    old = [r for r in packet["rows"] if r["profile"] == "full-integrated-a-v1"]
    routes = [r for r in route["rows"] if r["side"] == "A"]
    return old, tasks, routes


def test_real_pinned_crosswalk_is_method_only():
    if not (PRIVATE / crosswalk.PINS["old_packet"][1]).exists():
        pytest.skip("Private reviewed packet is not mounted")
    report = crosswalk.build(REPO, PRIVATE)
    assert len(report["rows"]) == 818
    assert report["p1_freeze"] == crosswalk.P1_FREEZE
    assert report["audit_task_credit"] is False
    assert report["fresh_pair_created"] is False
    assert report["audit_write"] is False
    assert report["instructor_key_migrated"] is False
    for side, failures in (("A", 2), ("B", 60)):
        counts = report["summary"][side]
        assert counts["prior_status"] == {"COMPLETE": 92, "IN_PROGRESS": 182, "NOT_STARTED": 135}
        assert counts["prior_conclusion"] == {
            "FAIL": failures,
            "LIMITATION": 274 - failures,
            "NOT_RUN": 135,
        }
        assert counts["reuse_class"] == {
            "AUTHORED_METHOD_CANDIDATE": 407,
            "SCOPE_REVIEW_REQUIRED": 2,
        }
        assert (
            counts["authored_method_rows"],
            counts["workpaper_links"],
            counts["sample_links"],
        ) == (407, 275, 70)
        assert counts["p1_unrun"] == 409
        assert counts["scope_drift_task_ids"] == sorted(crosswalk.KNOWN_SCOPE_DRIFT)
    forbidden = {
        "evidence_ids",
        "evidence",
        "sample_result",
        "workpaper_conclusion",
        "key",
        "grade",
    }
    assert not forbidden.intersection(report["rows"][0])
    assert all(row["task_credit"] is False for row in report["rows"])


@pytest.mark.parametrize("change", ["task_id", "scope", "status", "test"])
def test_identity_scope_and_credit_drift_rejected(inputs, change):
    old, tasks, routes = copy.deepcopy(inputs)
    if change == "task_id":
        tasks[0]["id"] += "-DRIFT"
    elif change == "scope":
        tasks[0]["scope"]["period_end"] = "2028-01-01"
    elif change == "status":
        tasks[0]["status"] = "COMPLETE"
    else:
        tasks[0]["test"] += " altered"
    with pytest.raises(crosswalk.CrosswalkError):
        crosswalk._compare_side(old, tasks, routes, "A")


def test_pinned_packet_tamper_rejected(tmp_path):
    source = PRIVATE / crosswalk.PINS["old_review"][1]
    if not source.exists():
        pytest.skip("Private independent review is not mounted")
    relative = Path(crosswalk.PINS["old_review"][1])
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes() + b" ")
    target.chmod(0o600)
    with pytest.raises(crosswalk.CrosswalkError, match="pin differs"):
        crosswalk._read_pinned(REPO, tmp_path, "old_review")
