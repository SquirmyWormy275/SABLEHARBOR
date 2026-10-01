from decimal import Decimal as D

from enterprise.closeout.support_inventory import allocation, step
from industrial.planning.enterprise import load_anchor


def test_august_actual_platform_and_site_capacity_are_distinct():
    native = [r for r in load_anchor() if r["entity"] == "RWH_PS" and int(r["month"]) == 8]
    row = allocation(native, 2026, 8)
    assert row["ps_cost"] == 203125
    assert row["site_cost"] == 30208
    assert row["group_production_cost"] == 102979
    assert row["legal_production_cost"] == 71104
    assert row["fee_production_cost"] == 51000
    # Costs paid at the platform exceed the preserved fee; consolidation uses
    # actual cost without inventing an additional reimbursement agreement.
    assert row["group_production_cost"] - row["legal_production_cost"] == 31875
    result = step(D(0), D(0), native, 2026, 8, D(200000), D(50000))
    assert result["closing_legal"] + result["legal_cogs"] == 71104
    assert result["closing_elimination"] + result["elimination_cogs"] == 31875


def test_current_person_work_population_agrees_with_cost_mix():
    from enterprise.operations.completed_period import build

    rows = build()["tables"]["production_support_work"]
    # The cost provider's declared current percentage is independently tied to
    # the completed person-level work allocation, not to a generic G&A label.
    assert len(rows) == 12
    assert sum(D(r["loaded_payroll_usd"]) for r in rows) == 203125
    assert sum(D(r["production_support_payroll_usd"]) for r in rows) == 82875
