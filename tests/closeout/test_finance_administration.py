import json
from copy import deepcopy

import pytest

from enterprise.closeout.finance_administration import ROOT, SOURCE_PATHS, build


def test_existing_settlement_split_no_new_posting():
    result = build()
    assert [r["principal_usd"] for r in result["payoff_components"]] == [11500000, 2000000]
    assert result["payoff_total_principal_usd"] == 13500000
    assert result["retained_leases_excluded_usd"] == 2500000
    assert result["additional_journal_count"] == result["additional_cash_usd"] == 0
    assert result["maturity"]["date"] == "2031-01-07"
    assert all(r["release_instrument"] is None for r in result["payoff_components"])


def test_wrong_principal_population_rejected():
    source = json.loads((ROOT / SOURCE_PATHS[0]).read_text())
    source["closing_2025_drivers"]["term_principal"] += 1
    with pytest.raises(ValueError, match="reconcile"):
        build(finance=source)


@pytest.mark.parametrize("mutation", ["duplicate", "omit"])
def test_asset_population_integrity(mutation):
    source = json.loads((ROOT / SOURCE_PATHS[1]).read_text())
    if mutation == "duplicate":
        source["road_equipment"].append(deepcopy(source["road_equipment"][0]))
    else:
        source["road_equipment"].pop()
    with pytest.raises(ValueError, match="[Dd]uplicate|incomplete"):
        build(operations=source)


def test_explicit_and_inferred_title_are_separate():
    rows = build()["asset_screen"]
    explicit = [r for r in rows if r["disposition"] == "ARU_OWNER_EXPLICIT_SOURCE"]
    inferred = [r for r in rows if r["disposition"] == "ARU_HANDLING_OWNER_INFERRED_REQUIRE_TITLE"]
    assert len(explicit) == 57
    assert len(inferred) == 14
    assert all(not r["pledged"] and r["collateral_value_usd"] is None for r in rows)
    assert all(not r["asset_id"].startswith("BST-") for r in explicit + inferred)


def test_wrong_facility_does_not_promote_handling_owner():
    source = json.loads((ROOT / SOURCE_PATHS[1]).read_text())
    row = source["handling_equipment"][0]
    row["facility_id"] = "FAC-WAM-INT"
    actual = next(r for r in build(operations=source)["asset_screen"] if r["asset_id"] == row["id"])
    assert actual["disposition"] == "EXCLUDED_FROM_ARU_ONLY_CANDIDATE_SCOPE"
