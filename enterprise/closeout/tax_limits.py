"""Period-specific loss limits used by the company statutory workpapers."""

from decimal import Decimal as D


def illinois_nol_used(year, income, available_loss):
    """Calendar-year corporate limit, 35 ILCS 5/207(d), PA104-0468.

    Inputs are Illinois income before its loss deduction and the relevant
    taxpayer's available Illinois loss. This function does not pool members.
    """
    if type(year) is not int or not 2024 <= year <= 2031:
        raise ValueError("Illinois loss limit outside declared edition years")
    income, available_loss = D(income), D(available_loss)
    if not income.is_finite() or not available_loss.is_finite() or available_loss < 0:
        raise ValueError("Invalid Illinois income or loss population")
    income = max(income, D(0))
    percentages = {2027: ".15", 2028: ".30", 2029: ".50", 2030: ".65", 2031: ".80"}
    limit = max(D(500000), income * D(percentages.get(year, "0")))
    return min(income, available_loss, limit)
