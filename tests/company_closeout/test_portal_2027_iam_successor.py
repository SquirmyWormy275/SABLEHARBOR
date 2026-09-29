"""The selected Q1 payroll service has two grants and an inspectable review miss."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.operations.completed_period import build
from tools.company_closeout.portal_2027_iam_successor import derive, visible_events

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT / "enterprise/operations/source/portal_2027_payroll_release_q1_successor_2026_09_29.json"
)
PREDECESSOR = ROOT / "enterprise/operations/source/portal_2027_payroll_release_q1_2026_09_29.json"
EXPORT = ROOT / "enterprise/operations/portal_2027_iam/payroll_release_q1_v0.2.json"


@pytest.fixture(scope="module")
def inputs():
    source = json.loads(SOURCE.read_text())
    predecessor = json.loads(PREDECESSOR.read_text())
    records = build()
    records["repository_source_commit"] = source["accepted_august_release"]["source_commit"]
    return records, predecessor, source


def test_bounded_population_and_bidirectional_source_traces(inputs):
    ledger = derive(*inputs)
    assert ledger == json.loads(EXPORT.read_text())
    assert ledger["repository_available_at"] is None
    assert ledger["fact_status"] == "MODELED_2027_IN_UNIVERSE_EVENTS_NOT_REAL_DEPLOYMENT"
    assert ledger["service_population"] == {
        "unit": "human_service_role_account",
        "opening_before_2027_grants": 0,
        "opening_source_id": "SH-IAM007-Q1-2027-SELECTED-SERVICE-OPENING",
        "q1_grants": 2,
        "q1_other_jml_events": 0,
        "closing_at_2027_04_01": 2,
        "complete_within_declared_function": True,
        "company_wide_account_denominator": None,
    }
    review = ledger["review_population"]
    assert (
        review["due"],
        review["owner_decision_sources"],
        review["independently_verified"],
    ) == (2, 1, 1)
    assert review["missing_owner_decision"] == 1
    assert review["status"] == "PARTIAL_ONE_MISSING_NOT_CONTROL_PASS"
    assert len(ledger["event_index"]) == len({x["event_id"] for x in ledger["event_index"]}) == 15
    traces = ledger["forward_traces"]
    assert len(traces) == 2
    for trace in traces:
        account = trace["service_account_id"]
        for field in (
            "opening_source_id",
            "hr_event_id",
            "authorization_id",
            "iam_realization_id",
            "review_population_id",
        ):
            assert account in ledger["reverse_trace_index"][trace[field]]
    assert sum(t["review_decision_id"] is None for t in traces) == 1
    assert sum(t["missing_response_id"] is not None for t in traces) == 1
    assert ledger["portal_intake_contract"]["full_company_denominator"] is None
    assert ledger["case_branches"]["A"] == ledger["case_branches"]["B"]


def test_repository_publication_and_case_clocks_are_separate(inputs):
    ledger = derive(*inputs)
    publication = "2026-09-29T06:30:00Z"  # A simulated post-authoring receipt for test only.
    assert (
        visible_events(
            ledger,
            as_of="2027-04-02T00:00:00Z",
            known_on="2027-04-02T00:00:00Z",
            repository_available_at=None,
        )
        == []
    )
    assert (
        visible_events(
            ledger,
            as_of="2027-04-02T00:00:00Z",
            known_on="2026-09-29T06:29:59Z",
            repository_available_at=publication,
        )
        == []
    )
    with pytest.raises(ValueError, match="precedes authoring"):
        visible_events(
            ledger,
            as_of="2027-04-02T00:00:00Z",
            known_on="2027-04-02T00:00:00Z",
            repository_available_at="2026-09-29T06:22:11Z",
        )

    def events(as_of, known_on):
        return {
            row["event_id"]
            for row in visible_events(
                ledger,
                as_of=as_of,
                known_on=known_on,
                repository_available_at=publication,
            )
        }

    assert events("2027-01-01T00:00:00Z", "2027-04-02T00:00:00Z") == {
        "SH-IAM007-Q1-2027-DELEGATE-OWNER",
        "SH-IAM007-Q1-2027-DELEGATE-IMPLEMENTER",
        "SH-IAM007-Q1-2027-DELEGATE-HR",
        "SH-IAM007-Q1-2027-DELEGATE-VALIDATOR",
        "SH-IAM-AUTH-Q1-2027-PREPARE",
        "SH-IAM-AUTH-Q1-2027-APPROVE",
    }
    assert "SH-IAM-REALIZE-Q1-2027-PREPARE" not in events(
        "2027-01-02T00:00:00Z", "2027-01-01T00:09:59Z"
    )
    assert "SH-IAM-REALIZE-Q1-2027-PREPARE" in events(
        "2027-01-02T00:00:00Z", "2027-01-01T00:10:00Z"
    )
    assert "SH-IAM007-Q1-2027-DECISION-PREPARE" not in events(
        "2027-03-29T00:00:00Z", "2027-03-27T16:09:59Z"
    )
    assert "SH-IAM007-Q1-2027-VERIFY-PREPARE" in events(
        "2027-03-29T00:00:00Z", "2027-03-28T12:05:00Z"
    )
    assert "SH-IAM007-Q1-2027-MISSING-APPROVE" not in events(
        "2027-04-02T00:00:00Z", "2027-04-01T01:04:59Z"
    )
    assert "SH-IAM007-Q1-2027-MISSING-APPROVE" in events(
        "2027-04-02T00:00:00Z", "2027-04-01T01:05:00Z"
    )


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r, p, s: r["tables"]["access"].pop(), "people and principals differ"),
        (
            lambda r, p, s: s["scope"]["included_service_account_ids"].append(
                s["scope"]["included_service_account_ids"][0]
            ),
            "Declared service",
        ),
        (
            lambda r, p, s: s["scope"].update(period_end_exclusive="2027-04-02T00:00:00Z"),
            "Declared service",
        ),
        (
            lambda r, p, s: s["opening_state"]["service_account_ids"].append(
                "SH-ESS-PAYROLL-RELEASE-PREPARE-0001"
            ),
            "Selected-service opening",
        ),
        (
            lambda r, p, s: s["role_delegations"][0].update(person_id="SH-EMP-ESS-0001"),
            "Delegated actor",
        ),
        (
            lambda r, p, s: s["hr_role_events"][0].update(approved_by="SH-EMP-ESS-0001"),
            "HR to authorization",
        ),
        (
            lambda r, p, s: s["grant_authorizations"][0].update(right="APPROVE_PAYROLL_BATCH"),
            "HR to authorization",
        ),
        (
            lambda r, p, s: s["iam_realization_events"][0].update(authorization_id="UNSUPPORTED"),
            "HR to authorization",
        ),
        (
            lambda r, p, s: s["iam_realization_events"][0].update(
                case_available_at="2026-09-29T06:30:00Z"
            ),
            "HR/IAM approval",
        ),
        (
            lambda r, p, s: s["review_population"]["service_account_ids"].pop(),
            "Quarterly population",
        ),
        (
            lambda r, p, s: s["review_decisions"][0].update(decided_by="SH-EMP-ESS-0001"),
            "Review decision",
        ),
        (
            lambda r, p, s: s["review_decisions"][0].update(
                case_available_at="2027-04-02T00:00:00Z"
            ),
            "Review evidence after due",
        ),
        (
            lambda r, p, s: s["independent_verifications"][0].update(verified_by="SH-EMP-ESS-0005"),
            "Review decision",
        ),
        (
            lambda r, p, s: s["review_decisions"].append(copy.deepcopy(s["review_decisions"][0])),
            "Duplicate service_account_id",
        ),
        (
            lambda r, p, s: s["missing_decision_response"].update(
                owner_decision_source_id="UNSUPPORTED"
            ),
            "Missing decision",
        ),
        (
            lambda r, p, s: s["case_branches"]["B"].update(company_delta_state="CLEAN"),
            "Private A/B delta",
        ),
        (
            lambda r, p, s: s.update(repository_available_at="2026-09-29T06:22:12Z"),
            "Unaccepted successor",
        ),
        (
            lambda r, p, s: s.update(fact_status="COMPLETED_2027_ACTUAL"),
            "Unaccepted successor",
        ),
    ],
)
def test_unsupported_identity_right_period_population_or_performance_rejected(
    inputs, change, reason
):
    records, predecessor, source = copy.deepcopy(inputs)
    change(records, predecessor, source)
    with pytest.raises(ValueError, match=reason):
        derive(records, predecessor, source)
