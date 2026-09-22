from collections import defaultdict
from decimal import Decimal as D

import pytest

from enterprise.closeout.statutory_posting import TYPES, StatutoryPosting, installments
from industrial.planning.enterprise import Books


def test_california_minimum_is_first_installment_not_four_quarters():
    assert installments(D(800), "CA") == {4: D(800), 6: D(0), 12: D(0)}
    assert sum(installments(D("12345.6789"), "CA").values()) == D("12345.6789")


def test_state_credits_cannot_settle_another_jurisdiction():
    p = object.__new__(StatutoryPosting)
    p.tax = {("base", "PS", "CA", 2026): D(800), ("base", "PS", "IL", 2026): D(1200)}
    p.native = defaultdict(lambda: defaultdict(D))
    p.cash = defaultdict(D)
    p.annual_deferred = defaultdict(lambda: defaultdict(D))
    p.opening_deferred = defaultdict(lambda: defaultdict(D))
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-22", "created_on": "2026-09-22"},
        TYPES | {"1150": "asset", "2150": "liability", "1000": "asset", "3100": "equity"},
    )
    b.balances["PS"]["CO_SUB_TAX_PREPAID_CA"] = D(800)
    p.post_month(b, 2026, 1)
    assert b.balances["PS"]["CO_SUB_TAX_PAY_CA"] == 0
    assert b.balances["PS"]["CO_SUB_TAX_PAY_IL"] == D(-100)
    assert b.balances["PS"]["CO_SUB_TAX_PREPAID_CA"] == D("733.3333")
    with pytest.raises(ValueError, match="Duplicate"):
        p.post_month(b, 2026, 1)


def test_acquired_dta_successor_hits_expense_not_opening_equity():
    p = object.__new__(StatutoryPosting)
    p.tax = {}
    p.native = defaultdict(lambda: defaultdict(D))
    p.cash = defaultdict(D)
    p.annual_deferred = defaultdict(lambda: defaultdict(D))
    p.opening_deferred = defaultdict(lambda: defaultdict(D))
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-22", "created_on": "2026-09-22"},
        TYPES
        | {
            "1150": "asset",
            "2150": "liability",
            "1000": "asset",
            "3100": "equity",
            "1800": "asset",
        },
    )
    for entity, value in [("ARU", D(500000)), ("BST", D(87500))]:
        p.native["base", entity, 2026, 1]["1800"] = value
        b.balances[entity]["1800"] = value
    p.post_month(b, 2026, 1)
    assert sum(b.balances[e]["CO_SUB_TAX_DEFERRED"] for e in ("ARU", "BST")) == D(587500)
    assert all(b.balances[e]["3100"] == 0 for e in ("ARU", "BST"))
    assert all(r["account"] != "1600" for r in b.rows)


def inputs():
    from types import SimpleNamespace

    scenarios, years = ("base", "downside", "expansion"), range(2026, 2032)

    def tax(s, e, j, y):
        return dict(
            scenario=s,
            taxpayer=e,
            jurisdiction=j,
            year=y,
            current_tax_usd="0",
            gross_dta_usd="0",
            valuation_allowance_usd="0",
            gross_dtl_usd="0",
        )

    states = [
        tax(s, e, j, y)
        for s in scenarios
        for e in ("SHI", "SHIH", "PS", "ARU", "BST")
        for j in ("CA", "IL", "WV")
        for y in years
    ]
    federal = [
        tax(s, e, "US", y) for s in scenarios for e in ("SHIH", "PS", "ARU", "BST") for y in years
    ]
    deferred = states + [
        tax(s, e, "US", y)
        for s in scenarios
        for e in ("SHI", "SHIH", "PS", "ARU", "BST")
        for y in years
    ]
    opening = [
        tax(s, e, j, 2026)
        for s in scenarios
        for e, j in [("SHI", "US"), ("PS", "US"), ("SHI", "CA"), ("PS", "IL"), ("SHI", "WV")]
    ]
    parent = SimpleNamespace(rows=[dict(scenario=s, year=y) for s in scenarios for y in years])
    journal = [
        dict(
            scenario=s,
            entity=e,
            year=y,
            month=m,
            source_id="LEGAL-test",
            journal_id=f"{e}-{y}-{m}",
            line_no=1,
        )
        for s in scenarios
        for e in ("ARU", "BST", "PS", "RWH")
        for y in years
        for m in range(1, 13)
    ]
    settlement = dict(
        rows=[
            dict(scenario=s, source_group=g, year=y, month=m, gross_source_tax_cash_paid_usd="0")
            for s in scenarios
            for g in ("ARU_GROUP", "RWH_PS")
            for y in years
            for m in range(1, 13)
        ],
        payments=[],
    )
    return [
        dict(journal_rows=journal),
        parent,
        dict(federal=federal, states=states),
        deferred,
        opening,
        settlement,
    ]


def test_exact_source_population():
    from enterprise.closeout.statutory_posting import _validate_inputs

    _validate_inputs(*inputs())


@pytest.mark.parametrize(
    "position,key", [(2, "federal"), (2, "states"), (5, "rows"), (0, "journal_rows")]
)
@pytest.mark.parametrize("mutation", ["duplicate", "omit"])
def test_input_population_mutations_rejected(position, key, mutation):
    from enterprise.closeout.statutory_posting import _validate_inputs

    args = inputs()
    rows = args[position][key]
    rows.append(dict(rows[0])) if mutation == "duplicate" else rows.pop()
    with pytest.raises(ValueError):
        _validate_inputs(*args)


@pytest.mark.parametrize("position", [3, 4])
def test_deferred_duplicate_rejected(position):
    from enterprise.closeout.statutory_posting import _validate_inputs

    args = inputs()
    args[position].append(dict(args[position][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        _validate_inputs(*args)


def test_paid_summary_without_source_payment_rejected():
    from enterprise.closeout.statutory_posting import _validate_inputs

    args = inputs()
    args[5]["rows"][0]["gross_source_tax_cash_paid_usd"] = "100"
    with pytest.raises(ValueError, match="payment detail"):
        _validate_inputs(*args)


@pytest.mark.parametrize("mismatch", [False, True])
def test_native_bst_dta_writeoff_requires_exact_aru_expense_counterpart(mismatch):
    p = object.__new__(StatutoryPosting)
    p.settlement = {"payments": []}
    p.tax = {}
    p.native = defaultdict(lambda: defaultdict(D))
    p.cash = defaultdict(D)
    p.annual_deferred = defaultdict(lambda: defaultdict(D))
    p.opening_deferred = defaultdict(lambda: defaultdict(D))
    p.native["downside", "ARU", 2027, 1].update(
        {"1800": D(-137500), "2250": D(-18055), "5501": D(605555)}
    )
    p.native["downside", "BST", 2027, 1]["1800"] = D(-450000) + int(mismatch)
    b = Books(
        "downside",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-22", "created_on": "2026-09-22"},
        TYPES
        | {
            "1150": "asset",
            "2150": "liability",
            "1000": "asset",
            "3100": "equity",
            "1800": "asset",
            "2250": "liability",
            "5501": "expense",
        },
    )
    if mismatch:
        with pytest.raises(ValueError, match="Unexplained native deferred"):
            p.post_month(b, 2027, 1)
    else:
        p.post_month(b, 2027, 1)
        assert sum(b.balances[e]["CO_SUB_TAX_DEFERRED"] for e in ("ARU", "BST")) == 0
        assert all(b.balances[e]["3100"] == 0 for e in ("ARU", "BST"))
