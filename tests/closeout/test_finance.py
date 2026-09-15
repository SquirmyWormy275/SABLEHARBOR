from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.finance import CloseoutAdjustment, verify
from industrial.planning.enterprise import Books


def books(scenario):
    b = Books(
        scenario,
        {
            "segment_mapping": {"FOUNDRY_FIELD": "foundry-field"},
            "knowledge_cutoff": "2026-09-15",
            "created_on": "2026-09-15",
        },
        CloseoutAdjustment.account_types | {"LEG_1600": "asset", "LEG_3000": "equity"},
    )
    b.balances["SHI"]["LEG_1600"] = D(30000000)
    return b


def emitted():
    adjustment = CloseoutAdjustment()
    rows = []
    for scenario in ["base", "downside", "expansion"]:
        b = books(scenario)
        adjustment.post_opening(b)
        adjustment._post(b, 2027, 1)
        rows += b.rows
    return rows


def test_scoped_correction():
    rows = emitted()
    assert verify(rows)["direct_cash_usd"] == "0"
    assert all(r["entity"] == "SHI" for r in rows)
    assert sum(D(r["signed_usd"]) for r in rows) == 0
    assert sum(D(r["signed_usd"]) for r in rows if r["account"] == "LEG_1600") == -90000000
    assert len([r for r in rows if r["source_id"] == "FF-003-TAX"]) == 2


@pytest.mark.parametrize(
    "mutation", ["duplicate", "reverse", "entity", "period", "scenario", "missing", "cash"]
)
def test_reject_corrupt_balanced_or_scoped_outputs(mutation):
    rows = deepcopy(emitted())
    if mutation == "duplicate":
        rows += deepcopy(rows[:2])
    if mutation == "reverse":
        for row in rows[:2]:
            row["signed_usd"] = str(-D(row["signed_usd"]))
    if mutation == "entity":
        rows[0]["entity"] = "ARU"
    if mutation == "period":
        rows[0]["month"] = 9
    if mutation == "scenario":
        rows[-1]["scenario"] = "base"
    if mutation == "missing":
        rows.pop()
    if mutation == "cash":
        rows[0]["cash_flow"] = "FINANCING"
    with pytest.raises(ValueError):
        verify(rows)


def test_guard_opening_and_duplicate_application():
    adjustment = CloseoutAdjustment()
    b = books("base")
    adjustment.post_opening(b)
    assert b.balances["SHI"]["LEG_1600"] == 0
    with pytest.raises(ValueError):
        adjustment.post_opening(b)
    b = books("base")
    b.balances["SHI"]["LEG_1600"] = D(0)
    with pytest.raises(ValueError):
        adjustment.post_opening(b)


def test_predecessor_bridge_retains_runtime_action_and_corrects_opening():
    from enterprise.runtime.build_finance import replacement_bridge

    rows = [r for r in emitted() if r["source_id"] == "SH-VOICE-GW-01"]
    bridge = replacement_bridge({"journal_rows": []}, {"journal_rows": rows})
    assert {r["action"] for r in bridge} == {"ADD_GOODWILL_OPENING_CORRECTION"}
