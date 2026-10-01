"""Newly authored August platform work allocation inside existing paid payroll."""

import json
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("source") / "production_support_2026_08.json"


def rows(tables):
    source = json.loads(SOURCE.read_text())
    people = {r["source_person_id"]: r for r in tables["people"] if r["legal_employer"] == "PS"}
    allocation = source["people"]
    if len(allocation) != len(people) or {r["source_person_id"] for r in allocation} != set(people):
        raise ValueError("PS production-support employee population differs")
    result = []
    for row in allocation:
        person = people[row["source_person_id"]]
        time = next(r for r in tables["time"] if r["person_id"] == person["person_id"])
        payroll = [r for r in tables["payroll"] if r["person_id"] == person["person_id"]]
        cost = sum(D(r["gross_usd"]) + D(r["employer_burden_usd"]) for r in payroll)
        fraction = D(row["production_fraction"])
        if not 0 <= fraction <= 1:
            raise ValueError("Invalid production-support share")
        production = (cost * fraction).quantize(D(".01"))
        result.append(
            dict(
                allocation_id="PS-AUG-WORK-" + person["person_id"],
                person_id=person["person_id"],
                legal_employer="PS",
                effective_period="2026-08",
                activity=row["activity"],
                time_id=time["time_id"],
                worked_hours=time["worked_hours"],
                production_support_hours=str(D(time["worked_hours"]) * fraction),
                other_work_hours=str(D(time["worked_hours"]) * (1 - fraction)),
                production_fraction=str(fraction),
                loaded_payroll_usd=str(cost),
                production_support_payroll_usd=str(production),
                selling_corporate_payroll_usd=str(cost - production),
                allocation_basis=source["basis"],
                source_path=str(SOURCE.relative_to(SOURCE.parents[3])),
                additional_expense_or_cash_usd="0.00",
            )
        )
    return result


def extend(source, tables):
    from .completed_period import stamp

    tables["production_support_work"] = [dict(stamp(source), **r) for r in rows(tables)]


def validate(tables):
    expected = rows(tables)
    actual = tables["production_support_work"]
    if len(actual) != len(expected):
        raise ValueError("Production-support population omitted or duplicated")
    for a, e in zip(actual, expected, strict=True):
        if any(a[k] != v for k, v in e.items()):
            raise ValueError("Production-support work/payroll allocation differs")
    return dict(
        employees=len(expected),
        loaded_payroll_usd=str(sum(D(r["loaded_payroll_usd"]) for r in expected)),
        production_support_payroll_usd=str(
            sum(D(r["production_support_payroll_usd"]) for r in expected)
        ),
        selling_corporate_payroll_usd=str(
            sum(D(r["selling_corporate_payroll_usd"]) for r in expected)
        ),
    )
