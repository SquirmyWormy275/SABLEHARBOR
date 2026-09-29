"""The Q1 selected function has a due population, but no performed review."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.operations.completed_period import build
from tools.company_closeout.portal_2027_iam_case import derive_case

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/operations/source/portal_2027_payroll_release_q1_2026_09_29.json"
EXPORT = ROOT / "enterprise/operations/portal_2027_iam/payroll_release_q1_v0.1.json"


@pytest.fixture(scope="module")
def inputs():
    case = json.loads(SOURCE.read_text())
    policy = json.loads(
        (ROOT / "enterprise/ccf/assurance/design_data/control_procedures.json").read_text()
    )
    records = build()
    records["repository_source_commit"] = case["source_commit"]
    return records, case, policy


def test_two_role_due_population_and_unperformed_review(inputs):
    actual = derive_case(*inputs)
    assert actual == json.loads(EXPORT.read_text())
    assert actual["prior_period_bridge"]["unrepresented_jml_count"] is None
    assert actual["source_authored_at"] == "2026-09-29T05:44:16Z"
    assert actual["source_available_at"] is None
    assert actual["repository_available_at"] is None
    assert actual["known_on_state"] == (
        "PENDING_REPOSITORY_ACCEPTANCE_NOT_QUERYABLE_AS_CASE_EVIDENCE"
    )
    assert actual["accepted_august_approval_count"] == 10
    assert len(set(actual["accepted_august_approval_ids"])) == 10
    jml = actual["q1_selected_scope_jml"]
    assert jml["declared_2027_grant_count"] == 2
    assert jml["declared_other_change_count"] == 0
    assert jml["universal_company_jml_count"] is None
    schedule = actual["q1_review_schedule"]
    assert schedule["selected_privileged_role_accounts_due"] == 2
    assert schedule["supplied_owner_decision_sources"] == 0
    assert schedule["due_state_at_authoring"] == "FUTURE_DUE_NOT_RUN"
    assert schedule["actual_q1_performance_conclusion"] is None
    assert actual["case_branches"]["A"] == actual["case_branches"]["B"]


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r, c, p: r["tables"]["approvals"].pop(), "approval population"),
        (
            lambda r, c, p: c["newly_authored_role_grants"][0].update(person_id="SH-EMP-ESS-0003"),
            "Role holder",
        ),
        (
            lambda r, c, p: c["newly_authored_role_grants"][0].update(
                right="APPROVE_PAYROLL_BATCH"
            ),
            "authorization rights",
        ),
        (
            lambda r, c, p: c["newly_authored_role_grants"][0].update(event_status="DEPLOYED"),
            "Role holder",
        ),
        (
            lambda r, c, p: c["prior_period_bridge"].update(
                september_december_complete_company_jml=True
            ),
            "Sep-Dec unknown",
        ),
        (
            lambda r, c, p: c["review_requirement"].update(due_at="2027-04-02T00:00:00Z"),
            "Q1 period",
        ),
        (
            lambda r, c, p: c["review_requirement"]["owner_decision_source_ids"].append(
                "UNSUPPORTED"
            ),
            "Q1 period",
        ),
        (
            lambda r, c, p: c["case_branches"]["B"].update(company_delta_state="NONE"),
            "A/B case delta",
        ),
        (
            lambda r, c, p: c.update(fact_status="COMPLETED_2027_ACTUAL"),
            "authority, temporal",
        ),
        (
            lambda r, c, p: c.update(available_at="2026-09-29T05:44:16Z"),
            "authority, temporal",
        ),
        (
            lambda r, c, p: c.update(repository_available_at="2026-09-29T05:49:21Z"),
            "authority, temporal",
        ),
    ],
)
def test_invented_scope_rights_performance_or_actual_claim_rejected(inputs, change, reason):
    records, case, policy = copy.deepcopy(inputs)
    change(records, case, policy)
    with pytest.raises(ValueError, match=reason):
        derive_case(records, case, policy)
