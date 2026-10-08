"""Reviewed LEG/DAT native leads preserve the frozen V16 route and P1 gates."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import documentary_283_route_reconciliation_v17 as route
from enterprise.audit_suite.documentary_283_route_reconciliation_v12 import V12ReconciliationError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]
STEM = REPOSITORY / "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01"


@pytest.fixture(scope="module")
def inputs() -> tuple[dict, dict, dict, dict]:
    def load(name: str) -> dict:
        pin = route.PINS[name]
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
        return json.loads(path.read_bytes())

    return load("v16_ledger"), load("leg_receipt"), load("dat_receipt"), load("leg_gap")


@pytest.fixture(scope="module")
def result(inputs: tuple[dict, dict, dict, dict]) -> dict:
    return route._extend(*inputs, route.P1_FREEZE)


def test_all_reviewed_input_bytes_exact_and_corrected_gap_bridge() -> None:
    for pin in route.PINS.values():
        path = (REPOSITORY if pin["scope"] == "repo" else PRIVATE) / pin["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    original_review = json.loads((PRIVATE / route.LEG_REVIEW).read_text())
    correction_review = json.loads((PRIVATE / route.LEG_GAP_REVIEW).read_text())
    assert original_review["corrected_gap_report_sha256"]["JSON"] == (
        route.LEG_PRECORRECTION_GAP_SHA256
    )
    assert correction_review["prior_source_review_sha256"] == route.PINS["leg_review"]["sha256"]
    assert correction_review["tracked_gap_json_sha256"] == route.PINS["leg_gap"]["sha256"]
    assert correction_review["audit_task_credit"] is False


def test_only_18_exact_authored_routes_change_previous_fields(
    inputs: tuple[dict, dict, dict, dict], result: dict
) -> None:
    previous, _, _, gap = inputs
    selected = {row["task_id"] for row in gap["rows_by_side"]["A"] if row["new_overlay_cohort"]}
    assert len(selected) == 16
    selected |= set(route.DAT_TASKS)
    assert len(selected) == 18
    assert len(previous["rows"]) == len(result["rows"]) == 566
    assert result["v16_prefix_sha256"] == route.PINS["v16_ledger"]["sha256"]
    assert result["active_p1_tasks"] == previous["active_p1_tasks"]
    assert result["p1_freeze"] == previous["p1_freeze"]
    for side in "AB":
        assert (
            sum(
                row["v17_reviewed_source_ids"] == []
                for row in result["rows"]
                if row["side"] == side
            )
            == 265
        )
    for old, new in zip(previous["rows"], result["rows"], strict=True):
        is_selected = old["task_id"] in selected
        allowed = {"targeted_integrated_source_ids"} if is_selected else set()
        assert all(new[key] == value for key, value in old.items() if key not in allowed)
        assert new["v17_reviewed_source_ids"] == (
            [route.LEG_SOURCE if old["task_id"] not in route.DAT_TASKS else route.DAT_SOURCE]
            if is_selected
            else []
        )
        assert new["classification"] == old["classification"]
        assert new["current_status"] == "NOT_STARTED"
        assert new["current_conclusion"] == "NOT_RUN"
        assert new["audit_task_credit"] is False


def test_exact_branch_native_refs_and_no_credit_limits(
    inputs: tuple[dict, dict, dict, dict], result: dict
) -> None:
    previous, leg_receipt, dat_receipt, gap = inputs
    refs = route._selected_refs(leg_receipt, dat_receipt, gap, previous)
    for side, scenario, branch, dat_count in (
        ("A", "CLEAN", "LEGOV-CLEAN", 5),
        ("B", "MESSY", "LEGOV-MESSY", 6),
    ):
        rows = [row for row in result["rows"] if row["side"] == side]
        assert len(rows) == 283
        assert result["counts"][side]["targeted_integrated_route_count"] == 201
        assert result["counts"][side]["classifications"] == {
            "DESIGN_CONTEXT_ONLY": 21,
            "SOURCE_CANDIDATE_PARTIAL": 141,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        assert result["counts"][side]["v17_new_classification_promotions"] == 0
        for task_id, exact_refs in refs[side]["leg"].items():
            row = next(row for row in rows if row["task_id"] == task_id)
            assert row["v17_source_record_refs"] == {route.LEG_SOURCE: exact_refs}
            assert {ref["branch"] for ref in exact_refs} == {branch}
            assert len(exact_refs) == (5 if "ACTION-H-LEGAL-STATUS" in task_id else 3)
            assert row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
        for task_id in route.DAT_TASKS:
            row = next(row for row in rows if row["task_id"] == task_id)
            assert row["v17_source_record_refs"] == {route.DAT_SOURCE: refs[side]["dat"]}
            assert len(refs[side]["dat"]) == dat_count
            assert {ref["branch"] for ref in refs[side]["dat"]} == {route.dat.BRANCHES[scenario]}
            assert row["classification"] == "UNSUPPORTED_EXACT_CLAUSE"
    assert leg_receipt["2027_legal_text_verified"] is False
    assert leg_receipt["real_hipaa_applicability"] == "UNDETERMINED"
    assert dat_receipt["actual_requests_or_external_responses"] == 0
    assert dat_receipt["accepted_amendments_or_accounting_completions"] == 0
    assert result["audit_task_credit"] is result["active_pair_mutated"] is False


def test_tampered_gate_gap_and_branch_fail_closed(inputs: tuple[dict, dict, dict, dict]) -> None:
    previous, leg_receipt, dat_receipt, gap = inputs
    changed = deepcopy(previous)
    row = next(row for row in changed["rows"] if row["task_id"] == route.DAT_TASKS[0])
    row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
    with pytest.raises(route.V17ReconciliationError):
        route._extend(changed, leg_receipt, dat_receipt, gap, route.P1_FREEZE)
    changed = deepcopy(gap)
    selected = next(row for row in changed["rows_by_side"]["A"] if row["new_overlay_cohort"])
    selected["new_overlay_status"] = "ROUTED_AND_PROVED"
    with pytest.raises(route.V17ReconciliationError, match="LEG provision candidate"):
        route._selected_refs(leg_receipt, dat_receipt, changed, previous)
    changed = deepcopy(leg_receipt)
    changed["records"]["CLEAN"][0]["branch"] = leg_receipt["branches"]["MESSY"]
    with pytest.raises(route.V17ReconciliationError, match="native branch refs"):
        route._selected_refs(changed, dat_receipt, gap, previous)
    changed = deepcopy(dat_receipt)
    changed["records"]["MESSY"][0]["branch"] = route.dat.BRANCHES["CLEAN"]
    with pytest.raises(route.V17ReconciliationError, match="native branch refs"):
        route._selected_refs(leg_receipt, changed, gap, previous)


def test_disposable_pinned_byte_tamper_fails(tmp_path: Path) -> None:
    path = tmp_path / "copy.json"
    original = (REPOSITORY / route.LEG_GAP).read_bytes()
    path.write_bytes(original)
    pin = {"scope": "private", "path": path.name, "sha256": hashlib.sha256(original).hexdigest()}
    path.chmod(0o600)
    assert route._pin(tmp_path, tmp_path, pin) == path
    path.write_bytes(original + b"\n")
    with pytest.raises(V12ReconciliationError, match="Reviewed input byte or mode differs"):
        route._pin(tmp_path, tmp_path, pin)


def test_generated_bytes_and_full_native_verification(
    result: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert result == json.loads(STEM.with_suffix(".json").read_text())
    assert route.markdown(result) == STEM.with_suffix(".md").read_text()

    def no_recursive_build(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Recursive V16 build is forbidden")

    monkeypatch.setattr(route.prior, "build", no_recursive_build)
    assert route.build(REPOSITORY, PRIVATE) == result
    assert route._p1_inventory(PRIVATE) == route.P1_FREEZE
