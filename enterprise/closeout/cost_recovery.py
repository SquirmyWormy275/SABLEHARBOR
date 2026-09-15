"""Annual tax cost-recovery workpapers; acquisition cost is never a cash-flow plug."""

from decimal import Decimal as D

Q = D(".0001")


def schedule(
    cost,
    service_year,
    service_month,
    life,
    *,
    bonus=False,
    building=False,
    straight_line=False,
    mid_quarter=False,
    last_year=2031,
):
    """Return annual allowance and basis, retaining convention and switch evidence.

    MACRS declining balance switches to straight line over convention-adjusted
    remaining life. Buildings use statutory midmonth. CA selected section167
    straight line uses actual service months, a disclosed separate model policy.
    """
    cost, life = D(str(cost)), D(str(life))
    if cost < 0 or life <= 0 or not 1 <= service_month <= 12:
        raise ValueError("Invalid tax cohort cost, life, or service month")
    if bonus and (building or life > 20):
        raise ValueError("Bonus cannot be assigned to a structural or >20-year cohort")
    if building:
        first_fraction = (D(12 - service_month) + D(".5")) / 12
    elif straight_line:
        first_fraction = D(13 - service_month) / 12
    elif mid_quarter:
        quarter = (service_month - 1) // 3 + 1
        first_fraction = (D(4 - quarter) + D(".5")) / 4
    else:
        first_fraction = D(".5")
    balance = cost
    used_life = D(0)
    result = []
    for year in range(service_year, last_year + 1):
        opening = balance
        elapsed = min(first_fraction if year == service_year else D(1), max(life - used_life, D(0)))
        remaining = life - used_life
        if bonus and year == service_year:
            allowance = cost
        elif balance == 0 or elapsed == 0:
            allowance = D(0)
        elif building or straight_line:
            allowance = min(balance, cost / life * elapsed)
        else:
            factor = D("1.5") if life in {D(15), D(20)} else D(2)
            annual = max(balance * factor / life, balance / remaining)
            allowance = min(balance, annual * elapsed)
        used_life += elapsed
        balance -= allowance
        result.append(
            dict(
                year=year,
                opening_tax_basis_usd=str(opening.quantize(Q)),
                tax_depreciation_usd=str(allowance.quantize(Q)),
                closing_tax_basis_usd=str(balance.quantize(Q)),
                convention="MID_MONTH"
                if building
                else "ACTUAL_SERVICE_MONTHS"
                if straight_line
                else "MID_QUARTER"
                if mid_quarter
                else "HALF_YEAR",
                bonus_selected=bonus,
            )
        )
    return result


def quarterly_test(cohorts):
    """40-percent convention test excludes nonresidential buildings and land."""
    denominator = sum(
        D(str(r["cost_usd"]))
        for r in cohorts
        if not r.get("building") and D(str(r["life_years"])) > 0
    )
    numerator = sum(
        D(str(r["cost_usd"]))
        for r in cohorts
        if not r.get("building") and D(str(r["life_years"])) > 0 and int(r["service_month"]) >= 10
    )
    return denominator > 0 and numerator / denominator > D(".4")
