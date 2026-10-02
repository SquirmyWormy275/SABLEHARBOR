"""Task-specific custody preserves actual ordinary-source B01 calculations."""

from copy import deepcopy

import pytest
import test_source_identity_methods as identity_tests
import test_source_workforce_methods as workforce_tests

from enterprise.audit_suite import source_workforce_efficient_methods as efficient
from enterprise.audit_suite import source_workforce_methods as accepted
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.store import digest


@pytest.fixture(scope="module")
def originals(tmp_path_factory):
    return identity_tests.build_originals(tmp_path_factory, workforce_tests.author_neutral_source)


def test_all52_fresh_results_failures_and_contracts_are_unchanged(originals):
    records, clock = originals["records"], originals["as_of"]
    before = accepted.inspections(records, as_of=clock)
    after = efficient.inspections(records, as_of=clock)
    assert len(after) == 52 and efficient.task_contracts() == accepted.task_contracts()
    for old, new in zip(before, after, strict=True):
        assert {k: v for k, v in old.items() if k not in {"observations", "artifact_ids"}} == {
            k: v for k, v in new.items() if k not in {"observations", "artifact_ids"}
        }
        assert new["observations"] and new["artifact_ids"]
        assert {e["artifact_id"] for o in new["observations"] for e in o["evidence"]} == set(
            new["artifact_ids"]
        )
        assert all(len(o["id"]) <= 128 and len(o["evidence"]) <= 20 for o in new["observations"])
        assert all(
            o["facts"]["exact_task_result_sha256"] == digest(new["result"])
            for o in new["observations"]
        )


def test_new22_cite_method_originals_instead_of_unrelated_person_documents(originals):
    rows = {r["artifact_id"]: r for r in originals["records"]}
    tasks = {
        t["task_id"]: t
        for t in efficient.inspections(originals["records"], as_of=originals["as_of"])
    }
    eth = tasks["TASK-SH-ETH-001-corporate-TOE"]
    assert {rows[i]["logical_family"] for i in eth["artifact_ids"]} == {"eth001conduct"}
    assert eth["result"]["performed_attributes"][1]["facts"]["historical_late_ids"]
    sanctions = tasks["TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS"]
    assert {rows[i]["logical_family"] for i in sanctions["artifact_ids"]} == {"supplementalops"}
    assert sanctions["result"]["performed_attributes"][0]["facts"]["decision_delay_seconds"] > 0
    physical = tasks["TASK-SH-IAM-002-corporate-CHECK-SOC2:CC6.4"]
    assert {rows[i]["logical_family"] for i in physical["artifact_ids"]} == {"physicalsite"}
    assert physical["disposition"]["conclusion"] == "FAIL"
    assert all(
        "selected_document" not in o["facts"] for t in tasks.values() for o in t["observations"]
    )


def test_actual_account_versions_permission_bytes_monthly_and_quarter_dependencies_remain(
    originals,
):
    rows = originals["records"]
    tasks = {t["task_id"]: t for t in efficient.inspections(rows, as_of=originals["as_of"])}
    permission = tasks["TASK-SH-IAM-004-corporate-TOE"]
    required = {
        r["artifact_id"]
        for r in rows
        if r["logical_family"] == "person-access-history"
        and (
            r["logical_system"].startswith("account_")
            or r["logical_system"] in {"permission_activity", "workspace_object"}
        )
    }
    assert required <= set(permission["artifact_ids"])
    assert (
        len(
            permission["result"]["company_workforce_access"]["selected_attributes"][
                "permission_tests"
            ]
        )
        == 3
    )
    quarter = tasks["TASK-SH-IAM-007-corporate-TOE"]
    roles = {r["logical_system"] for r in rows if r["artifact_id"] in quarter["artifact_ids"]}
    assert {
        "denominator_snapshot",
        "periodic_review_population",
        "periodic_review_decisions",
        "account_application",
    } <= roles
    assert all(
        r["artifact_id"] not in permission["artifact_ids"]
        for r in rows
        if r["logical_system"] == "meeting_note"
    )


def test_unrelated_inputs_are_still_strictly_parsed_and_cached_results_ignored(originals):
    bad = deepcopy(originals["records"])
    note = next(r for r in bad if r["logical_system"] == "meeting_note")
    note["receipt"]["content_bytes"] = True
    with pytest.raises(ProcedureError, match="receipt"):
        efficient.inspections(bad, as_of=originals["as_of"])
    cached = deepcopy(originals["records"])
    for row in cached:
        row["document"] = {"fake_pass": True}
        row["old_audit_result"] = {"conclusion": "PASS"}
    assert efficient.inspections(cached, as_of=originals["as_of"]) == efficient.inspections(
        originals["records"], as_of=originals["as_of"]
    )


def test_missing_family_preserves_specific_limits_without_citing_unrelated_workforce(originals):
    rows = [r for r in originals["records"] if r["logical_family"] != "training-history"]
    before = {t["task_id"]: t for t in accepted.inspections(rows, as_of=originals["as_of"])}
    after = {t["task_id"]: t for t in efficient.inspections(rows, as_of=originals["as_of"])}
    name = "TASK-SH-TRN-002-corporate-TOE"
    assert after[name]["result"] == before[name]["result"]
    assert after[name]["disposition"] == before[name]["disposition"]
    assert after[name]["result"]["missing_selected_inputs"] == ["training/training_assignments"]
    assert all(o["facts"]["input_boundary_witness_only"] for o in after[name]["observations"])
