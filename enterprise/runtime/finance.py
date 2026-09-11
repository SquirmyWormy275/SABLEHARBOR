"""Explicit runtime adjustment adapter; predecessor books remain reproducible."""

from decimal import Decimal as D
from . import model, planning


class RuntimeAdjustment:
    account_types = {
        "RT_LAND": "asset",
        "RT_SETTLEMENT_UNRESOLVED": "liability",
        "RT_CIP": "asset",
        "RT_IT": "asset",
        "RT_IT_ACCUM": "asset",
        "RT_EXPENSE": "expense",
        "RT_DDA": "expense",
    }

    def __init__(self, data=None):
        self.data = data if data is not None else model.load()
        model.validate(self.data)
        self.finance = planning.finance(self.data)
        self.monthly = {
            (r["scenario"], r["year"], r["month"]): r for r in self.finance["monthly"]
        }
        self.case_map = {
            "base": "base",
            "downside": "slower_adoption",
            "expansion": "high_demand",
        }
        self.input_hash = model.export(self.data)["source_sha256"]

    def post_month(self, books, year, month):
        if (year, month) == (2026, 9):
            books.post(
                "SHI",
                year,
                month,
                [("RT_LAND", D(3000000)), ("RT_SETTLEMENT_UNRESOLVED", D(-3000000))],
                "RT-LAND-20260904",
                "Synthetic land effective September 4; recorded September 11; settlement unresolved, no cash or vendor financing asserted",
                kind="RUNTIME_DATED_RECONCILIATION_ADJUSTMENT",
            )
        if year < 2027:
            return
        scenario = self.case_map[books.scenario]
        row = self.monthly[(scenario, year, month)]
        for field, account, flow in [
            ("facility_cash_request", "RT_CIP", "INVESTING"),
            ("hardware_cash_request", "RT_IT", "INVESTING"),
            ("operating_cash_request", "RT_EXPENSE", "OPERATING"),
        ]:
            value = D(row[field]).quantize(D(".0001"))
            if value:
                books.post(
                    "SHI",
                    year,
                    month,
                    [(account, value), ("1000", -value, flow)],
                    f"RT-FORECAST-{field}-{year}-{month}",
                    "Conditional runtime gross cash request; Treasury limits apply; not an actual contract, invoice, payroll or paid cash",
                    kind="RUNTIME_CONDITIONAL_FORECAST_REQUEST",
                )
        depreciation = D(0)
        for (case, y, m), cohort in self.monthly.items():
            age = (year - y) * 12 + month - m
            if case == scenario and 0 < age <= 48:
                depreciation += D(cohort["hardware_cash_request"]) / 48
        depreciation = depreciation.quantize(D(".0001"))
        if depreciation:
            books.post(
                "SHI",
                year,
                month,
                [("RT_DDA", depreciation), ("RT_IT_ACCUM", -depreciation)],
                f"RT-FORECAST-IT-DDA-{year}-{month}",
                "Conditional IT acceptance in acquisition month; depreciation following month. Land/CIP are not depreciated.",
                kind="RUNTIME_CONDITIONAL_FORECAST_REQUEST",
            )


def verify_land_adjustment(rows):
    """Independently reconcile emitted journal legs; do not trust output totals."""
    selected = [r for r in rows if r["source_id"] == "RT-LAND-20260904"]
    groups = {}
    for r in selected:
        groups.setdefault(r["scenario"], []).append(r)
    if not groups:
        raise ValueError("Runtime land adjustment ignored by enterprise generator")
    for scenario, legs in groups.items():
        values = {r["account"]: D(r["signed_usd"]) for r in legs}
        if len(legs) != 2 or values != {
            "RT_LAND": D(3000000),
            "RT_SETTLEMENT_UNRESOLVED": D(-3000000),
        }:
            raise ValueError("Land posted incorrectly or more than once")
        if any(
            r["entity"] != "SHI" or int(r["year"]) != 2026 or int(r["month"]) != 9
            for r in legs
        ):
            raise ValueError("Land date/entity mismatch")
    return {
        "scenarios": sorted(groups),
        "balanced_land_adjustment": "3000000.0000",
        "cash_paid": "0.0000",
        "settlement": "UNRESOLVED_NOT_VENDOR_FINANCING",
    }
