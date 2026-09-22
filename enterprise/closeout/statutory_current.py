"""Separate federal taxpayers and member-specific combined-state current tax.

Prepared September 21, 2026. Source workpapers retain their original dates.
This module calculates liabilities; it does not imply return submission/payment.
"""

from collections import defaultdict
from decimal import Decimal as D

from enterprise.closeout.acquisition_tax_costs import build as acquisition_costs
from enterprise.closeout.cost_recovery import schedule
from enterprise.closeout.tax_limits import illinois_nol_used

Q = D(".0001")
MEMBERS = ("SHI", "SHIH", "PS", "ARU", "BST")


def _index(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key in result:
            raise ValueError("Duplicate statutory source workpaper")
        result[key] = row
    return result


def parent_il_depreciation(parent, scenario, year):
    total = D(0)
    additions = defaultdict(lambda: [D(0), D(0)])
    for row in parent.asset_rows:
        if row["scenario"] == scenario and int(row["year"]) == int(row["placed_year"]):
            placed = int(row["placed_year"])
            additions[placed][0] += D(row["cost"])
            if int(row["placed_month"]) >= 10:
                additions[placed][1] += D(row["cost"])
    for row in parent.asset_rows:
        if row["scenario"] != scenario or int(row["year"]) != year:
            continue
        cost, placed = D(row["cost"]), int(row["placed_year"])
        if placed == 2023:
            elapsed = year - placed
            total += cost / 7 * (D(".5") if elapsed in (0, 7) else D(1)) if elapsed <= 7 else D(0)
        else:
            # Newly authored equipment-class precision: <=5-year management
            # equipment lives use five-year GDS; longer selected equipment seven.
            life = 5 if int(row["life_months"]) <= 60 else 7
            population, q4 = additions[placed]
            periods = schedule(
                cost,
                placed,
                int(row["placed_month"]),
                life,
                mid_quarter=bool(population and q4 / population > D(".40")),
            )
            total += sum(D(p["tax_depreciation_usd"]) for p in periods if p["year"] == year)
    return total


def build(parent, aru, mine, factors, journal_rows, state_cash_paid=None):
    state_cash_paid = state_cash_paid or {}
    ar = _index(aru["rows"], ("scenario", "taxpayer", "jurisdiction", "year"))
    rw = _index(mine, ("scenario", "jurisdiction", "year"))
    pa = _index(parent.rows, ("scenario", "year"))
    sf = _index(factors, ("scenario", "jurisdiction", "member", "year"))
    expected = {
        (s, e, j, y)
        for s in ("base", "downside", "expansion")
        for e in ("ARU", "BST")
        for j in ("US", "CA", "IL", "WV")
        for y in range(2026, 2032)
    }
    if set(ar) != expected or len(rw) != 72 or len(pa) != 18 or len(sf) != 288:
        raise ValueError("Incomplete statutory current-tax population")
    acquisition = acquisition_costs()
    fee = D(acquisition["additional_class_vii_usd"])
    amort = D(acquisition["annual_additional_amortization_usd"])
    holding = defaultdict(D)
    fee_book = defaultdict(D)
    for r in journal_rows:
        if (
            r["entity"] == "SHIH"
            and int(r["month"]) > 0
            and r["account_type"] in ("expense", "revenue")
        ):
            if r["account"] not in (
                "SHARED_EXP",
                "SHARED_REV",
                "5900",
                "5500",
                "5501",
                "CO_STATE_MIN_EXP",
            ):
                holding[r["scenario"], int(r["year"])] -= D(r["signed_usd"])
                if r["account"] == "5800" and int(r["year"]) == 2026:
                    fee_book[r["scenario"]] += D(r["signed_usd"])
    for scenario in ("base", "downside", "expansion"):
        if fee_book[scenario] != fee:
            raise ValueError("Acquisition fee book population differs from capitalized source")
        holding[scenario, 2026] += fee
    federal, states, openings = [], [], []
    federal_by_key = {}
    for scenario in ("base", "downside", "expansion"):
        for entity in ("SHIH", "PS", "ARU", "BST"):
            nol = (
                D(rw[scenario, "US", 2026]["opening_2026_loss_before_state_apportionment_usd"])
                if entity == "PS"
                else D(0)
            )
            interest_cf = D(0)
            for year in range(2026, 2032):
                if entity == "SHIH":
                    base = holding[scenario, year]
                    interest = deduction = ati = D(0)
                elif entity == "PS":
                    base = D(rw[scenario, "US", year]["income_before_nol_usd"])
                    interest = deduction = ati = D(0)
                else:
                    source = ar[scenario, entity, "US", year]
                    base = D(source["income_before_interest_limit_usd"]) - (
                        amort if entity == "ARU" else D(0)
                    )
                    interest = D(source["eligible_interest_expense_usd"])
                    ati = max(
                        base
                        + D(source["tax_depreciation_allowance_usd"])
                        + D(source["tax_goodwill_amortization_usd"])
                        + (amort if entity == "ARU" else D(0)),
                        D(0),
                    )
                    deduction = min(interest + interest_cf, ati * D(".30"))
                    interest_cf += interest - deduction
                    base -= deduction
                state_deduction = D(state_cash_paid.get((scenario, entity, year), 0))
                if not state_deduction.is_finite() or state_deduction < 0:
                    raise ValueError("Invalid actual state income-tax cash deduction")
                base -= state_deduction
                used = min(nol, max(base, D(0)) * D(".80"))
                opening = nol
                nol += max(-base, D(0)) - used
                row = dict(
                    scenario=scenario,
                    taxpayer=entity,
                    jurisdiction="US",
                    year=year,
                    income_before_nol_usd=str(base.quantize(Q)),
                    opening_nol_usd=str(opening.quantize(Q)),
                    nol_used_usd=str(used.quantize(Q)),
                    closing_nol_usd=str(nol.quantize(Q)),
                    interest_current_usd=str(interest.quantize(Q)),
                    interest_deducted_usd=str(deduction.quantize(Q)),
                    interest_carryforward_usd=str(interest_cf.quantize(Q)),
                    ati_usd=str(ati.quantize(Q)),
                    current_tax_usd=str(((max(base, D(0)) - used) * D(".21")).quantize(Q)),
                    state_income_tax_paid_deduction_usd=str(state_deduction),
                    filing_state="MODELED_WORKPAPER_NOT_SUBMITTED",
                    payment_state="JOIN_SEPARATE_SETTLEMENT_POPULATION",
                )
                federal.append(row)
                federal_by_key[scenario, entity, year] = row
        # 2025 unitary history precedes the ARU acquisition. The inherited SHI
        # loss includes its standalone 2025 loss; replace that component only.
        ca_parent_2025 = D(parent.historical_income["2025"]) - D(9000000) / 7
        ca_mine_2025 = -D(
            rw[scenario, "CA", 2026]["opening_2026_loss_before_state_apportionment_usd"]
        )
        ca_group_2025 = ca_parent_2025 + ca_mine_2025
        ca_loss = max(-ca_group_2025 * D("104900000") / D("117500000"), D(0))
        ca_parent_opening = parent.opening_state_nol - max(-ca_parent_2025, D(0)) + ca_loss
        il_parent_2025 = D(parent.historical_income["2025"]) - D(9000000) / 7 - D(8000000)
        il_mine_2025 = -D(
            rw[scenario, "IL", 2026]["opening_2026_loss_before_state_apportionment_usd"]
        )
        il_loss = max(-(il_parent_2025 + il_mine_2025) * D("12600000") / D("117500000"), D(0))
        balances = defaultdict(D, {("CA", "SHI"): ca_parent_opening, ("IL", "PS"): il_loss})
        openings.append(
            dict(
                scenario=scenario,
                year=2025,
                ca_combined_income_usd=str(ca_group_2025.quantize(Q)),
                ca_shi_allocated_loss_usd=str(ca_loss.quantize(Q)),
                ca_shi_opening_2026_nol_usd=str(ca_parent_opening.quantize(Q)),
                il_ps_opening_2026_nol_usd=str(il_loss.quantize(Q)),
                fact_status="NEWLY_AUTHORED_HISTORICAL_FUNCTIONAL_CONTINUITY_AND_MARKET_SOURCE;NOT_FILED_RETURN",
            )
        )
        for year in range(2026, 2032):
            p = pa[scenario, year]
            common = sum(
                D(p[f])
                for f in (
                    "book_pretax_usd",
                    "book_depreciation_usd",
                    "allowance_addback_usd",
                    "inventory_addback_usd",
                    "unpaid_transaction_tax_addback_usd",
                    "book_only_service_fee_reversal_usd",
                )
            )
            for jurisdiction in ("CA", "IL", "WV"):
                depreciation = (
                    D(p["california_depreciation_usd"])
                    if jurisdiction == "CA"
                    else parent_il_depreciation(parent, scenario, year)
                    if jurisdiction == "IL"
                    else D(p["federal_depreciation_usd"])
                )
                parent_base = common - depreciation
                if jurisdiction != "CA":
                    parent_base -= D(p["historical_research_amortization_usd"])
                    parent_base += D(p["interest_usd"]) - D(p["interest_deducted_usd"])
                group = (
                    parent_base
                    + holding[scenario, year]
                    + D(rw[scenario, jurisdiction, year]["income_before_nol_usd"])
                )
                for entity in ("ARU", "BST"):
                    r = ar[scenario, entity, jurisdiction, year]
                    deduction = (
                        D(r["eligible_interest_expense_usd"])
                        if jurisdiction == "CA"
                        else D(federal_by_key[scenario, entity, year]["interest_deducted_usd"])
                    )
                    group += (
                        D(r["income_before_interest_limit_usd"])
                        - deduction
                        - (amort if entity == "ARU" else D(0))
                    )
                for entity in MEMBERS:
                    f = sf[scenario, jurisdiction, entity, year]
                    apportioned = group * D(f["member_factor"])
                    positive = max(apportioned, D(0))
                    loss = balances[jurisdiction, entity]
                    if jurisdiction == "IL":
                        used = illinois_nol_used(year, positive, loss)
                    elif jurisdiction == "WV":
                        used = min(loss, positive * D(".8"))
                    else:
                        used = D(0) if year == 2026 and positive >= 1000000 else min(loss, positive)
                    balances[jurisdiction, entity] += max(-apportioned, D(0)) - used
                    rate = {"CA": D(".0884"), "IL": D(".095"), "WV": D(".065")}[jurisdiction]
                    minimum = (
                        D(800) if jurisdiction == "CA" and entity in ("SHI", "SHIH", "PS") else D(0)
                    )
                    tax = max(minimum, (positive - used) * rate)
                    states.append(
                        dict(
                            scenario=scenario,
                            year=year,
                            jurisdiction=jurisdiction,
                            taxpayer=entity,
                            group_income_before_apportionment_usd=str(group.quantize(Q)),
                            member_factor=f["member_factor"],
                            apportioned_income_before_nol_usd=str(apportioned.quantize(Q)),
                            opening_member_nol_usd=str(loss.quantize(Q)),
                            member_nol_used_usd=str(used.quantize(Q)),
                            closing_member_nol_usd=str(balances[jurisdiction, entity].quantize(Q)),
                            current_tax_usd=str(tax.quantize(Q)),
                            minimum_tax_usd=str(minimum),
                            filing_state="COMBINED_MEMBER_WORKPAPER_NOT_SUBMITTED",
                            payment_state="JOIN_SEPARATE_SETTLEMENT_POPULATION",
                        )
                    )
    return dict(
        federal=federal,
        states=states,
        historical_state_openings=openings,
        acquisition_cost_basis=acquisition,
    )
