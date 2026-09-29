"""A design boundary must not silently become a 2027 operating calendar."""

import copy
import json
from pathlib import Path

import pytest

from tools.company_closeout.portal_2027_common_boundary import SOURCE, derive, load, sha256

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "enterprise/operations/portal_2027_common_boundary/opening_v0.1.json"


@pytest.fixture(scope="module")
def inputs():
    source = json.loads((ROOT / SOURCE).read_text())
    original = {}
    for key, pin in source["source_pins"].items():
        path = ROOT / pin["path"]
        assert sha256(path) == pin["sha256"]
        if path.suffix == ".json":
            original[key] = json.loads(path.read_text())
    return source, original


def test_exact_export_and_boundary():
    # Loading source bytes and pins is separate from the acceptance of future operations.
    result = load(ROOT)
    assert result == json.loads(EXPORT.read_text())
    assert result["boundary"]["legal_entity"] == {
        "id": "SHI",
        "legal_name": "Sable Harbor, LLC",
        "jurisdiction": "Delaware",
        "legal_form": "LLC",
        "headquarters": "Sacramento, California",
    }
    assert len(result["boundary"]["selected_service_designs"]) == 3
    assert len(result["boundary"]["selected_site_designs"]) == 3
    assert all(
        site["operating_at_2027_opening"] is None
        for site in result["boundary"]["selected_site_designs"]
    )
    assert all(
        site["operating_at_2026_source"] is False
        for site in result["boundary"]["selected_site_designs"]
    )
    assert (
        result["known_on_state"]
        == "PENDING_REPOSITORY_ACCEPTANCE_NOT_QUERYABLE_AS_COMPANY_EVIDENCE"
    )


def test_five_conditional_rules_have_no_invented_due_or_performance():
    result = load(ROOT)
    calendar = result["calendar"]
    assert len(calendar["conditional_rules"]) == 5
    assert {c for r in calendar["conditional_rules"] for c in r["control_ids"]} == {
        "SH-IAM-005",
        "SH-IAM-006",
        "SH-BCM-002",
        "SH-BCM-003",
        "SH-REC-004",
    }
    assert all(
        calendar[k] is None
        for k in ("company_due_count", "company_observed_count", "company_missing_count")
    )
    assert calendar["supplied_2027_company_performance_source_ids"] == []
    assert all(
        all(
            row[k] is None
            for k in ("company_due_count", "company_observed_count", "company_missing_count")
        )
        for row in calendar["conditional_rules"]
    )
    assert result["case_branches"]["A"] == result["case_branches"]["B"]


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (
            lambda s, i: s.update(repository_available_at="2026-09-29T06:06:27Z"),
            "acceptance boundary",
        ),
        (lambda s, i: s.update(authored_at="2028-01-01T00:00:00Z"), "authored after"),
        (
            lambda s, i: s["boundary"].update(confirmed_2027_operating_systems=1),
            "inventory promoted",
        ),
        (lambda s, i: s["calendar"].update(company_due_count=26), "due or performance"),
        (lambda s, i: s["calendar"].update(company_missing_count=0), "due or performance"),
        (
            lambda s, i: s["calendar"]["duty_rules"][0].update(specific_due_dates_state="KNOWN"),
            "due calendar",
        ),
        (lambda s, i: s["case_branches"]["B"].update(company_delta_state="NO_DIFFERENCE"), "A/B"),
        (
            lambda s, i: i["runtime_sites"]["sites"][0].update(contract_executed=True),
            "contracted or operating",
        ),
        (
            lambda s, i: i["ccf_procedures"].remove(
                next(r for r in i["ccf_procedures"] if r["control_id"] == "SH-IAM-005")
            ),
            "Required CCF procedure",
        ),
        (lambda s, i: s["boundary"].update(legal_entity_id="SHIH"), "legal entity"),
    ],
)
def test_false_activation_population_or_calendar_rejected(inputs, mutate, reason):
    source, original = copy.deepcopy(inputs)
    mutate(source, original)
    with pytest.raises(ValueError, match=reason):
        derive(source, original, sha256(ROOT / SOURCE))
