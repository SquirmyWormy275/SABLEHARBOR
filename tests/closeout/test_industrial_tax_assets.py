from decimal import Decimal as D

from enterprise.closeout.industrial_tax_assets import build


def test_acquisition_component_cost_ownership_and_structural_exclusion():
    result = build({"datasets": {"assets": []}})
    initial = [
        r
        for r in result["rows"]
        if r["scenario"] == "base"
        and r["jurisdiction"] == "US"
        and r["year"] == 2026
        and r["asset_id"].startswith("ARU-TERMINAL")
    ]
    assert sum(D(r["gross_cost_usd"]) for r in initial) == 12000000
    assert sum(D(r["tax_depreciation_usd"]) for r in initial) < 12000000 / 39
    assert {r["taxpayer"] for r in initial} == {"ARU", "BST"}
    assert all(not r["bonus_selected"] for r in initial)


def test_historical_cip_keeps_basis_without_early_deduction():
    result = build({"datasets": {"assets": []}})
    rows = [
        r
        for r in result["rows"]
        if r["scenario"] == "base" and r["jurisdiction"] == "US" and r["asset_id"] == "RW-H2-REHAB"
    ]
    first, service = rows[:2]
    assert first["year"] == 2025 and D(first["tax_depreciation_usd"]) == 0
    assert D(first["closing_tax_basis_usd"]) == 8000000
    assert service["year"] == 2026 and D(service["tax_depreciation_usd"]) == 8000000


def test_il_regular_depreciation_and_ca_do_not_inherit_bonus():
    result = build({"datasets": {"assets": []}})
    rows = [
        r
        for r in result["rows"]
        if r["scenario"] == "base"
        and r["taxpayer"] == "PS"
        and r["asset_id"] == "RW-H2-REHAB"
        and r["year"] == 2026
    ]
    amounts = {r["jurisdiction"]: D(r["tax_depreciation_usd"]) for r in rows}
    assert amounts["US"] == amounts["WV"] == 8000000
    assert 0 < amounts["IL"] < amounts["US"]
    assert amounts["CA"] == 800000


def test_equal_total_component_reallocation_and_duplicate_lease_rejected():
    import copy
    import json

    import pytest

    from enterprise.closeout.industrial_tax_assets import ROOT, SOURCE, validate_components

    source = json.loads(SOURCE.read_text())
    finance = json.loads((ROOT / "industrial/source/finance.json").read_text())
    validate_components(source, finance)
    changed = copy.deepcopy(source)
    changed["aru_initial_components"][0]["cost_usd"] = "11999999"
    changed["aru_initial_components"][2]["cost_usd"] = "12000001"
    with pytest.raises(ValueError, match="buckets"):
        validate_components(changed, finance)
    changed = copy.deepcopy(source)
    changed["aru_initial_components"].append(changed["aru_initial_components"][-1])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_components(changed, finance)


def test_forecast_cip_and_cost_identity_guards():
    import copy

    import pytest

    from enterprise.closeout.industrial_tax_assets import validate_card_history

    row = dict(
        year=2027,
        month=3,
        entity="ARU_GROUP",
        project_id="TRUCK-CAPACITY",
        gross_usd="100",
        asset_status="CONSTRUCTION_IN_PROGRESS",
        actual_conditional_service_period="NOT_IN_SERVICE",
    )
    served = dict(
        row,
        month=4,
        asset_status="CONDITIONAL_IN_SERVICE",
        actual_conditional_service_period="2027-04",
    )
    validate_card_history([row, served])
    for field, value in (
        ("gross_usd", "101"),
        ("entity", "RWH_PS"),
        ("actual_conditional_service_period", "2027-05"),
    ):
        broken = copy.deepcopy(served)
        broken[field] = value
        with pytest.raises(ValueError):
            validate_card_history([row, broken])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_card_history([row, row])
    with pytest.raises(ValueError, match="CIP"):
        validate_card_history([dict(row, actual_conditional_service_period="2027-03")])
