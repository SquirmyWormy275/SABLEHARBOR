import copy
import json
from decimal import Decimal as D

import pytest

from enterprise.closeout.state_apportionment import (
    MEMBERS,
    SOURCE,
    build,
    factors,
    il_transport_conversion,
)


def test_prescribed_transport_conversion_uses_subgroup_denominator():
    result = il_transport_conversion(
        {"ARU": 300, "BST": 700}, {"ARU": 5, "BST": 8}, {"ARU": 25, "BST": 175}
    )
    assert result == {"ARU": D(25), "BST": D(40)}
    with pytest.raises(ValueError):
        il_transport_conversion({"ARU": 300}, {"ARU": 0}, {"ARU": 0})


def test_finnigan_and_qualified_activity_screen():
    e = dict(SHI=1000, SHIH=0, PS=1000, ARU=300, BST=700)
    sales = {s: {m: 0 for m in MEMBERS} for s in ["CA", "IL", "WV"]}
    sales["CA"]["SHI"] = 1000
    sales["IL"].update(PS=1000, ARU=5, BST=8)
    taxable = {"CA": ["SHI", "SHIH", "PS"], "IL": ["PS"], "WV": ["SHI"]}
    r = factors(e, sales, {"ARU": 25, "BST": 175}, 1000, taxable)
    il = {x["member"]: x for x in r if x["jurisdiction"] == "IL"}
    assert D(il["PS"]["market_numerator_usd"]) == 1065
    assert D(il["ARU"]["member_factor"]) == 0
    with pytest.raises(ValueError, match="three-factor"):
        factors(e, sales, {"ARU": 25, "BST": 175}, 1501, taxable)


def fixture():
    source = json.loads(SOURCE.read_text())
    legal, native, anchor, markets = [], [], [], []
    for scenario in source["scenarios"]:
        for year in source["years"]:
            for month in range(1, 13):
                for entity, amount in [("SHI", 1000), ("RWH", 100), ("ARU", 100), ("BST", 100)]:
                    jid = f"{entity}-{year}-{month}"
                    row = dict(
                        scenario=scenario,
                        entity=entity,
                        year=year,
                        month=month,
                        journal_id=jid,
                        line_no="1",
                        account="4000",
                        account_type="revenue",
                        signed_usd=str(-amount),
                        source_id=jid,
                    )
                    legal.append(row)
                    if entity == "SHI":
                        markets.append(
                            dict(
                                row,
                                population="EXTERNAL_CUSTOMER",
                                market_state="CA",
                                receipts_usd=str(amount),
                            )
                        )
                    else:
                        n = dict(
                            row,
                            entity="RWH_PS" if entity == "RWH" else "ARU_GROUP",
                            segment="RWH"
                            if entity == "RWH"
                            else ("TRUCKING" if entity == "ARU" else "BST"),
                        )
                        if year == 2026:
                            if scenario == "base":
                                n.pop("scenario")
                                anchor.append(n)
                        else:
                            native.append(n)
    return source, {"journal_rows": legal}, {"journal_rows": native}, anchor, markets


def test_full_population_and_old_target_day_are_preserved():
    source, result, native, anchor, markets = fixture()
    rows = build(result, native, anchor, market_rows=markets, source=source)
    assert len(rows) == 288
    row = next(
        r
        for r in rows
        if (r["scenario"], r["year"], r["jurisdiction"], r["member"]) == ("base", 2026, "IL", "ARU")
    )
    assert D(row["oldtarget_january7_receipts_excluded_usd"]) == 4
    assert D(row["external_receipts_usd"]) == 1196
    assert all(r["monetary_journals_posted"] == 0 for r in rows)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "omission",
        "wrong_entity",
        "wrong_year",
        "native_duplicate",
        "market_duplicate",
        "market_omission",
    ],
)
def test_adversarial_population_mutations(mutation):
    source, result, native, anchor, markets = copy.deepcopy(fixture())
    if mutation == "duplicate":
        result["journal_rows"].append(result["journal_rows"][0])
    elif mutation == "omission":
        result["journal_rows"].pop()
    elif mutation == "wrong_entity":
        result["journal_rows"][0]["entity"] = "NEWCO"
    elif mutation == "wrong_year":
        result["journal_rows"][0]["year"] = 2032
    elif mutation == "native_duplicate":
        anchor.append(anchor[0])
    elif mutation == "market_duplicate":
        markets.append(markets[0])
    else:
        markets.pop()
    with pytest.raises(ValueError):
        build(result, native, anchor, market_rows=markets, source=source)
