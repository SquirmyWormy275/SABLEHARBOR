import json
from copy import deepcopy

import pytest

from enterprise.closeout.capital_rights import CAPITAL, SOURCE, build


def holdings():
    return {r["holder_id"]: r["units"] for r in json.loads(CAPITAL.read_text())["holders"]}


def test_current_board_and_holdings_unchanged():
    x = build()
    assert len(x["board_director_ids"]) == 9
    assert len(x["synthetic_assents"]) == 5
    assert all(r["eligible"] for r in x["rights"])
    assert x["unit_changes"] == x["additional_cash_usd"] == 0


@pytest.mark.parametrize("holder,threshold", [("SH-HOLDER-HV", 9250000), ("SH-HOLDER-WR", 7500000)])
@pytest.mark.parametrize("delta", [0, -1])
def test_exact_inclusive_threshold(holder, threshold, delta):
    h = holdings()
    transfer = h[holder] - threshold - delta
    h[holder] -= transfer
    h["SH-HOLDER-DM"] += transfer
    row = next(r for r in build(h)["rights"] if r["holder_id"] == holder)
    assert row["eligible"] is (delta == 0)
    assert row["automatic_appointment_or_removal"] is False


def test_split_preserves_eligibility_and_earlier_date_not_backdated():
    x = build({k: v * 2 for k, v in holdings().items()}, split_numerator=2)
    assert x["rights"][0]["threshold_numerator"] == 18500000
    assert all(r["eligible"] for r in x["rights"])
    assert all(r["eligible"] is None for r in build(as_of="2026-09-21")["rights"])


@pytest.mark.parametrize(
    "mutation", ["duplicate_assent", "missing_holder", "threshold", "negative"]
)
def test_invalid_population_or_changed_right_rejected(mutation):
    h = holdings()
    s = deepcopy(json.loads(SOURCE.read_text()))
    if mutation == "duplicate_assent":
        s["synthetic_member_assents"][-1] = s["synthetic_member_assents"][0]
    elif mutation == "missing_holder":
        h.pop("SH-HOLDER-DM")
    elif mutation == "threshold":
        s["designations"][0]["threshold_units"] += 1
    else:
        h["SH-HOLDER-DM"] = -1
    with pytest.raises(ValueError):
        build(h, source=s)
