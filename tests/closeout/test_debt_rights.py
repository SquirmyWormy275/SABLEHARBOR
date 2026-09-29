import json
from copy import deepcopy

import pytest

from enterprise.closeout.debt_rights import OPERATIONS, SOURCE, build


def test_exact_grant_and_separate_filing_states():
    result = build()
    assert len(result["collateral"]) == 64
    assert len(result["context_only_facilities"]) == 7
    assert result["excluded_asset_count"] == 78
    assert result["additional_cash_usd"] == result["additional_journal_count"] == 0
    assert all(
        r["grantor"] == "ARU" and r["collateral_value_usd"] is None for r in result["collateral"]
    )
    assert all(
        r["filing_submission"] == "NOT_SUBMITTED" and r["perfection"] == "NOT_ESTABLISHED"
        for r in result["collateral"]
    )
    assert result["reporting_obligations"][0]["due_date"] == "2026-11-14"
    assert result["old_lien_release"] == "NOT_ESTABLISHED"


def test_no_backdated_grant():
    result = build(as_of="2026-09-21")
    assert all(r["grant_state"] == "NOT_YET_EFFECTIVE" for r in result["collateral"])
    assert result["synthetic_execution"]["state"] == "NOT_YET_EFFECTIVE"


@pytest.mark.parametrize("change", ["other_owner", "leased", "future", "planned"])
def test_unsupported_source_asset_rejected(change):
    ops = deepcopy(json.loads(OPERATIONS.read_text()))
    row = ops["road_equipment"][0]
    if change == "other_owner":
        row["owner"] = "Blood, Sweat & Tears Railway Company"
    elif change == "leased":
        row["ownership"] = "leased"
    elif change == "future":
        row["in_service_date"] = "2027-01-01"
    else:
        row["status"] = "planned purchase"
    with pytest.raises(ValueError):
        build(operations=ops)


@pytest.mark.parametrize(
    "change",
    [
        "guarantee",
        "premium",
        "missing_asset",
        "duplicate",
        "perfection",
        "backdate",
        "missing_owner",
    ],
)
def test_unapproved_terms_population_and_filing_states_rejected(change):
    source = deepcopy(json.loads(SOURCE.read_text()))
    if change == "guarantee":
        source["terms"]["guarantors"] = ["SHI"]
    elif change == "premium":
        source["terms"]["prepayment_premium_pct"] = "1"
    elif change == "missing_asset":
        source["collateral_ids"].pop()
    elif change == "duplicate":
        source["collateral_ids"][-1] = source["collateral_ids"][0]
    elif change == "perfection":
        source["filing_states"]["perfection"] = "PERFECTED"
    elif change == "backdate":
        source["effective_date"] = "2026-01-07"
    else:
        source["handling_owner_confirmations"].pop()
    with pytest.raises(ValueError):
        build(source=source)


def test_vehicle_route_does_not_infer_certificate_jurisdiction_from_incorporation():
    rows = build()["collateral"]
    road = [r for r in rows if r["population"] == "road_equipment"]
    assert len(road) == 44
    assert all("SUBJECT_TO_TITLE_JURISDICTION_CONFIRMATION" in r["filing_route"] for r in road)
    assert all(r["perfection"] == "NOT_ESTABLISHED" for r in road)
