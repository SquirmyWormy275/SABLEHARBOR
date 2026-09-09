import json
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path

import pytest

from enterprise.business.model import BusinessModel
from enterprise.operations.credit import (
    CreditMixin,
    allocate_treasury,
    start_scenario,
    validate,
)


class Model(CreditMixin, BusinessModel):
    pass


def model():
    m = Model()
    m.operations_inputs = {
        "credit": json.loads((Path(__file__).parents[1] / "source/credit.json").read_text())
    }
    m.scenario, m.case, m.month = "base", m.policy["cases"]["base"], 1
    m.sequence = 0
    m.balances = defaultdict(lambda: defaultdict(D))
    m.invoices, m.payables, m.host_payables, m.lots = [], [], [], []
    m.invoice_ids = set()
    start_scenario(m)
    return m


def finish(m):
    m.tables["invoices"] = m.invoices
    validate(m)
    grouped = defaultdict(D)
    for r in m.tables["journal"]:
        grouped[r["journal_id"]] += D(r["signed_usd"])
    assert not any(grouped.values())


def test_partial_receipt_retains_open_claim_and_final_settlement():
    m = model()
    inv = m.invoice("FF-001-TERM-0", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    assert inv["remaining_usd"] == "40.0000"
    assert inv["collected_usd"] == "60.0000"
    m.month = 3
    m.settle()
    assert inv["remaining_usd"] == "40.0000"
    m.month = 4
    m.settle()
    assert inv["remaining_usd"] == "0.0000"
    finish(m)


def test_dispute_grade_and_resolution_change_the_actual_allowance():
    m = model()
    inv = m.invoice("FF-002-TERM-0", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    m.close()
    assert m.balances["foundry-field"]["BIZ_ALLOWANCE"] == D("-26.25")
    m.month = 5
    m.settle()
    m.close()
    assert inv["credit_state"] == "RESOLVED"
    assert m.balances["foundry-field"]["BIZ_ALLOWANCE"] == 0
    finish(m)


def test_credit_after_writeoff_does_not_refund_uncollected_cash():
    m = model()
    inv = m.invoice("FF-003-TERM-0", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    m.month = 6
    m.settle()
    before = m.balances["foundry-field"]["1000"]
    note = m.issue_credit(inv, 20, "Contract contraction", credit_id="contract-credit")
    assert note["writtenoff_applied_usd"] == "20.0000"
    assert note["refund_usd"] == "0.0000"
    assert m.balances["foundry-field"]["1000"] == before == 25
    m.month = 10
    m.settle()
    assert inv["recovered_usd"] == "10.0000"
    assert inv["collected_usd"] == "35.0000"
    finish(m)


def test_recovery_cannot_resurrect_credited_writeoff():
    m = model()
    inv = m.invoice("FF-003-TERM-0", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    m.month = 6
    m.settle()
    m.issue_credit(inv, 74, "Large contraction")
    m.month = 10
    m.settle()
    assert inv["recovered_usd"] == "1.0000"
    finish(m)


def test_credit_allocates_open_then_written_claim_then_cash():
    m = model()
    inv = m.invoice("FF-003-TERM-0", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    first = m.issue_credit(inv, 10, "Early credit")
    assert first["open_applied_usd"] == "10.0000"
    m.month = 6
    m.settle()
    note = m.issue_credit(inv, 80, "Final credit")
    assert note["writtenoff_applied_usd"] == "65.0000"
    assert note["refund_usd"] == "15.0000"
    finish(m)


def test_deferred_credit_releases_unearned_revenue():
    m = model()
    inv = m.invoice("term", "foundry-field", "customer", 100, deferred=True)
    m.issue_credit(inv, 20, "Unperformed service", deferred=True)
    assert m.balances["foundry-field"]["BIZ_DEFERRED"] == -80
    assert m.balances["foundry-field"]["BIZ_REVENUE"] == 0
    finish(m)


def test_collected_credit_refunds_only_actual_collections():
    m = model()
    inv = m.invoice("term", "foundry-field", "customer", 100)
    m.month = 2
    m.settle()
    note = m.issue_credit(inv, 25, "Earned-service remedy")
    assert note["refund_usd"] == "25.0000"
    assert m.balances["foundry-field"]["1000"] == 75
    finish(m)


@pytest.mark.parametrize("value", [0, -1, 101])
def test_invalid_credit_is_rejected_without_mutation(value):
    m = model()
    inv = m.invoice("term", "foundry-field", "customer", 100)
    before = deepcopy(m.tables)
    with pytest.raises(ValueError):
        m.issue_credit(inv, value, "Invalid")
    assert m.tables == before


def test_duplicate_credit_and_aggregate_overcredit_are_rejected():
    m = model()
    inv = m.invoice("term", "foundry-field", "customer", 100)
    m.issue_credit(inv, 60, "First", credit_id="same")
    with pytest.raises(ValueError, match="Duplicate"):
        m.issue_credit(inv, 10, "Again", credit_id="same")
    with pytest.raises(ValueError, match="exceeds"):
        m.issue_credit(inv, 50, "Too much")


def test_host_requests_follow_receipts_and_default_releases_claim():
    m = model()
    inv = m.invoice("FF-003-TERM-0", "project-cradle", "refiner", 100, host_share="0.20")
    m.month = 2
    m.settle()
    assert m.tables["host_collection_settlements"] == []
    m.month = 3
    m.settle()
    assert inv["host_settled_usd"] == "5.0000"
    m.month = 6
    m.settle()
    assert m.balances["project-cradle"]["BIZ_HOST_AP"] == 0
    m.month = 10
    m.settle()
    assert m.balances["project-cradle"]["BIZ_HOST_AP"] == -2
    m.month = 11
    m.settle()
    assert inv["host_settled_usd"] == "7.0000"
    finish(m)


def test_host_pending_refund_reduces_scheduled_host_payment():
    m = model()
    inv = m.invoice("lot", "project-cradle", "refiner", 100, host_share="0.20")
    m.month = 2
    m.settle()
    m.issue_credit(inv, 25, "Assay correction")
    m.month = 3
    m.settle()
    assert inv["host_settled_usd"] == "15.0000"
    finish(m)


def test_host_paid_refund_is_held_without_fabricating_host_cash():
    m = model()
    inv = m.invoice("lot", "project-cradle", "refiner", 100, host_share="0.20")
    m.month = 2
    m.settle()
    m.month = 3
    m.settle()
    before = deepcopy(inv)
    with pytest.raises(ValueError, match="host clawback"):
        m.issue_credit(inv, 10, "Correction after host payment")
    assert inv == before


def treasury_fixture():
    rows = []

    def row(month, source, account, value, kind="DERIVED_PLANNING", flow="OPERATING"):
        rows.append(
            {
                "scenario": "base",
                "entity": "SHI",
                "unit": "foundry-field",
                "year": 2027,
                "month": month,
                "journal_id": f"j{len(rows)}",
                "line_no": len(rows),
                "source_id": source,
                "source_type": kind,
                "account": account,
                "signed_usd": str(value),
                "cash_flow": flow,
            }
        )

    row(1, "vendor1", "1000", -80)
    row(1, "vendor2", "1000", -40)
    row(1, "CORE-UNPAID-2027-1", "CORE_UNPAID", -50, "UNFUNDED_PAYMENT_DEFERRAL")
    row(2, "CORE-ARREARS-PAID-2027-2", "CORE_UNPAID", 30)
    row(2, "CORE-ARREARS-PAID-2027-2", "1000", -30)
    return {
        "journal_rows": rows,
        "funding_rows": [
            {
                "scenario": "base",
                "year": 2027,
                "month": 1,
                "unpaid_operating_obligations_usd": "50",
                "new_payment_deferral_usd": "50",
                "arrears_paid_usd": "0",
            },
            {
                "scenario": "base",
                "year": 2027,
                "month": 2,
                "unpaid_operating_obligations_usd": "20",
                "new_payment_deferral_usd": "0",
                "arrears_paid_usd": "30",
            },
        ],
    }


def test_treasury_allocates_individual_requests_and_old_arrears_fifo():
    m = model()
    result = treasury_fixture()
    allocation = allocate_treasury(m, result)
    assert allocation["requests"] == 2
    obligations = m.tables["treasury_obligations"]
    assert obligations[0]["funded_usd"] == "80.0000"
    assert obligations[1]["funded_usd"] == "20.0000"
    assert obligations[1]["unpaid_usd"] == "20.0000"
    assert obligations[0]["due_date"] == "2027-01-31"
    assert result == treasury_fixture()


def test_treasury_rejects_unidentified_funding_gap():
    m = model()
    result = treasury_fixture()
    result["journal_rows"][2]["signed_usd"] = "-121"
    with pytest.raises(ValueError, match="eligible requests"):
        allocate_treasury(m, result)


def test_treasury_rejects_source_funding_mismatch():
    m = model()
    result = treasury_fixture()
    result["funding_rows"][1]["unpaid_operating_obligations_usd"] = "19"
    with pytest.raises(ValueError, match="enterprise funding"):
        allocate_treasury(m, result)


def test_validator_detects_tampered_collection_history():
    m = model()
    inv = m.invoice("term", "foundry-field", "customer", 100)
    inv["collected_usd"] = "99.0000"
    m.tables["invoices"] = m.invoices
    with pytest.raises(ValueError, match="reconciliation"):
        validate(m)


def test_treasury_reconciles_real_funding_engine_across_all_three_flows():
    from industrial.planning.enterprise import Books, member_funding

    policy = json.loads(Path("industrial/planning/source/enterprise.json").read_text())
    policy["scenarios"]["downside"]["member_equity_annual_limit_usd"] = 0
    policy["core"]["minimum_cash_usd"] = 0
    policy["core"]["payment_deferral_accounts"] = {
        "OPERATING": "CORE_UNPAID",
        "INVESTING": "BIZ_CAPITAL_UNPAID",
        "FINANCING": "BIZ_DEBT_UNPAID",
    }
    books = Books(
        "downside",
        policy,
        {
            "1000": "asset",
            "3000": "equity",
            "PPE": "asset",
            "PAYROLL": "expense",
            "DEBT": "liability",
            "CORE_UNPAID": "liability",
            "BIZ_CAPITAL_UNPAID": "liability",
            "BIZ_DEBT_UNPAID": "liability",
        },
    )
    for source, account, value, flow in (
        ("payroll", "PAYROLL", 80, "OPERATING"),
        ("equipment", "PPE", 100, "INVESTING"),
        ("CORE-PRINCIPAL", "DEBT", 30, "FINANCING"),
    ):
        books.post(
            "SHI",
            2027,
            1,
            [(account, value), ("1000", -value, flow)],
            source,
            source,
            kind="BUSINESS_DRIVEN_FORECAST",
        )
    funding, used = [], {"core": D(0), "subsidiary": D(0)}
    member_funding(books, 2027, 1, D(0), used, D(0), funding)
    books.post(
        "SHI",
        2027,
        2,
        [("1000", 125, "FINANCING"), ("3000", -125)],
        "explicit-new-cash",
        "declared capital receipt",
    )
    member_funding(books, 2027, 2, D(0), used, D(0), funding)
    m = model()
    original = deepcopy(books.rows)
    allocate_treasury(m, {"journal_rows": books.rows, "funding_rows": funding})
    assert books.rows == original
    obligations = {r["cash_flow"]: r for r in m.tables["treasury_obligations"]}
    assert obligations["OPERATING"]["unpaid_usd"] == "0.0000"
    assert obligations["INVESTING"]["unpaid_usd"] == "55.0000"
    assert obligations["FINANCING"]["unpaid_usd"] == "30.0000"
