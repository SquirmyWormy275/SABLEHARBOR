import pytest

from enterprise.closeout.statutory_replay import compare


def source():
    common = dict(
        scenario="base",
        entity="PS",
        year=2026,
        month=1,
        source_id="CO-STAT-PROVISION-PS-2026-1",
        cash_flow="",
    )
    return [
        common | dict(account="CO_SUB_TAX_CURRENT", signed_usd="100.0000"),
        common | dict(account="CO_SUB_TAX_PAY_CA", signed_usd="-100.0000"),
    ]


def test_replay_positive():
    assert compare(source(), source())["statutory_legs_replayed"] == 2


@pytest.mark.parametrize("mutation", ["duplicate", "reverse", "entity", "period", "omit"])
def test_balanced_or_missing_statutory_mutations_rejected(mutation):
    rows = source()
    if mutation == "duplicate":
        rows += source()
    elif mutation == "reverse":
        for r in rows:
            r["signed_usd"] = str(-float(r["signed_usd"]))
    elif mutation == "entity":
        for r in rows:
            r["entity"] = "SHI"
    elif mutation == "period":
        for r in rows:
            r["month"] = 2
    else:
        rows = []
    with pytest.raises(ValueError, match="Statutory replay differs"):
        compare(source(), rows)
