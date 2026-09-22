"""Gross temporary differences and bounded management-basis valuation allowances."""

from collections import defaultdict
from decimal import Decimal as D

Q = D(".0001")


def federal_valuation(nol, interest, pool):
    if any(
        v < 0
        for v in (
            nol,
            interest,
            pool["deductible"],
            pool["reserve"],
            pool["taxable"],
            pool["scheduled_taxable"],
        )
    ):
        raise ValueError("Negative gross deferred-tax source")
    if pool["scheduled_taxable"] > pool["taxable"]:
        raise ValueError("Realization capacity exceeds taxable difference")
    rate = D(".21")
    dta = (nol + interest + pool["deductible"] + pool["reserve"]) * rate
    dtl = pool["taxable"] * rate
    # A closing taxable-difference stock is not a net year-by-year reversal
    # schedule. Other deductible differences can consume the same capacity.
    # The management basis therefore reserves NOL benefit as well until that
    # net schedule substantiates realization; no future-profit plug is used.
    realized = D(0)
    return dta, dtl, dta - realized, realized


def opening(parent, mine, assets, current, history, historical_rot):
    """Pre-2026 SHI/PS differences only; ARU enters on its acquisition date."""
    rows = []
    parent_book = D(9000000) * (D(1) - D(3) / 7)
    parent_us = D(9000000) - D(7200000) - D(1800000) / 7 * D("2.5")
    parent_il = D(9000000) - D(9000000) / 7 * D("2.5")
    h = history["source"]
    rw_book = D(50000000) - D(history["book_dda_usd"])
    rw_book_inventory = D(6312500) + D(history["book_inventory_delta_usd"])
    mineral = D(history["rows"][0]["initial_mineral_basis_usd"]) - D(
        history["rows"][0]["deduction_depletion_usd"]
    )
    inventory_cash = D(history["cash_inventory_usd"]) + sum(
        D(v) for v in h["production_indirect_allocations"].values()
    ) * D(125000) / D(h["produced_lb"])
    for scenario in ("base", "downside", "expansion"):
        op = next(r for r in current["historical_state_openings"] if r["scenario"] == scenario)
        for jurisdiction in ("US", "CA", "IL", "WV"):
            asset = assets["totals"][scenario, "PS", jurisdiction, 2025]
            tax = asset["closing_tax_basis_usd"] + mineral + D(26000000) * D(2) / 42
            dda_stock = (
                asset["tax_depreciation_usd"]
                * (D(h["owned_days"]) - D(h["whole_pool_idle_days"]))
                / D(h["owned_days"])
                * D(125000)
                / D(h["produced_lb"])
            )
            deductible = (
                max(inventory_cash + dda_stock - rw_book_inventory, D(0))
                + D(16467716)
                + D(historical_rot)
            )
            taxable = max(rw_book - tax, D(0))
            parent_difference = max(
                parent_book
                - (
                    {"US": parent_us, "WV": parent_us, "IL": parent_il, "CA": parent_book}[
                        jurisdiction
                    ]
                ),
                D(0),
            )
            if jurisdiction == "US":
                rw_nol = D(
                    next(
                        r
                        for r in mine
                        if r["scenario"] == scenario
                        and r["jurisdiction"] == "US"
                        and r["year"] == 2026
                    )["opening_2026_loss_before_state_apportionment_usd"]
                )
                populations = (
                    (
                        "SHI",
                        (parent.opening_nol + D(12000000)) * D(".21"),
                        parent_difference * D(".21"),
                    ),
                    ("PS", (rw_nol + deductible) * D(".21"), taxable * D(".21")),
                )
            else:
                rate = {"CA": D(".0884"), "IL": D(".095"), "WV": D(".065")}[jurisdiction]
                entity = "PS" if jurisdiction == "IL" else "SHI"
                share = (
                    D(12600000) / D(117500000)
                    if jurisdiction == "IL"
                    else D(104900000) / D(117500000)
                    if jurisdiction == "CA"
                    else D(0)
                )
                nol = D(
                    op["il_ps_opening_2026_nol_usd"]
                    if jurisdiction == "IL"
                    else op["ca_shi_opening_2026_nol_usd"]
                    if jurisdiction == "CA"
                    else "0"
                )
                populations = (
                    (
                        entity,
                        (nol + deductible * share) * rate,
                        (taxable + parent_difference) * share * rate,
                    ),
                )
            for entity, dta, dtl in populations:
                rows.append(
                    dict(
                        scenario=scenario,
                        year=2026,
                        month=0,
                        taxpayer=entity,
                        jurisdiction=jurisdiction,
                        gross_dta_usd=str(dta.quantize(Q)),
                        valuation_allowance_usd=str(dta.quantize(Q)),
                        gross_dtl_usd=str(dtl.quantize(Q)),
                        net_deferred_asset_usd=str((-dtl).quantize(Q)),
                        method="HISTORICAL_OPENING_CORRECTION;FULL_VA;NO_ACQUISITION_GOODWILL_CHANGE",
                    )
                )
    return rows


def _index(rows, fields, expected, label):
    indexed = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in indexed:
            raise ValueError(f"Duplicate deferred-tax {label} source")
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError(f"Incomplete or unexpected deferred-tax {label} population")
    return indexed


def _year_end_balances(result):
    balances = defaultdict(lambda: defaultdict(D))
    seen = set()
    for row in result["legal_trial_balance_rows"]:
        if int(row["month"]) != 12:
            continue
        key = row["scenario"], row["entity"], int(row["year"]), row["account"]
        if key in seen:
            raise ValueError("Duplicate year-end legal-book deferred-tax account")
        seen.add(key)
        balances[key[:3]][key[3]] = D(row["signed_usd"])
    source = defaultdict(D)
    journal_seen = set()
    for row in result["journal_rows"]:
        identity = row["scenario"], row["journal_id"], row["line_no"]
        if identity in journal_seen:
            raise ValueError("Duplicate deferred-tax source journal leg")
        journal_seen.add(identity)
        for year in range(max(2026, int(row["year"])), 2032):
            source[row["scenario"], row["entity"], year, row["account"]] += D(row["signed_usd"])
    for key in set(source) | seen:
        if source[key].quantize(Q) != balances[key[:3]].get(key[3], D(0)).quantize(Q):
            raise ValueError(f"Year-end deferred-tax account differs from source journal: {key}")
    return balances


def build(result, parent, mine, assets, current, factors):
    scenarios = ("base", "downside", "expansion")
    years = range(2026, 2032)
    jurisdictions = ("US", "CA", "IL", "WV")
    members = ("SHI", "SHIH", "PS", "ARU", "BST")
    balances = _year_end_balances(result)
    required = {
        (s, e, y) for s in scenarios for e in ("SHI", "PS", "RWH", "ARU", "BST") for y in years
    }
    if not required.issubset(balances):
        raise ValueError("Incomplete year-end legal-book deferred-tax population")
    m = _index(
        mine,
        ("scenario", "jurisdiction", "year"),
        {(s, j, y) for s in scenarios for j in jurisdictions for y in years},
        "mine",
    )
    p = _index(
        parent.rows, ("scenario", "year"), {(s, y) for s in scenarios for y in years}, "parent"
    )
    federal = _index(
        current["federal"],
        ("scenario", "taxpayer", "year"),
        {(s, e, y) for s in scenarios for e in ("SHIH", "PS", "ARU", "BST") for y in years},
        "federal",
    )
    state_scope = {
        (s, j, e, y) for s in scenarios for j in ("CA", "IL", "WV") for e in members for y in years
    }
    states = _index(
        current["states"], ("scenario", "jurisdiction", "taxpayer", "year"), state_scope, "state"
    )
    factor_rows = _index(
        factors,
        ("scenario", "jurisdiction", "member", "year"),
        state_scope | {(s, "PA", "SHI", y) for s in scenarios for y in years},
        "factor",
    )
    factor = {key: D(row["member_factor"]) for key, row in factor_rows.items()}
    if any(not value.is_finite() or not 0 <= value <= 1 for value in factor.values()):
        raise ValueError("Invalid deferred-tax member factor")
    expected_assets = {
        (s, e, j, y)
        for s in scenarios
        for e in ("PS", "ARU", "BST")
        for j in jurisdictions
        for y in years
    }
    actual_assets = {key for key in assets["totals"] if 2026 <= key[3] <= 2031}
    if actual_assets != expected_assets:
        raise ValueError("Incomplete or unexpected deferred-tax asset basis population")
    for key in expected_assets:
        value = D(assets["totals"][key]["closing_tax_basis_usd"])
        if not value.is_finite() or value < 0:
            raise ValueError("Invalid deferred-tax closing asset basis")
    rows = []
    for scenario in ("base", "downside", "expansion"):
        parent_temporary = D(0)
        for year in range(2026, 2032):
            pr = p[scenario, year]
            parent_temporary += sum(
                D(pr[f])
                for f in (
                    "allowance_addback_usd",
                    "inventory_addback_usd",
                    "unpaid_transaction_tax_addback_usd",
                )
            )
            jurisdiction_pools = {}
            for jurisdiction in ("US", "CA", "IL", "WV"):
                pools = {}
                for entity in ("SHI", "PS", "ARU", "BST"):
                    b = balances[scenario, entity, year]
                    if entity == "SHI":
                        book = D(pr["book_asset_carrying_usd"])
                        if jurisdiction == "CA":
                            tax = D(pr["california_asset_basis_usd"])
                        elif jurisdiction == "IL":
                            from enterprise.closeout.statutory_current import parent_il_depreciation

                            opening = D(9000000) - D(9000000) / 7 * D("2.5")
                            added = sum(
                                D(r["cost"])
                                for r in parent.asset_rows
                                if r["scenario"] == scenario
                                and int(r["year"]) == int(r["placed_year"])
                                and 2026 <= int(r["year"]) <= year
                            )
                            tax = (
                                opening
                                + added
                                - sum(
                                    parent_il_depreciation(parent, scenario, y)
                                    for y in range(2026, year + 1)
                                )
                            )
                        else:
                            tax = D(pr["federal_asset_basis_usd"])
                        temporary = parent_temporary + (
                            D(pr["historical_research_basis_usd"]) if jurisdiction != "CA" else D(0)
                        )
                        reserve = land_difference = D(0)
                        inventory = D(0)
                    elif entity == "PS":
                        rb = balances[scenario, "RWH", year]
                        mr = m[scenario, jurisdiction, year]
                        book = rb["1400"] + rb["1410"] + rb["1490"]
                        tax = (
                            assets["totals"][scenario, "PS", jurisdiction, year][
                                "closing_tax_basis_usd"
                            ]
                            + D(mr["tax_mineral_basis_usd"])
                            + D(26000000) * D(2) / 42
                        )
                        land_difference = D(2000000) - D(26000000) * D(2) / 42
                        inventory = (
                            D(mr["tax_cash_inventory_usd"])
                            + D(mr["tax_dda_inventory_usd"])
                            - (rb["1200"] + rb["1210"] + balances[scenario, "ELIM", year]["1200"])
                        )
                        temporary = max(-rb["CO_RWH_ROT_PAY"], D(0)) + inventory
                        reserve = max(-rb["2200"], D(0))
                    else:
                        land = D(3600000) if entity == "ARU" else D(4400000)
                        book = b["1400"] + b["1410"] + b["1490"] + b["1500"] + b["1590"] - land
                        tax = assets["totals"][scenario, entity, jurisdiction, year][
                            "closing_tax_basis_usd"
                        ]
                        # Only the tax-deductible13M goodwill component creates
                        # subsequent amortization differences. Preserve original
                        # 1.7625M nondeductible book-goodwill component separately.
                        if entity == "ARU":
                            book += D(13000000)
                            tax += max(D(13000000) - D(13000000) / 180 * 12 * (year - 2025), D(0))
                            # Separate900kfacilitative AGUB successor, no bookGW addition.
                            tax += max(D(900000) - D(60000) * (year - 2025), D(0))
                        land_difference = D(0)
                        temporary = max(-b["2110"], D(0)) + max(-b["CO_PAYROLL_EMP_TAX_PAY"], D(0))
                        reserve = max(-b["2200"], D(0)) + max(-b["2300"], D(0))
                        inventory = D(0)
                    difference = book - tax
                    pools[entity] = dict(
                        taxable=max(difference, D(0)) + max(-temporary, D(0)),
                        deductible=max(-difference, D(0)) + max(temporary, D(0)),
                        reserve=reserve,
                        scheduled_taxable=max(difference - max(land_difference, D(0)), D(0)),
                        inventory=inventory,
                    )
                jurisdiction_pools[jurisdiction] = pools
            for entity in ("SHI", "PS", "ARU", "BST"):
                pool = jurisdiction_pools["US"][entity]
                f = pr if entity == "SHI" else federal[scenario, entity, year]
                nol = D(f["closing_federal_nol_usd"] if entity == "SHI" else f["closing_nol_usd"])
                interest = D(f["interest_carryforward_usd"])
                rate = D(".21")
                dta, dtl, va, realized = federal_valuation(nol, interest, pool)
                rows.append(
                    dict(
                        scenario=scenario,
                        year=year,
                        taxpayer=entity,
                        jurisdiction="US",
                        gross_dta_usd=str(dta.quantize(Q)),
                        gross_dtl_usd=str(dtl.quantize(Q)),
                        valuation_allowance_usd=str(va.quantize(Q)),
                        net_deferred_asset_usd=str((dta - va - dtl).quantize(Q)),
                        fully_reserved_aro_contingency_dta_usd=str(
                            (pool["reserve"] * rate).quantize(Q)
                        ),
                        recognized_nol_dta_usd=str(realized.quantize(Q)),
                        method="FULL_VA;NET_REVERSAL_YEAR_CAPACITY_NOT_ESTABLISHED;NO_FORECAST_PROFIT_SUPPORT;MANAGEMENT_BASIS",
                    )
                )
            for jurisdiction, rate in (("CA", D(".0884")), ("IL", D(".095")), ("WV", D(".065"))):
                pools = jurisdiction_pools[jurisdiction]
                taxable = sum(x["taxable"] for x in pools.values())
                deductible = sum(x["deductible"] + x["reserve"] for x in pools.values())
                for entity in ("SHI", "SHIH", "PS", "ARU", "BST"):
                    share = factor[scenario, jurisdiction, entity, year]
                    nol = D(states[scenario, jurisdiction, entity, year]["closing_member_nol_usd"])
                    dta = (nol + deductible * share) * rate
                    dtl = taxable * share * rate
                    rows.append(
                        dict(
                            scenario=scenario,
                            year=year,
                            taxpayer=entity,
                            jurisdiction=jurisdiction,
                            gross_dta_usd=str(dta.quantize(Q)),
                            gross_dtl_usd=str(dtl.quantize(Q)),
                            valuation_allowance_usd=str(dta.quantize(Q)),
                            net_deferred_asset_usd=str((-dtl).quantize(Q)),
                            fully_reserved_aro_contingency_dta_usd=str(
                                (sum(x["reserve"] for x in pools.values()) * share * rate).quantize(
                                    Q
                                )
                            ),
                            recognized_nol_dta_usd="0",
                            method="CURRENT_SOURCE_APPORTIONMENT_ESTIMATE;FULL_STATE_VA_PENDING_STABLE_REVERSAL_CAPACITY;MANAGEMENT_BASIS",
                        )
                    )
    return rows
