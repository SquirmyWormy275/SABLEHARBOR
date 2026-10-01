"""The selected future lab case has a closed population and keeps failures visible."""

import copy
import json
from pathlib import Path

import pytest

from tools.company_closeout.portal_2027_reference_controls import (
    SOURCE,
    case_view,
    derive,
    sha256,
)

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "enterprise/operations/portal_2027_reference_controls/q1_v0.1.json"


@pytest.fixture(scope="module")
def inputs():
    case = json.loads((ROOT / SOURCE).read_text())
    pinned = {}
    for key, pin in case["source_pins"].items():
        path = ROOT / pin["path"]
        assert sha256(path) == pin["sha256"]
        pinned[key] = json.loads(path.read_text())
    accepted_roster = pinned["august_roster"]
    ess = next(g for g in accepted_roster["core_groups"] if g["unit"] == "ess")
    assert ess["occupied"] >= 4
    # The full accepted release is byte-pinned by the CLI. This small test fixture
    # exercises the joins and ledger logic without copying a 62-MB release asset.
    selected = ["SH-EMP-ESS-0003", "SH-EMP-ESS-0004"]
    records = {
        "repository_source_commit": case["accepted_august_release"]["source_commit"],
        "tables": {
            "people": [{"person_id": p, "legal_employer": "SHI", "unit": "ess"} for p in selected],
            "access": [{"person_id": p} for p in selected],
        },
    }
    receipt = {
        "status": "ACCEPTED_SCOPED_EDITION",
        "source_commit": case["accepted_august_release"]["source_commit"],
    }
    return case, pinned, records, receipt


def derive_fixture(inputs):
    case, pinned, records, receipt = copy.deepcopy(inputs)
    return derive(
        records,
        receipt,
        case,
        pinned["common_boundary"],
        pinned["ccf_procedures"],
    )


def test_exact_export_and_complete_selected_population(inputs):
    ledger = derive_fixture(inputs)
    assert ledger == json.loads(EXPORT.read_text())
    assert ledger["totals"] == {
        "due": 9,
        "observed": 7,
        "success": 5,
        "failed": 2,
        "missing": 2,
    }
    assert {r["control_id"]: r["due"] for r in ledger["per_control"]} == {
        "SH-IAM-006": 2,
        "SH-BCM-002": 3,
        "SH-BCM-003": 1,
        "SH-IAM-005": 1,
        "SH-REC-004": 2,
    }
    assert ledger["company_wide_2027_due_count"] is None
    assert ledger["repository_available_at"] is None
    assert ledger["repository_acceptance_at"] is None
    assert ledger["scope"]["real_deployment"] is False
    assert ledger["case_branches"]["A"] == ledger["case_branches"]["B"]
    assert len(ledger["inventory"]["nonhuman_accounts"]) == 1
    assert len(ledger["inventory"]["privileged_grants"]) == 1
    assert len(ledger["inventory"]["copies"]) == 2
    assert len(ledger["exercise_briefings"]) == 2
    assert ledger["authorization"]["approved_at"] < ledger["inventory"]["modeled_opened_at"]
    assert all(r["corporate_control_effectiveness"] is None for r in ledger["per_control"])


def test_original_failures_misses_and_post_cutoff_response_remain_separate(inputs):
    ledger = derive_fixture(inputs)
    by_id = {
        r["due_id"].rsplit("-", 2)[-2] + "-" + r["due_id"].rsplit("-", 1)[-1]: r
        for r in ledger["due_rows"]
    }
    assert by_id["BKP-02"]["status_at_case_cutoff"] == "MISSING"
    assert by_id["REST-01"]["status_at_case_cutoff"] == "FAIL"
    assert by_id["DISP-BACKUP"]["status_at_case_cutoff"] == "FAIL"
    assert by_id["PRIV-REVIEW"]["status_at_case_cutoff"] == "MISSING"
    assert by_id["PRIV-REVIEW"]["exception_ticket_ids_at_case_cutoff"] == []
    assert len(ledger["remediation_events"]) == 5
    assert any(
        e["event_at"] > ledger["period"]["case_cutoff"] for e in ledger["remediation_events"]
    )


def test_known_on_preview_never_promotes_future_or_pending_source(inputs):
    ledger = derive_fixture(inputs)
    with pytest.raises(ValueError, match="not accepted"):
        case_view(ledger, as_of="2027-04-03T00:00:00Z", known_on="2027-04-03T00:00:00Z")
    before_plan = case_view(
        ledger,
        as_of="2027-04-03T00:00:00Z",
        known_on="2027-01-01T00:14:00Z",
        allow_provisional=True,
    )
    assert before_plan["due_ids"] == before_plan["visible_event_ids"] == []
    q1 = case_view(
        ledger,
        as_of="2027-04-01T00:00:00Z",
        known_on="2027-04-01T00:00:00Z",
        allow_provisional=True,
    )
    assert len(q1["due_ids"]) == 9
    assert "SH-REFCTRL-EV-PRIV-REVIEW-LATE" not in q1["visible_event_ids"]
    assert "SH-REFCTRL-EV-REST-01" in q1["visible_event_ids"]
    assert "SH-REFCTRL-EV-REST-01-RETEST" in q1["visible_event_ids"]


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (
            lambda c, p, r, x: c.update(repository_available_at="2026-09-29T00:00:00Z"),
            "availability",
        ),
        (lambda c, p, r, x: c["scope"].update(real_deployment=True), "deployed"),
        (lambda c, p, r, x: c["branch_inputs"]["B"].update(company_delta_state="PASS"), "A/B"),
        (lambda c, p, r, x: c["schedule"].pop(), "due occurrences"),
        (
            lambda c, p, r, x: c["schedule"].append(copy.deepcopy(c["schedule"][0])),
            "Duplicate due_id",
        ),
        (
            lambda c, p, r, x: c["performed_events"][0].update(
                fictional_available_at="2027-01-09T00:00:00Z"
            ),
            "chronology",
        ),
        (lambda c, p, r, x: c["performed_events"][2].update(result="SUCCESS"), "restore failure"),
        (lambda c, p, r, x: c["performed_events"][5].update(result="SUCCESS"), "disposal failure"),
        (
            lambda c, p, r, x: c["performed_events"][0].update(actor_person_id="SH-EMP-ESS-0004"),
            "actor",
        ),
        (
            lambda c, p, r, x: c["remediation_events"][0].update(event_at="2027-01-12T09:00:00Z"),
            "Follow-up",
        ),
        (lambda c, p, r, x: c["exception_tickets"].pop(), "exception population"),
        (
            lambda c, p, r, x: c["exception_tickets"][1].update(
                fictional_available_at="2027-01-19T00:00:00Z"
            ),
            "Exception/disposition",
        ),
        (
            lambda c, p, r, x: c["local_authorization"].update(approved_by="SH-EMP-ESS-0003"),
            "reviewer separation",
        ),
        (lambda c, p, r, x: c["local_authorization"].pop("approved_at"), "Local authorization"),
        (
            lambda c, p, r, x: c["local_authorization"].update(approved_at="2027-01-01T00:30:00Z"),
            "Local authorization",
        ),
        (lambda c, p, r, x: c["exercise_briefings"].pop(), "briefing population"),
        (lambda c, p, r, x: r["tables"]["people"].pop(), "accepted SHI roster"),
        (lambda c, p, r, x: x.update(status="DRAFT"), "Source edition"),
    ],
)
def test_false_population_or_status_rejected(inputs, mutate, reason):
    case, pinned, records, receipt = copy.deepcopy(inputs)
    mutate(case, pinned, records, receipt)
    with pytest.raises(ValueError, match=reason):
        derive(
            records,
            receipt,
            case,
            pinned["common_boundary"],
            pinned["ccf_procedures"],
        )
