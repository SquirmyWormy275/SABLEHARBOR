"""Existing retention awards in compensation YTD, separate from new salaries."""

from decimal import Decimal as D

SOURCE = "enterprise/operations/source/retention_payroll_2026.json"


def awards_by_name():
    from .completed_period import read

    return {
        name: D(value) / 2
        for name, value in read("industrial/source/finance.json")["transaction"][
            "retention_allocations"
        ].items()
    }


def prior_bonus(person):
    return awards_by_name().get(person.get("name"), D(0))


def workpapers(source, people):
    from .completed_period import cents, money, read, stamp, withholding

    policy = read(SOURCE)
    if policy["bonus_paid_on"] != "2026-07-07" or D(policy["federal_supplemental_rate"]) != D(
        ".22"
    ):
        raise ValueError("Retention payroll source date or supplemental rate changed")
    names = awards_by_name()
    selected = {p["name"]: p for p in people if p["name"] in names}
    if set(selected) != set(names):
        raise ValueError("Retention employee population missing")
    events = []
    for name, person in selected.items():
        if person["jurisdiction"] != "WY":
            raise ValueError("Retention jurisdiction requires a new tax workpaper")
        monthly = cents(D(person["annual_salary_usd"]) / 12)
        ytd = D(0)
        for month in range(1, 9):
            payments = [
                ("REGULAR_1", cents(monthly / 2)),
                ("REGULAR_2", monthly - cents(monthly / 2)),
            ]
            if month == 7:
                payments.insert(0, ("RETENTION", names[name]))
            for kind, gross in payments:
                taxes = withholding(
                    gross, ytd, person["jurisdiction"], person["legal_employer"] == "BST"
                )
                if kind == "RETENTION":
                    taxes["federal_income"] = cents(gross * D(".22"))
                employee = sum(
                    value for key, value in taxes.items() if key != "employer_known_taxes"
                )
                events.append(
                    stamp(
                        source,
                        event_id=f"SH-YTD-{person['person_id']}-2026{month:02}-{kind}",
                        person_id=person["person_id"],
                        employee_name=name,
                        legal_entity=person["legal_employer"],
                        event_period=f"2026-{month:02}",
                        payment_kind=kind,
                        opening_ytd_usd=money(ytd),
                        gross_usd=money(gross),
                        closing_ytd_usd=money(ytd + gross),
                        employee_withholding_usd=money(employee),
                        employee_net_usd=money(gross - employee),
                        employer_known_taxes_usd=money(taxes["employer_known_taxes"]),
                        tax_components={key: money(value) for key, value in taxes.items()},
                        settlement_basis="EXISTING_GROSS_SOURCE_BATCH_EMPLOYEE_NET_PLUS_WITHHOLDING"
                        if kind == "RETENTION"
                        else "REGULAR_SALARY_YTD_RECONSTRUCTION",
                        employer_bonus_settlement_state=policy["employer_bonus_levy_state"]
                        if kind == "RETENTION"
                        else "WITHIN_EXISTING_REGULAR_SALARY_BURDEN",
                    )
                )
                events[-1]["effective_period"] = f"2026-{month:02}"
                if kind == "RETENTION":
                    events[-1].update(
                        paid_on=policy["bonus_paid_on"],
                        source_id="RETENTION-PAYMENT",
                        payment_ref=f"SH-SYN-RETENTION-20260707-{person['person_id']}",
                        employee_withholding_remitted_on=policy["bonus_paid_on"],
                        employer_levy_paid_usd="0.00",
                        employer_levy_disposition="FINANCE_SUCCESSOR_CONTROLS_NO_PAYMENT_INFERRED",
                    )
                ytd += gross
    return events


def validate(tables):
    from .completed_period import SOURCE as PERIOD_SOURCE
    from .completed_period import read

    expected = workpapers(read(PERIOD_SOURCE), tables["people"])
    actual = tables["retention_payroll_ytd"]
    fields = [
        "event_id",
        "person_id",
        "legal_entity",
        "event_period",
        "effective_period",
        "payment_kind",
        "opening_ytd_usd",
        "gross_usd",
        "closing_ytd_usd",
        "employee_withholding_usd",
        "employee_net_usd",
        "employer_known_taxes_usd",
        "tax_components",
        "paid_on",
        "source_id",
        "employee_withholding_remitted_on",
        "employer_levy_paid_usd",
    ]
    if [{key: r.get(key) for key in fields} for r in actual] != [
        {key: r.get(key) for key in fields} for r in expected
    ]:
        raise ValueError("Retention compensation/YTD/tax population differs from source")
    opening = {
        r["person_id"]: r["opening_ytd_usd"]
        for r in actual
        if r["event_period"] == "2026-08" and r["payment_kind"] == "REGULAR_1"
    }
    for row in tables["payroll"]:
        if (
            row["person_id"] in opening
            and row["pay_date"].endswith("-14")
            and D(row["opening_ytd_wages_usd"]) != D(opening[row["person_id"]])
        ):
            raise ValueError("August payroll omitted July retention wages")
    bonus = [r for r in actual if r["payment_kind"] == "RETENTION"]
    from industrial.planning.enterprise import load_anchor

    gross = sum(D(r["gross_usd"]) for r in bonus)
    source_cash = -sum(
        D(r["signed_usd"])
        for r in load_anchor()
        if r["entity"] == "ARU_GROUP"
        and int(r["year"]) == 2026
        and int(r["month"]) == 7
        and r["source_id"] == "RETENTION-PAYMENT"
        and r["account"] == "1000"
    )
    if gross != source_cash:
        raise ValueError("Retention gross settlement differs from existing source cash")
    return {
        "retention_recipients": len(bonus),
        "ytd_payment_events": len(actual),
        "gross_bonus_usd": str(sum(D(r["gross_usd"]) for r in bonus)),
        "employee_bonus_net_usd": str(sum(D(r["employee_net_usd"]) for r in bonus)),
        "employee_bonus_withholding_usd": str(sum(D(r["employee_withholding_usd"]) for r in bonus)),
        "employer_bonus_levy_usd": str(sum(D(r["employer_known_taxes_usd"]) for r in bonus)),
    }
