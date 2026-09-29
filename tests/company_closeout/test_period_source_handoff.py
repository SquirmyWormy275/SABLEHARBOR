"""Selected source-population handoff rejects false completeness claims."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.operations.completed_period import SOURCE, build, read
from tools.company_closeout.period_source_handoff import derive


@pytest.fixture(scope="module")
def sources():
    return (
        build(),
        read(SOURCE),
        json.loads(Path("enterprise/ccf/company_closeout/obligation_census.json").read_text()),
    )


def test_declared_source_populations_and_unknowns(sources):
    p = derive(*sources)
    assert p["payroll"]["due"] == p["payroll"]["observed"] == 1404
    assert p["contract_delivery_invoice"]["observed_invoice"] == 92
    assert p["contract_delivery_invoice"]["modeled_unpaid_invoices"] == 33
    assert p["selected_operating_chains"]["stage_records"] == 52
    assert p["selected_operating_chains"]["full_month_transaction_denominator"] is None
    assert p["august_rail_event_review"]["missing_evidence"] == 1
    assert p["red_wash_permit_conditions"]["due_occurrences"] is None


def test_current_activity_population_ids_match_independent_export(sources):
    activity = json.loads(
        Path("enterprise/ccf/company_closeout/current_activity_successor.json").read_text()
    )
    for table, declared in activity["populations"].items():
        actual = {row[declared["primary_key"]] for row in sources[0]["tables"][table]}
        assert declared["count"] == len(actual)
        assert set(declared["ids"]) == actual


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda t: t["payroll"].append(copy.deepcopy(t["payroll"][0])), "payroll occurrence"),
        (lambda t: t["settlements"].pop(), "settlement population"),
        (lambda t: t["current_invoices"].pop(), "contract population"),
        (
            lambda t: next(
                r for r in t["current_receipts"] if r["state"] == "MODELED_UNPAID"
            ).update(cash_usd="1.00"),
            "Unpaid invoice",
        ),
    ],
)
def test_false_completion_is_rejected(sources, change, reason):
    records = copy.deepcopy(sources[0])
    change(records["tables"])
    with pytest.raises(ValueError, match=reason):
        derive(records, sources[1], sources[2])


def test_unknown_permit_due_is_not_silently_filled(sources):
    obligations = copy.deepcopy(sources[2])
    next(r for r in obligations["records"] if r["id"] == "RW-PER-001")["expected_occurrences"] = 1
    with pytest.raises(ValueError, match="Permit cadence"):
        derive(sources[0], sources[1], obligations)
