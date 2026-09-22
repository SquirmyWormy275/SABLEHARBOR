from collections import defaultdict
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from enterprise.closeout.statutory_deferred import build


def population():
    result = dict(legal_trial_balance_rows=[], journal_rows=[])
    parent = SimpleNamespace(rows=[], asset_rows=[])
    mine, factors = [], []
    assets = dict(totals=defaultdict(lambda: defaultdict(D)))
    current = dict(federal=[], states=[])
    for s in ("base", "downside", "expansion"):
        for y in range(2026, 2032):
            parent.rows.append(
                dict(
                    scenario=s,
                    year=y,
                    **{
                        f: "0"
                        for f in (
                            "allowance_addback_usd",
                            "inventory_addback_usd",
                            "unpaid_transaction_tax_addback_usd",
                            "book_asset_carrying_usd",
                            "california_asset_basis_usd",
                            "federal_asset_basis_usd",
                            "historical_research_basis_usd",
                            "closing_federal_nol_usd",
                            "interest_carryforward_usd",
                        )
                    },
                )
            )
            for e in ("SHI", "PS", "RWH", "ARU", "BST", "ELIM"):
                # A nonzero source account makes omissions and doubling observable.
                result["journal_rows"].append(
                    dict(
                        scenario=s,
                        entity=e,
                        year=y,
                        month=1,
                        journal_id=f"{e}-{y}",
                        line_no=1,
                        account="1200",
                        signed_usd="1",
                    )
                )
                result["legal_trial_balance_rows"].append(
                    dict(
                        scenario=s,
                        entity=e,
                        year=y,
                        month=12,
                        account="1200",
                        signed_usd=str(y - 2025),
                    )
                )
            for e in ("PS", "ARU", "BST"):
                current["federal"].append(
                    dict(
                        scenario=s,
                        taxpayer=e,
                        year=y,
                        closing_nol_usd="0",
                        interest_carryforward_usd="0",
                    )
                )
            for j in ("US", "CA", "IL", "WV"):
                mine.append(
                    dict(
                        scenario=s,
                        jurisdiction=j,
                        year=y,
                        tax_mineral_basis_usd="0",
                        tax_cash_inventory_usd="0",
                        tax_dda_inventory_usd="0",
                    )
                )
                for e in ("PS", "ARU", "BST"):
                    assets["totals"][s, e, j, y]["closing_tax_basis_usd"] = D(1)
            for j in ("CA", "IL", "WV"):
                for e in ("SHI", "SHIH", "PS", "ARU", "BST"):
                    current["states"].append(
                        dict(
                            scenario=s,
                            jurisdiction=j,
                            taxpayer=e,
                            year=y,
                            closing_member_nol_usd="0",
                        )
                    )
                    factors.append(
                        dict(scenario=s, jurisdiction=j, member=e, year=y, member_factor=".1")
                    )
            factors.append(
                dict(scenario=s, jurisdiction="PA", member="SHI", year=y, member_factor="0")
            )
    return result, parent, mine, assets, current, factors


def selected(args, name):
    return {
        "parent": args[1].rows,
        "mine": args[2],
        "federal": args[4]["federal"],
        "state": args[4]["states"],
        "factor": args[5],
    }[name]


def test_complete_population_and_elimination_inventory():
    args = population()
    rows = build(*args)
    assert len(rows) == 342
    first = next(
        r
        for r in rows
        if (r["scenario"], r["taxpayer"], r["year"], r["jurisdiction"])
        == ("base", "PS", 2026, "US")
    )
    # The legal RWH inventory and separate ELIM inventory each reduce tax-minus-book by 1.
    args[0]["journal_rows"] = [r for r in args[0]["journal_rows"] if r["entity"] != "ELIM"]
    args[0]["legal_trial_balance_rows"] = [
        r for r in args[0]["legal_trial_balance_rows"] if r["entity"] != "ELIM"
    ]
    no_elim = next(
        r
        for r in build(*args)
        if (r["scenario"], r["taxpayer"], r["year"], r["jurisdiction"])
        == ("base", "PS", 2026, "US")
    )
    assert D(first["gross_dtl_usd"]) - D(no_elim["gross_dtl_usd"]) == D(".21")


@pytest.mark.parametrize("name", ["parent", "mine", "federal", "state", "factor"])
@pytest.mark.parametrize("mutation", ["duplicate", "omit", "wrong_scope"])
def test_index_population_rejected(name, mutation):
    args = population()
    rows = selected(args, name)
    if mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "omit":
        rows.pop(0)
    else:
        rows[0]["scenario"] = "unapproved"
    with pytest.raises(ValueError, match="deferred-tax"):
        build(*args)


def test_missing_defaultdict_asset_group_does_not_become_zero():
    args = population()
    del args[3]["totals"]["base", "PS", "US", 2026]
    with pytest.raises(ValueError, match="asset basis population"):
        build(*args)


@pytest.mark.parametrize(
    "mutation", ["omit_account", "duplicate_account", "duplicate_journal", "changed_amount"]
)
def test_legal_book_population_reconciles_to_journal(mutation):
    args = population()
    result = args[0]
    if mutation == "omit_account":
        result["legal_trial_balance_rows"].pop(0)
    elif mutation == "duplicate_account":
        result["legal_trial_balance_rows"].append(dict(result["legal_trial_balance_rows"][0]))
    elif mutation == "duplicate_journal":
        result["journal_rows"].append(dict(result["journal_rows"][0]))
    else:
        result["legal_trial_balance_rows"][0]["signed_usd"] = "2"
    with pytest.raises(ValueError, match="[Dd]eferred-tax"):
        build(*args)
