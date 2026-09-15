"""Thirteen-week timing view from existing monthly books; no independent bank evidence."""

import argparse
import calendar
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_DOWN
from decimal import Decimal as D
from pathlib import Path

from industrial.planning.enterprise import read_csv, write_csv

START, END = date(2026, 9, 1), date(2026, 11, 30)


def spread(value, days):
    """Four-decimal source precision; last calendar day receives rounding residual."""
    value = D(value)
    each = (value / D(days)).quantize(D(".0001"), rounding=ROUND_DOWN)
    return [each] * (days - 1) + [value - each * (days - 1)]


def build(output):
    root = output / "enterprise"
    journal = read_csv(root / "enterprise_journal.csv")
    statements = read_csv(root / "enterprise_monthly_statements.csv")
    opening = {
        (r["scenario"], r["entity"]): D(r["ending_cash_usd"])
        for r in statements
        if (int(r["year"]), int(r["month"])) == (2026, 8)
    }
    closing = {
        (r["scenario"], r["entity"], int(r["month"])): D(r["ending_cash_usd"])
        for r in statements
        if r["year"] == "2026" and int(r["month"]) in {9, 10, 11}
    }
    selected = [
        r
        for r in journal
        if r["account"] == "1000" and r["year"] == "2026" and int(r["month"]) in {9, 10, 11}
    ]
    # Journal line identity is unique within scenario. Duplication must not become receipts.
    keys = [(r["scenario"], r["journal_id"], r["line_no"]) for r in selected]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate cash leg in treasury population")
    daily = defaultdict(lambda: defaultdict(D))
    lineage = []
    for r in selected:
        month = int(r["month"])
        count = calendar.monthrange(2026, month)[1]
        for i, value in enumerate(spread(r["signed_usd"], count)):
            day = date(2026, month, i + 1)
            for timing in ["UNIFORM_CALENDAR_ALLOCATION", "MEMBER_CASH_UNAVAILABLE"]:
                missing = (
                    timing == "MEMBER_CASH_UNAVAILABLE"
                    and r["entity"] == "SHI"
                    and r["source_type"] == "MEMBER_EQUITY"
                )
                fields = daily[timing, r["scenario"], r["entity"], day]
                if missing:
                    fields["unavailable_member_cash_usd"] += value
                    continue
                fields["receipts_usd" if value > 0 else "payments_signed_usd"] += value
                fields[r["cash_flow"].lower() + "_net_usd"] += value
                if r["entity"] == "SHI" and r["source_type"] == "MEMBER_EQUITY":
                    fields["member_cash_usd"] += value
        lineage.append(
            {
                k: r[k]
                for k in [
                    "scenario",
                    "entity",
                    "year",
                    "month",
                    "journal_id",
                    "line_no",
                    "source_id",
                    "source_type",
                    "cash_flow",
                    "signed_usd",
                    "available_at",
                    "fact_state",
                ]
            }
        )
    # Cancel internal source/flow cash legs before counting consolidated receipts/payments.
    # Source-level net allocation remains net where the accepted legal adapter supplies only net cash.
    consolidated = defaultdict(D)
    for r in selected:
        consolidated[r["scenario"], int(r["month"]), r["source_id"], r["cash_flow"]] += D(
            r["signed_usd"]
        )
    member_ids = {
        r["source_id"]
        for r in selected
        if r["entity"] == "SHI" and r["source_type"] == "MEMBER_EQUITY"
    }
    for (scenario, month, source_id, flow), amount in consolidated.items():
        for i, value in enumerate(spread(amount, calendar.monthrange(2026, month)[1])):
            for timing in ["UNIFORM_CALENDAR_ALLOCATION", "MEMBER_CASH_UNAVAILABLE"]:
                fields = daily[timing, scenario, "CONSOLIDATED", date(2026, month, i + 1)]
                if timing == "MEMBER_CASH_UNAVAILABLE" and source_id in member_ids:
                    fields["unavailable_member_cash_usd"] += value
                    continue
                fields["receipts_usd" if value > 0 else "payments_signed_usd"] += value
                fields[flow.lower() + "_net_usd"] += value
                if source_id in member_ids:
                    fields["member_cash_usd"] += value
    result = []
    month_checks = []
    for timing in ["UNIFORM_CALENDAR_ALLOCATION", "MEMBER_CASH_UNAVAILABLE"]:
        for (scenario, entity), initial in sorted(opening.items()):
            if entity == "ELIM":
                continue
            cash = initial
            cumulative_missing = D(0)
            for week in range(13):
                start = START + timedelta(days=week * 7)
                end = start + timedelta(days=6)
                values = defaultdict(D)
                week_open = cash
                minimum = cash
                for offset in range(7):
                    day = start + timedelta(days=offset)
                    flow = daily[timing, scenario, entity, day]
                    for key, value in flow.items():
                        values[key] += value
                    cash += flow["receipts_usd"] + flow["payments_signed_usd"]
                    minimum = min(minimum, cash)
                    cumulative_missing += flow["unavailable_member_cash_usd"]
                    if day.day == calendar.monthrange(day.year, day.month)[1]:
                        expected = closing[scenario, entity, day.month] - cumulative_missing
                        if cash != expected:
                            raise ValueError(
                                f"Month closing does not reconcile {timing}/{scenario}/{entity}/{day}: {cash} != {expected}"
                            )
                        month_checks.append(
                            dict(
                                timing_case=timing,
                                scenario=scenario,
                                entity=entity,
                                month=day.month,
                                monthly_source_closing_usd=str(
                                    closing[scenario, entity, day.month]
                                ),
                                unavailable_member_cash_cumulative_usd=str(cumulative_missing),
                                timing_closing_usd=str(cash),
                                difference_usd="0.0000",
                            )
                        )
                result.append(
                    dict(
                        timing_case=timing,
                        scenario=scenario,
                        entity=entity,
                        week=week + 1,
                        week_start=str(start),
                        week_end=str(end),
                        timezone="America/Los_Angeles",
                        opening_cash_usd=str(week_open),
                        receipts_usd=str(values["receipts_usd"]),
                        payments_usd=str(-values["payments_signed_usd"]),
                        closing_cash_usd=str(cash),
                        arithmetic_difference_usd=str(
                            week_open
                            + values["receipts_usd"]
                            + values["payments_signed_usd"]
                            - cash
                        ),
                        member_cash_usd=str(values["member_cash_usd"]),
                        unavailable_member_cash_usd=str(values["unavailable_member_cash_usd"]),
                        modeled_minimum_cash_usd=str(minimum),
                        liquidity_state="INFEASIBLE_WITHOUT_RESPONSE"
                        if minimum < 0
                        else "NO_NEGATIVE_UNDER_ASSUMED_TIMING",
                        **{
                            k: str(values[k])
                            for k in ["operating_net_usd", "investing_net_usd", "financing_net_usd"]
                        },
                        evidence_state="MONTHLY_MODEL_TIMING_SENSITIVITY_NOT_BANK_CONFIRMATION",
                        known_on="2026-09-15",
                        period_role="CONDITIONAL_FORECAST",
                        limitation="Uniform calendar timing; no daily sufficiency or verified payroll/tax/debt value dates; parent tax unresolved",
                    )
                )
    write_csv(output / "treasury_13week.csv", result)
    write_csv(output / "treasury_month_bridge.csv", month_checks)
    write_csv(output / "treasury_cash_population.csv", lineage)
    return {
        "weeks": 13,
        "start": str(START),
        "end": str(END),
        "rows": len(result),
        "selected_cash_legs": len(lineage),
        "monthly_checks": len(month_checks),
        "negative_week_rows": sum(
            r["liquidity_state"] == "INFEASIBLE_WITHOUT_RESPONSE" for r in result
        ),
        "source_sha256": hashlib.sha256((root / "enterprise_journal.csv").read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(json.dumps(build(a.output), indent=2))
