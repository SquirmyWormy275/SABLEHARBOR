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


def build(result, parent, mine, assets, current, factors):
    balances = defaultdict(lambda: defaultdict(D))
    seen = set()
    for r in result["legal_trial_balance_rows"]:
        if int(r["month"]) == 12:
            identity = (r["scenario"], r["entity"], int(r["year"]), r["account"])
            if identity in seen:
                raise ValueError("Duplicate deferred legal trial-balance account")
            seen.add(identity)
            balances[r["scenario"], r["entity"], int(r["year"])][r["account"]] += D(r["signed_usd"])
    required = {
        (s, e, y)
        for s in ("base", "downside", "expansion")
        for e in ("SHI", "PS", "RWH", "ARU", "BST")
        for y in range(2026, 2032)
    }
    if not required.issubset(balances):
        raise ValueError("Incomplete year-end legal-book deferred-tax population")
    m = {(r["scenario"], r["jurisdiction"], r["year"]): r for r in mine}
    p = {(r["scenario"], r["year"]): r for r in parent.rows}
    federal = {(r["scenario"], r["taxpayer"], r["year"]): r for r in current["federal"]}
    states = {
        (r["scenario"], r["jurisdiction"], r["taxpayer"], r["year"]): r for r in current["states"]
    }
    factor = {
        (r["scenario"], r["jurisdiction"], r["member"], r["year"]): D(r["member_factor"])
        for r in factors
    }
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
