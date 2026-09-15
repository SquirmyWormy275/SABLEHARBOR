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
