"""Research gate, recovery conservation and industrial allocation regressions."""

import copy
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

import pytest

from enterprise.business.model import BusinessModel
from enterprise.business.validation import business
from enterprise.operations.research import (
    ResearchMixin,
    build_industrial_detail,
    start_scenario,
    validate,
)
from industrial.planning.operating_model import calculate
from industrial.planning.transactions import procurement_costs, procurement_documents


def source():
    return json.loads((Path(__file__).parents[1] / "source/research.json").read_text())


class ResearchModel(ResearchMixin, BusinessModel):
    def __init__(self, research=None):
        super().__init__()
        self.operations_inputs = {"research": research or source()}


@pytest.fixture(scope="module")
def model():
    return ResearchModel().build()


def test_research_and_recovery_journals_reconcile(model):
    assert business(model)["business_journals"] > 10000
    checks = validate(model)
    assert checks["research_attempts"] == 36
    assert checks["assay_runs"] == 1080
    assert checks["quarantined_lots"] == 18


def test_reusable_equipment_and_initial_research_unchanged(model):
    baseline = BusinessModel().build()
    assert model.tables["asset_rollforward"] == baseline.tables["asset_rollforward"]
    ids = {p["project_id"] for p in baseline.inputs["projects"]}
    previous = [
        r
        for r in baseline.tables["events"]
        if r["kind"] == "EXPERIMENT_GATE" and r["source_id"] in ids
    ]
    current = [
        r
        for r in model.tables["events"]
        if r["kind"] == "EXPERIMENT_GATE" and r["source_id"] in ids
    ]
    assert current == previous


def test_failed_attempts_survive_independent_corrected_replicates(model):
    for scenario in ("base", "downside", "expansion"):
        attempts = [r for r in model.tables["research_attempts"] if r["scenario"] == scenario]
        assert all(r["result"] == "FAIL" for r in attempts if r["attempt_number"] == 1)
        assert sum(r["result"] == "PASS" for r in attempts) == 5
        stopped = [
            r
            for r in model.tables["research_gate_evidence"]
            if r["scenario"] == scenario and r["decision"] == "STOP"
        ]
        assert len(stopped) == 1
        assert not stopped[0]["qualified"]


def test_materials_budget_hold_blocks_qualification_and_spending():
    inputs = source()
    inputs["follow_on_phases"][0]["materials_budget_usd"] = 10000
    m = ResearchModel(inputs).build()
    rows = [
        r for r in m.tables["research_phase_forecasts"] if r["phase_id"] == "WIL-RF-RETEST-2027"
    ]
    assert all(D(r["materials_incurred_usd"]) <= 10000 for r in rows)
    gates = [r for r in m.tables["research_gate_evidence"] if r["phase_id"] == "WIL-RF-RETEST-2027"]
    assert all(r["decision"] == "STOP" and not r["qualified"] for r in gates)
    validate(m)


def test_rejected_lots_never_generate_sales_or_host_claims(model):
    rejected = [r for r in model.tables["recovery_lots"] if r["status"] == "QUARANTINED_REJECTED"]
    assert rejected
    for lot in rejected:
        assert D(lot["cost_usd"]) == 0
        assert not any(lot["lot_id"] in i["source_id"] for i in model.tables["invoices"])
        assert not any(
            lot["lot_id"] == e["source_id"] and e["kind"] == "DOWNSTREAM_ACCEPTANCE"
            for e in model.tables["events"]
        )


def test_hard_bypass_has_no_capture_or_genealogy(model):
    rows = [r for r in model.tables["recovery_run_assays"] if r["bypass"]]
    assert len(rows) == 27
    for row in rows:
        assert D(row["feed_quantity"]) == D(row["contained_kg"]) == D(row["recovered_kg"]) == 0
        assert not any(g["lot_id"] == row["lot_id"] for g in model.tables["recovery_genealogy"])


@pytest.mark.parametrize(
    "table,field,value,message",
    [
        ("research_attempts", "score", "0.99", "digest"),
        ("recovery_run_assays", "recovered_kg", "999999", "digest"),
        ("recovery_genealogy", "quantity", "999999", "mass"),
    ],
)
def test_evidence_tampering_is_detected(model, table, field, value, message):
    damaged = copy.copy(model)
    damaged.tables = {k: v for k, v in model.tables.items()}
    damaged.tables[table] = copy.deepcopy(model.tables[table])
    index = next(
        (i for i, r in enumerate(damaged.tables[table]) if r.get("edge_type") == "CAPTURE_MERGE"), 0
    )
    damaged.tables[table][index][field] = value
    with pytest.raises(ValueError, match=message):
        validate(damaged)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r["follow_on_phases"][0].update(maintenance_owner=""), "receiver"),
        (lambda r: r["follow_on_phases"][0].update(gate_month=61), "bounded"),
        (lambda r: r["assay"].update(run_fractions=["0.5", "0.4"]), "preserve"),
    ],
)
def test_bad_source_cannot_authorize_work(mutation, match):
    inputs = source()
    mutation(inputs)
    with pytest.raises(ValueError, match=match):
        start_scenario(ResearchModel(inputs))


def industrial_fixture():
    op = calculate()[0]
    tables = procurement_documents(procurement_costs([op]))
    tables["service_manifests"], tables["sales_invoices"] = [], []
    for segment, row in op["segments"].items():
        invoice = f"INV-{segment}"
        tables["sales_invoices"].append(
            {"scenario": "base", "invoice_id": invoice, "amount_usd": 100001}
        )
        tables["service_manifests"].append(
            {
                "scenario": "base",
                "year": 2027,
                "month": 1,
                "segment": segment,
                "service_manifest_id": f"MANIFEST-{segment}",
                "invoice_id": invoice,
                "source_id": f"SALE-{segment}",
                "contract_id": f"CONTRACT-{segment}",
                "customer_id": f"CUSTOMER-{segment}",
                "allocated_realized_units": str(row["served_units"]),
                "unit": row["unit"],
                "revenue_usd": 100001,
            }
        )
    m = SimpleNamespace(operations_inputs={"research": source()}, tables=defaultdict(list))
    return m, [op], tables


def test_service_allocations_exactly_preserve_invoice_and_monthly_quantity():
    m, ops, tables = industrial_fixture()
    result = build_industrial_detail(m, ops, tables)
    assert result["service_allocations"] > 1000
    for segment in ops[0]["segments"]:
        details = [r for r in m.tables["industrial_service_detail"] if r["segment"] == segment]
        assert sum(D(r["revenue_usd"]) for r in details) == 100001
        assert sum(D(r["quantity"]) for r in details) == ops[0]["segments"][segment]["served_units"]
        assert (
            sum(D(r["quantity"]) for r in details if r["provider"] == "OWNED")
            == ops[0]["segments"][segment]["owned_served_units"]
        )
        assert all(r["service_date"].startswith("2027-01-") for r in details)
        if segment in {"BST", "TRUCKING"}:
            assert all(D(r["quantity"]) == int(D(r["quantity"])) for r in details)


def test_infeasible_equipment_and_crew_capacity_is_visible():
    m, ops, tables = industrial_fixture()
    ops[0]["capacity"]["truck_driver_hours"] = 1
    result = build_industrial_detail(m, ops, tables)
    assert result["infeasible_owned_shift_allocations"] > 0
    rows = [r for r in m.tables["industrial_shift_capacity"] if r["segment"] == "TRUCKING"]
    assert all(r["capacity_state"] == "INFEASIBLE_CAPACITY" for r in rows)
    assert all(D(r["over_capacity_hours"]) > 0 for r in rows)


def test_source_invoice_mismatch_is_rejected():
    m, ops, tables = industrial_fixture()
    tables["sales_invoices"][0]["amount_usd"] += 1
    with pytest.raises(ValueError, match="invoice"):
        build_industrial_detail(m, ops, tables)


def test_maintenance_ties_supplier_cost_and_is_deducted_from_daily_capacity():
    m, ops, tables = industrial_fixture()
    build_industrial_detail(m, ops, tables)
    for work in tables["work_orders"]:
        jobs = [
            r
            for r in m.tables["industrial_maintenance_jobs"]
            if r["work_order_id"] == work["work_order_id"]
        ]
        assert sum(D(r["expense_usd"]) for r in jobs) == work["expense_usd"]
    assert any(
        D(r["maintenance_downtime_hours"]) > 0 for r in m.tables["industrial_shift_capacity"]
    )


def test_mine_maintenance_excludes_cash_payments_and_preserves_all_production_cost():
    m, ops, tables = industrial_fixture()
    common = {
        "scenario": "base",
        "year": 2027,
        "month": 1,
        "source_id": "MINE-PRODUCTION-base-202701",
    }
    journal = [
        dict(common, source_type="PRODUCTION_COST", signed_usd=100000),
        dict(common, source_type="PRODUCTION_COST", signed_usd=-100000),
        dict(common, source_type="PAYMENT_PRODUCTION_COST", signed_usd=100000),
        dict(common, source_type="PAYMENT_PRODUCTION_COST", signed_usd=-100000),
    ]
    build_industrial_detail(m, ops, tables, journal)
    row = next(r for r in m.tables["industrial_detail_reconciliation"] if r["segment"] == "RWH")
    assert D(row["source_amount_usd"]) == 100000
    assert D(row["maintenance_amount_usd"]) == 8000
    assert D(row["remaining_production_amount_usd"]) == 92000
