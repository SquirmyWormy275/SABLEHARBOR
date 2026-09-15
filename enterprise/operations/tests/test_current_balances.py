import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import build
from enterprise.operations.current_balances import validate, verify_legal_balances


@pytest.fixture(scope="module")
def tables():
    return build()["tables"]


def test_complete_declared_balance_populations(tables):
    assert len(tables["current_receivable_customers"]) == 29
    assert len(tables["current_supplier_balances"]) == 6
    assert len(tables["current_asset_source_population"]) == 149
    assert (
        sum(D(r["closing_allowance_usd"]) for r in tables["current_receivable_customers"]) == 80000
    )
    assert (
        sum(D(r["gross_cost_usd"]) for r in tables["current_core_asset_carrying_components"])
        == 9000000
    )
    expected = {
        ("ARU", "1100"): D("3830400"),
        ("BST", "1100"): D("2249600"),
        ("RWH", "1100"): D("4366668"),
        ("RWH", "1200"): D("8693912.5497"),
        ("RWH", "1210"): D("867149.3725"),
    }
    for row in tables["current_legal_balance_bridges"]:
        key = row["legal_entity"], row["account"]
        if key in expected:
            assert D(row["closing_signed_usd"]) == expected[key]


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("current_receivable_customers", "collected_usd", "0"),
        ("current_supplier_balances", "payments_usd", "1"),
        ("current_inventory_classes", "closing_quantity", "1"),
        ("current_legal_balance_bridges", "effective_period", "2027-08"),
        ("current_core_asset_carrying_components", "gross_cost_usd", "1"),
    ],
)
def test_balance_mutations_fail(tables, table, field, value):
    broken = copy.deepcopy(tables)
    broken[table][0][field] = value
    with pytest.raises(ValueError):
        validate(broken)


@pytest.mark.parametrize(
    "table",
    [
        "current_receivable_customers",
        "current_supplier_balances",
        "current_asset_source_population",
        "current_inventory_classes",
    ],
)
def test_omitted_and_duplicated_members_fail(tables, table):
    for mutation in ("omit", "duplicate"):
        broken = copy.deepcopy(tables)
        if mutation == "omit":
            broken[table].pop()
        else:
            broken[table].append(broken[table][0])
        with pytest.raises(ValueError):
            validate(broken)


def test_legal_balance_reperformance_rejects_wrong_current_book(tables):
    rows = [
        dict(
            entity=r["legal_entity"],
            account=r["account"],
            signed_usd=r["closing_signed_usd"],
            scenario="base",
            year="2026",
            month="8",
        )
        for r in tables["current_legal_balance_bridges"]
    ]
    assert verify_legal_balances(tables, rows)["additional_journal_usd"] == "0.00"
    rows[0]["signed_usd"] = "1"
    with pytest.raises(ValueError, match="independent legal"):
        verify_legal_balances(tables, rows)


def test_core_asset_net_bridge_and_old_uncorrected_finance_rejected(tables):
    from enterprise.operations.current_balances import verify_core_asset_balances

    rows = [
        dict(entity="SHI", scenario="base", year="2026", month="8", account=a, signed_usd=v)
        for a, v in (("LEG_1500", "9000000"), ("LEG_1590", "-4714285.7139"))
    ]
    assert D(verify_core_asset_balances(tables, rows)["net_usd"]) == D("4285714.2861")
    rows[1]["signed_usd"] = "0"
    with pytest.raises(ValueError, match="corrected finance"):
        verify_core_asset_balances(tables, rows)
    broken = copy.deepcopy(tables)
    broken["current_core_asset_carrying_components"][0]["net_carrying_usd"] = "5000000"
    with pytest.raises(ValueError, match="net bridge"):
        validate(broken)


def test_mine_cost_layers_are_one_stock_and_both_required(tables):
    layers = tables["current_mine_inventory_cost_layers"]
    assert len(layers) == 2
    assert sum(D(r["closing_signed_usd"]) for r in layers) == D("9561061.9222")
    for mutation in ("omit", "balanced_wrong"):
        broken = copy.deepcopy(tables)
        if mutation == "omit":
            broken["current_mine_inventory_cost_layers"].pop()
        else:
            r = broken["current_mine_inventory_cost_layers"][0]
            r["opening_signed_usd"] = str(D(r["opening_signed_usd"]) + 1)
            r["closing_signed_usd"] = str(D(r["closing_signed_usd"]) + 1)
        with pytest.raises(ValueError, match="Mine"):
            validate(broken)


def test_support_layer_reperformed_from_monthly_cost_and_unit_population(tables):
    from enterprise.closeout.rwh_book import current_inventory_bridge
    from industrial.planning.enterprise import load_anchor

    anchor = load_anchor()
    units, support, elimination = D(125000), D(0), D(0)
    for month in range(1, 9):
        native = [r for r in anchor if r["entity"] == "RWH_PS" and int(r["month"]) == month]
        ga = sum(
            D(r["signed_usd"])
            for r in native
            if r["account"] == "5100" and r["description"] == "pale sun site g and a usd"
        )
        provider_cost = D(203125) if month == 8 else D(125000)
        site_cost = ga - provider_cost
        site_production = D(10000) + (site_cost - D(10000)) / 2
        # Fee and underlying cost stay separate; no duplicated intercompany fee.
        legal_production = D(125000) * D(".408") + site_production
        difference = (provider_cost - D(125000)) * D(".408")
        available = units + D(547400) / 12
        sold = D(500000) / 12
        support = (support + legal_production) * (1 - sold / available)
        elimination = (elimination + difference) * (1 - sold / available)
        units = available - sold
    row = current_inventory_bridge(anchor)[7]
    assert support.quantize(D(".0001")) == D(row["support_inventory_usd"])
    assert elimination.quantize(D(".0001")) == D(row["consolidated_service_cost_inventory_usd"])
    assert elimination.quantize(D(".0001")) == D("25176.3198")
    legal = next(
        r
        for r in tables["current_legal_balance_bridges"]
        if r["legal_entity"] == "RWH" and r["account"] == "1200"
    )
    # The legal population excludes the distinct consolidated provider-cost adjustment.
    assert D(legal["closing_signed_usd"]) == D(row["corrected_cash_inventory_usd"])
    assert D(legal["closing_signed_usd"]) != D(row["corrected_cash_inventory_usd"]) + elimination
