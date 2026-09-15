"""Substantive checks for reconstructed populations and payroll/operating evidence."""

import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import (
    SOURCE,
    build,
    read,
    validate,
    visible_rows,
    withholding,
    write,
)


@pytest.fixture(scope="module")
def edition():
    return build()


def test_population_reconciles_without_double_counting(edition):
    assert edition["totals"]["legal_employer_counts"] == {
        "SHI": 431,
        "PS": 12,
        "RWH": 128,
        "ARU": 73,
        "BST": 58,
    }
    assert edition["totals"]["named_employees"] == 44
    assert edition["totals"]["nonemployee_directors"] == 7
    assert edition["totals"]["employees"] == 702
    assert edition["totals"]["j2_authorized"] == 237
    assert edition["totals"]["j2_occupied"] == 181
    people = edition["tables"]["people"]
    assert len([p for p in people if p["person_id"] == "P022"]) == 1
    assert next(p for p in people if p["person_id"] == "P022")["legal_employer"] == "PS"
    assert next(p for p in people if p["person_id"] == "P023")["source_person_id"] == "RW-0013"


def test_hand_reperformed_semimonthly_federal_and_california():
    # 120000 annualized minus8600=111400: (5800+53500*.22)/24=732.0833.
    # CA:5000-238=4762:146.74+(4762-3030)*.1023=323.9236.
    tax = withholding("5000", "70000", "CA")
    assert tax["federal_income"] == D("732.08")
    assert tax["state_income"] == D("323.92")
    assert tax["social_or_tier1"] == D("310.00")
    assert tax["medicare"] == D("72.50")
    assert tax["state_employee_contribution"] == D("65.00")
    assert D("5000") - sum(v for k, v in tax.items() if k != "employer_known_taxes") == D("3496.50")


def test_railroad_tier2_and_social_security_caps():
    tax = withholding("5000", "136000", "WY", True)
    assert tax["tier2"] == D("53.90")  # 1100*.049
    assert tax["employer_known_taxes"] == D("526.60")  # 310+72.5+144.1
    tax = withholding("5000", "183000", "WY")
    assert tax["social_or_tier1"] == D("93.00")
    tax = withholding("5000", "198000", "WY")
    assert tax["additional_medicare"] == D("27.00")
    assert tax["social_or_tier1"] == 0


def test_west_virginia_and_pennsylvania():
    assert withholding("5000", "70000", "WV")["state_income"] == D("195.76")
    tax = withholding("5000", "70000", "PA")
    assert tax["state_income"] == D("153.50")
    assert tax["local"] == D("152.17")
    assert tax["state_employee_contribution"] == D("3.50")


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("duplicate", "Duplicate population"),
        ("omit", "Omitted population"),
        ("wrong_entity", "[Ww]rong.*legal"),
        ("wrong_period", "[Ww]rong.*legal"),
        ("pay_twice", "duplicate payroll"),
        ("settlement", "settlement/GL"),
        ("early", "known-on"),
        ("self_review", "Independent approval"),
        ("access_omit", "HR/access"),
        ("leave", "Leave adds"),
        ("unqualified", "Unqualified"),
        ("quantity", "quantity/custody"),
        ("duplicate_gl", "duplicate financial"),
        ("uranium", "quantity/custody"),
    ],
)
def test_adversarial_mutations(edition, mutation, message):
    result = copy.deepcopy(edition["tables"])
    if mutation == "duplicate":
        result["people"].append(result["people"][0])
    elif mutation == "omit":
        result["people"].pop()
    elif mutation == "wrong_entity":
        result["payroll"][0]["legal_entity"] = "ARU"
    elif mutation == "wrong_period":
        result["payroll"][0]["effective_period"] = "2027-01"
    elif mutation == "pay_twice":
        result["payroll"].append(result["payroll"][0])
    elif mutation == "settlement":
        result["settlements"][0]["amount_usd"] = "1.00"
    elif mutation == "early":
        result["people"][0]["available_at"] = "2026-08-31T00:00:00Z"
    elif mutation == "self_review":
        result["approvals"][0]["reviewer_id"] = result["approvals"][0]["preparer_id"]
    elif mutation == "access_omit":
        result["access"].pop()
    elif mutation == "leave":
        result["time"][0]["worked_hours"] = "170"
    elif mutation == "unqualified":
        result["dispatch_assignments"][1]["disposition"] = "RELEASED"
    elif mutation == "quantity":
        result["operating_quantities"][0]["closing_quantity"] = "100"
    elif mutation == "duplicate_gl":
        result["operating_events"][0]["additional_gl_posting"] = True
    elif mutation == "uranium":
        next(r for r in result["operating_quantities"] if r["kind"] == "production")[
            "released_or_accepted_quantity"
        ] = "200"
    with pytest.raises(ValueError, match=message):
        validate(read(SOURCE), result)


def test_knowledge_time_does_not_backdate_newly_authored_history(edition):
    rows = edition["tables"]["people"]
    assert visible_rows(rows, as_of="2026-08-31", known_on="2026-08-31T23:59:59Z") == []
    assert len(visible_rows(rows, as_of="2026-08-31", known_on="2026-09-15T00:00:00Z")) == 702
    with pytest.raises(ValueError, match="timezone"):
        visible_rows(rows, as_of="2026-08-31", known_on="2026-09-15")


def test_stale_derivative_is_rejected(tmp_path, edition):
    write(edition, tmp_path)
    write(edition, tmp_path, check=True)
    (tmp_path / "people.csv").write_text("stale")
    with pytest.raises(ValueError, match="Stale"):
        write(edition, tmp_path, check=True)


def test_source_precision_bridge_is_small_but_not_hidden(edition):
    bridges = edition["tables"]["payroll_source_bridges"]
    known = [r for r in bridges if r["delta_usd"] is not None]
    assert len(known) == 5
    assert all(abs(D(r["delta_usd"])) < D("1.00") for r in known)
    assert any(D(r["delta_usd"]) != 0 for r in known)
    assert len([r for r in bridges if r["delta_usd"] is None]) == 3
