"""Retrospective August employee reconstruction and operating evidence input.

This extends the operations package without mutating the 2027 scenario roster or
immutable industrial books. Authored history and current repository acceptance are
separate. A payroll subledger is not a second independent bank confirmation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

from .availability import apply as apply_availability
from .availability import queryable

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "enterprise/operations/source/completed_period_2026_08.json"
OUTPUT = ROOT / "enterprise/generated/completed-period-2026-08"
CENT = D(".01")


def cents(value):
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money(value):
    return format(cents(value), ".2f")


def read(path):
    return json.loads((ROOT / path).read_text())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def graduated(value, table):
    value = max(D(0), D(value))
    lower, base, rate = next(row for row in reversed(table) if value >= D(row[0]))
    return D(base) + (value - D(lower)) * D(rate)


FEDERAL = [
    ("0", "0", "0"),
    ("7500", "0", ".10"),
    ("19900", "1240", ".12"),
    ("57900", "5800", ".22"),
    ("113200", "17966", ".24"),
    ("209275", "41024", ".32"),
    ("263725", "58448", ".35"),
    ("648100", "192979.25", ".37"),
]
CA = [
    ("0", "0", ".011"),
    ("462", "5.08", ".022"),
    ("1094", "18.98", ".044"),
    ("1727", "46.83", ".066"),
    ("2398", "91.12", ".088"),
    ("3030", "146.74", ".1023"),
    ("15478", "1420.17", ".1133"),
    ("18574", "1770.95", ".1243"),
    ("30956", "3310.03", ".1353"),
    ("41667", "4759.23", ".1463"),
]
WV = [
    ("0", "0", ".0211"),
    ("417", "8.80", ".0281"),
    ("1042", "26.36", ".0316"),
    ("1667", "46.11", ".0422"),
    ("2500", "81.26", ".0458"),
]


def withholding(gross, ytd, state, railroad=False):
    """One semimonthly payment; gross/YTD are explicit taxable compensation."""
    gross, ytd = D(gross), D(ytd)
    if gross < 0 or ytd < 0 or state not in {"CA", "PA", "WV", "WY"}:
        raise ValueError("Unsupported wage or jurisdiction")
    ss = cents(min(gross, max(D(0), D("184500") - ytd)) * D(".062"))
    medicare = cents(gross * D(".0145"))
    additional = cents(
        (max(D(0), ytd + gross - D("200000")) - max(D(0), ytd - D("200000"))) * D(".009")
    )
    fed = cents(graduated(gross * 24 - 8600, FEDERAL) / 24)
    state_tax = disability = local = tier2 = D(0)
    if state == "CA":
        state_tax = cents(graduated(gross - 238, CA)) if gross > 787 else D(0)
        disability = cents(gross * D(".013"))
    elif state == "PA":
        state_tax = cents(gross * D(".0307"))
        disability = cents(gross * D(".0007"))
        local = cents(gross * D(".03")) + cents(D(52) / 24)
    elif state == "WV":
        state_tax = cents(graduated(gross, WV))
    tier2_base = min(gross, max(D(0), D("137100") - ytd)) if railroad else D(0)
    tier2 = cents(tier2_base * D(".049"))
    employer = ss + medicare + cents(tier2_base * D(".131"))
    return dict(
        federal_income=fed,
        social_or_tier1=ss,
        medicare=medicare,
        additional_medicare=additional,
        tier2=tier2,
        state_income=state_tax,
        state_employee_contribution=disability,
        local=local,
        employer_known_taxes=employer,
    )


def stamp(source, **values):
    return dict(
        record_origin="PUBLIC_SYNTHETIC_DIEGETIC",
        fact_state=source["fact_state"],
        scenario=source["scenario"],
        effective_period=source["effective_period"],
        available_at=source["available_at"],
        recorded_at=source["recorded_at"],
        acceptance_state=source["acceptance_state"],
        access_scope="PUBLIC_SYNTHETIC",
        **values,
    )


def make_roster(source):
    chart = read("docs/organization/source/chartbook.json")
    named = {
        p["person_id"]: p
        for p in chart["nodes"]
        if p.get("type") == "person" and p.get("status") == "current_employee"
    }
    names = {p["name"]: pid for pid, p in named.items()}
    people, positions, links = [], [], []

    def add(pid, source_id, entity, unit, state, salary, title, group, basis):
        person = named.get(pid, {})
        position = f"SH-POS-{source_id}"
        people.append(
            stamp(
                source,
                person_id=pid,
                name=person.get("name", source.get("authored_names", {}).get(pid, "")),
                source_person_id=source_id,
                legal_employer=entity,
                unit=unit,
                jurisdiction=state,
                position_id=position,
                position_title=person.get("title", title),
                fte="1.00",
                status="ACTIVE",
                effective_from="2026-08-01",
                effective_to=None,
                effective_date_basis="Opening August reconstruction, not original hire/appointment",
                annual_salary_usd=money(salary),
                compensation_basis="SALARY_40_HOUR_WEEK",
                annual_salary_basis=basis,
                population_group=group,
                original_hire_year=person.get("joined_year"),
                manager_role="UNIT_ACCOUNTABLE_MANAGER",
                qualification_state="ROLE_TRAINING_REQUIRED; see qualifications",
                residence_basis="NEWLY_AUTHORED_RESIDENCE_IN_WORK_STATE",
                allocation_fte="1.00",
                allocation_unit=unit,
            )
        )
        positions.append(
            stamp(
                source,
                position_id=position,
                unit=unit,
                legal_entity=entity,
                authorized=True,
                occupancy="OCCUPIED",
                person_id=pid,
            )
        )
        links.append(
            stamp(
                source,
                person_id=pid,
                source_person_id=source_id,
                relationship="SAME_PERSON_NOT_ADDITIONAL_HEADCOUNT",
            )
        )

    for group in source["core_groups"] + source["j2_groups"]:
        for n in range(1, group["occupied"] + 1):
            sid = f"SH-EMP-{group['unit'].upper()}-{n:04d}"
            pid = group["named_people"][n - 1] if n <= len(group["named_people"]) else sid
            salary = D(group["annual_salary_usd"])
            if pid in group["named_people"]:
                salary *= D("1.25")
            add(
                pid,
                sid,
                "SHI",
                group["unit"],
                group["jurisdiction"],
                salary,
                f"{group['unit']} staff {n}",
                "CORE_RECONSTRUCTED",
                "NEWLY_AUTHORED_ROLE_BAND",
            )
        for n in range(group["occupied"] + 1, group.get("authorized", group["occupied"]) + 1):
            positions.append(
                stamp(
                    source,
                    position_id=f"SH-POS-SH-EMP-{group['unit'].upper()}-{n:04d}",
                    unit=group["unit"],
                    legal_entity="SHI",
                    authorized=True,
                    occupancy="VACANT_IN_AUTHORED_RECONSTRUCTION",
                    person_id=None,
                )
            )
    finance = read("industrial/source/finance.json")
    for row in finance["employees"]:
        sid = row["employee_id"]
        pid = names.get(row["name"], sid)
        add(
            pid,
            sid,
            "BST" if row["segment"] == "BST" else "ARU",
            row["segment"],
            "WY",
            D(row["annual_salary_usd"]) * D("1.03"),
            row["role"],
            "ARU_BST_SELECTED",
            "industrial/source/finance.json annual_salary_usd x accepted 2026 cost index1.03",
        )
    workforce = read("red_wash/source/core_operating_data.json")["workforce_2026"]
    groups = [("PS", "platform", workforce["pale_sun_business_layer"])]
    groups += [("RWH", name, count) for name, count in workforce["site_functions"].items()]
    index = 0
    for entity, unit, count in groups:
        for _n in range(count):
            index += 1
            sid = f"RW-{index:04d}"
            pid = source["industrial_person_links"].get(sid, sid)
            salary = D(
                source["payroll"][
                    "platform_annual_salary_usd" if entity == "PS" else "mine_annual_salary_usd"
                ]
            )
            if pid in named:
                salary *= D("1.25")
            add(
                pid,
                sid,
                entity,
                unit,
                "CA" if entity == "PS" else "WY",
                salary,
                f"{unit} position {n + 1}",
                "PS_RWH_SELECTED",
                "NEWLY_AUTHORED_ROLE_BAND",
            )
    directors = {
        p["person_id"]: p
        for p in chart["nodes"]
        if p.get("type") == "person" and p.get("status") == "current_nonemployee_director"
    }
    # The existing bridge distinguishes directors reliably even if chart status vocabulary changes.
    from_bridge = read("geospatial/facilities/population/REGISTER.json")
    directors = {
        p["person_id"]: p
        for p in from_bridge["people"]
        if p["status"] == "current_nonemployee_director"
    } or directors
    nonemployees = [
        stamp(
            source,
            person_id=pid,
            name=p["name"],
            kind="NONEMPLOYEE_DIRECTOR",
            payroll_included=False,
        )
        for pid, p in sorted(directors.items())
    ]
    return people, positions, links, nonemployees


def payroll(source, people):
    rows, taxes, journal, settlements, time, approvals = [], [], [], [], [], []
    leave = {e["person_id"]: D(e["hours"]) for e in source["events"] if e["action"] == "PAID_LEAVE"}
    for p in people:
        monthly = cents(D(p["annual_salary_usd"]) / 12)
        ytd = monthly * 7
        for sequence, date in enumerate(source["payroll"]["pay_dates"], 1):
            gross = cents(monthly / 2) if sequence == 1 else monthly - cents(monthly / 2)
            pay_id = f"SH-PAY-202608-{sequence}-{p['person_id']}"
            calculated = withholding(gross, ytd, p["jurisdiction"], p["legal_employer"] == "BST")
            deductions = sum(v for k, v in calculated.items() if k != "employer_known_taxes")
            burden = cents(gross * D(source["payroll"]["employer_burden_rate"]))
            known = calculated["employer_known_taxes"]
            if known > burden:
                raise ValueError("Statutory components exceed modeled loaded burden")
            net = gross - deductions
            batch = f"SH-PAYBATCH-{p['legal_employer']}-202608-{sequence}"
            rows.append(
                stamp(
                    source,
                    pay_id=pay_id,
                    person_id=p["person_id"],
                    position_id=p["position_id"],
                    legal_entity=p["legal_employer"],
                    unit=p["unit"],
                    pay_date=date,
                    gross_usd=money(gross),
                    opening_ytd_wages_usd=money(ytd),
                    withholding_usd=money(deductions),
                    net_usd=money(net),
                    employer_known_taxes_usd=money(known),
                    employer_burden_usd=money(burden),
                    remaining_benefit_and_employer_obligations_usd=money(burden - known),
                    gross_to_net_state="CALCULATED_FOR_DECLARED_RESIDENCE",
                    batch_id=batch,
                    settlement_state="MODELED_PAID",
                )
            )
            for tax, value in calculated.items():
                taxes.append(
                    stamp(
                        source,
                        liability_id=f"{pay_id}-{tax}",
                        pay_id=pay_id,
                        legal_entity=p["legal_employer"],
                        jurisdiction=p["jurisdiction"],
                        tax=tax,
                        amount_usd=money(value),
                        remitted_usd=money(value),
                        closing_liability_usd="0.00",
                        remitted_on=date,
                        remittance_id=f"{pay_id}-{tax}-REMIT",
                        remittance_state="NEWLY_AUTHORED_SYNTHETIC_PAYMENT_NOT_AGENCY_ACKNOWLEDGEMENT",
                    )
                )
            entries = [
                ("WAGES_EXPENSE", gross),
                ("EMPLOYER_COST_EXPENSE", burden),
                ("EMPLOYEE_WITHHOLDING_PAYABLE", -deductions),
                ("EMPLOYER_TAX_PAYABLE", -known),
                ("BENEFITS_AND_OTHER_EMPLOYER_PAYABLE", -(burden - known)),
                ("CASH", -net),
                ("EMPLOYEE_WITHHOLDING_PAYABLE", deductions),
                ("EMPLOYER_TAX_PAYABLE", known),
                ("CASH_TAX_REMITTANCE", -(deductions + known)),
            ]
            for account, value in entries:
                journal.append(
                    stamp(
                        source,
                        journal_id=pay_id,
                        source_id=pay_id,
                        legal_entity=p["legal_employer"],
                        unit=p["unit"],
                        account=account,
                        signed_usd=money(value),
                        posting_state="SUCCESSOR_SUBLEDGER_PENDING_ENTERPRISE_COMPOSITION",
                    )
                )
            settlements.append(
                stamp(
                    source,
                    settlement_id=f"{pay_id}-SET",
                    pay_id=pay_id,
                    batch_id=batch,
                    legal_entity=p["legal_employer"],
                    person_id=p["person_id"],
                    pay_date=date,
                    amount_usd=money(net),
                    authority_id=batch + "-RELEASE",
                    evidence_state="NEWLY_AUTHORED_SYNTHETIC_BANK_CLEARING",
                    independent_external_confirmation=False,
                )
            )
            ytd += gross
        hours_leave = leave.get(p["person_id"], D(0))
        time.append(
            stamp(
                source,
                time_id=f"SH-TIME-202608-{p['person_id']}",
                person_id=p["person_id"],
                position_id=p["position_id"],
                paid_hours="168.00",
                worked_hours=money(D(168) - hours_leave),
                paid_leave_hours=money(hours_leave),
                overtime_hours="0.00",
                time_state="NEWLY_AUTHORED_DAILY_SCHEDULE_SUMMARY",
                daily_schedule=(
                    "Monday-Friday8h, August2026; designated paid leave replaces work, "
                    "never adds capacity"
                ),
            )
        )
    for batch in sorted({r["batch_id"] for r in rows}):
        selected = [r for r in rows if r["batch_id"] == batch]
        approvals.append(
            stamp(
                source,
                authority_id=batch + "-RELEASE",
                batch_id=batch,
                preparer_id="SH-EMP-ESS-0001",
                reviewer_id="SH-EMP-ESS-0002",
                approved_on=selected[0]["pay_date"],
                payment_count=len(selected),
                net_usd=money(sum(D(r["net_usd"]) for r in selected)),
                state="NEWLY_AUTHORED_SYNTHETIC_RELEASE",
            )
        )
    return rows, taxes, journal, settlements, time, approvals


def access_and_qualifications(source, people):
    accesses, qualifications, events = [], [], []
    for p in people:
        accesses.append(
            stamp(
                source,
                principal_id=f"SH-IAM-{p['person_id']}",
                person_id=p["person_id"],
                tenant_id="sable-harbor",
                legal_entity=p["legal_employer"],
                unit=p["unit"],
                entitlement="RESOLVE_USING_ACCEPTED_INFORMATION_NATURE_POLICY",
                granted_at="2026-08-01T00:00:00-07:00",
                revoked_at=None,
                runtime_state="COMPANY_INPUT_NOT_DEPLOYMENT_EVIDENCE",
            )
        )
        qualifications.append(
            stamp(
                source,
                qualification_id=f"SH-QUAL-{p['person_id']}",
                person_id=p["person_id"],
                qualification="UNIT_INDUCTION",
                completed_on="2026-07-31",
                expires_on="2027-07-31",
                evidence_state="NEWLY_AUTHORED_SYNTHETIC_TRAINING",
                authority_scope="INTERNAL_INDUCTION_NOT_LICENSE_OR_OPERATING_AUTHORITY",
            )
        )
    for pid, expiry in [
        ("EMP-098", "2027-07-31"),
        ("EMP-099", "2026-07-31"),
        ("EMP-100", "2027-07-31"),
    ]:
        qualifications.append(
            stamp(
                source,
                qualification_id="SH-DRIVER-" + pid,
                person_id=pid,
                qualification="ORDINARY_INDUSTRIAL_DRIVING",
                completed_on="2026-01-01",
                expires_on=expiry,
                evidence_state="NEWLY_AUTHORED_SYNTHETIC_QUALIFICATION_REGISTER",
                authority_scope="ORDINARY_FREIGHT_ONLY; not radioactive material carriage",
            )
        )
    for e in source["events"]:
        if e["action"] != "EXIT":
            continue
        row = stamp(source, **e, state="LATE_REVOCATION", available_on=source["available_at"])
        row["effective_period"] = e["effective_at"][:7]
        events.append(row)
    return accesses, qualifications, events


def qualified_on(qualification, when):
    return qualification["completed_on"] <= when <= qualification["expires_on"]


def dispatch_assignments(source, qualifications):
    by_id = {r["qualification_id"]: r for r in qualifications}
    result = []
    for seq, pid, when, expected in [
        (1, "EMP-098", "2026-08-02", "RELEASED"),
        (2, "EMP-099", "2026-08-17", "BLOCKED"),
        (3, "EMP-100", "2026-08-20", "RELEASED"),
    ]:
        qid = "SH-DRIVER-" + pid
        result.append(
            stamp(
                source,
                assignment_id=f"SH-DISPATCH-ASSIGN-{seq:02d}",
                person_id=pid,
                qualification_id=qid,
                assignment_on=when,
                asset_id="ARU-TR-01" if seq == 1 else "ARU-TR-02",
                legal_entity="ARU",
                disposition=expected,
                qualification_valid=qualified_on(by_id[qid], when),
                chain_id="SH-CHAIN-202608-DISPATCH-01"
                if seq == 1
                else "SH-CHAIN-202608-DISPATCH-02",
                cargo_scope="ORDINARY_NONRADIOACTIVE_INDUSTRIAL_FREIGHT",
            )
        )
    return result


def operating_records(source, people):
    """Bounded chain population; these attribution records never create GL entries."""
    from datetime import date, timedelta

    events, quantities = [], []
    by_id = {p["person_id"]: p for p in people}
    for chain in source.get("operating_chains", []):
        if chain["responsible_person_id"] not in by_id:
            raise ValueError("Operating responsibility lacks HR identity")
        quantities.append(stamp(source, **{k: v for k, v in chain.items() if k != "stages"}))
        previous = None
        for index, stage in enumerate(chain["stages"]):
            event_id = f"{chain['chain_id']}-{index + 1:02d}"
            events.append(
                stamp(
                    source,
                    event_id=event_id,
                    predecessor_id=previous,
                    chain_id=chain["chain_id"],
                    population_id=chain["population_id"],
                    stage=stage,
                    legal_entity=chain["legal_entity"],
                    unit=chain["unit"],
                    performed_on=str(date.fromisoformat(chain["start_on"]) + timedelta(days=index)),
                    person_id=chain["responsible_person_id"],
                    asset_id=chain["asset_id"],
                    evidence_id=event_id + "-EVIDENCE",
                    evidence_state="NEWLY_AUTHORED_SYNTHETIC_ACTIVITY",
                    accounting_parent_source_id=chain["parent_source_id"],
                    additional_gl_posting=False,
                )
            )
            previous = event_id
    return events, quantities


def payroll_bridges(source, people, pay):
    """Independent comparison to accepted ARU loaded payroll rounding policy."""
    finance = read("industrial/source/finance.json")
    grouped = defaultdict(list)
    for row in finance["employees"]:
        grouped[row["segment"]].append(row)
    bridges = []
    for segment, employees in grouped.items():
        annual = sum(
            D(r["annual_salary_usd"])
            + (D(r["annual_salary_usd"]) * D(str(r["annual_employer_burden_pct"])) / 100).quantize(
                D(1), rounding=ROUND_HALF_UP
            )
            for r in employees
        )
        expected = (annual * D("1.03") / 12).quantize(D(1), rounding=ROUND_HALF_UP)
        actual = sum(
            D(r["gross_usd"]) + D(r["employer_burden_usd"]) for r in pay if r["unit"] == segment
        )
        bridges.append(
            stamp(
                source,
                bridge_id="SH-PAY-BRIDGE-202608-" + segment,
                legal_entity="BST" if segment == "BST" else "ARU",
                unit=segment,
                source_id="PAYROLL-2026",
                source_account="5000",
                source_loaded_expense_usd=money(expected),
                reconstructed_loaded_expense_usd=money(actual),
                delta_usd=money(actual - expected),
                treatment=(
                    "REPLACE_SOURCE_PAYROLL_DETAIL; delta is cent-rounded individual "
                    "versus whole-dollar segment"
                ),
            )
        )
    for entity in ("SHI", "PS", "RWH"):
        actual = sum(
            D(r["gross_usd"]) + D(r["employer_burden_usd"])
            for r in pay
            if r["legal_entity"] == entity
        )
        bridges.append(
            stamp(
                source,
                bridge_id="SH-PAY-BRIDGE-202608-" + entity,
                legal_entity=entity,
                unit="ALL",
                source_id="EMBEDDED_OPERATING_COST_POPULATION",
                source_account=None,
                source_loaded_expense_usd=None,
                reconstructed_loaded_expense_usd=money(actual),
                delta_usd=None,
                treatment=(
                    "SEE_CURRENT_BOOK_COST_COMPONENTS; payroll is a component of "
                    "existing paid cost, never additive"
                ),
            )
        )
    return bridges


def validate_chains(source, tables):
    expected = {c["chain_id"]: c for c in source.get("operating_chains", [])}
    events = defaultdict(list)
    for event in tables["operating_events"]:
        events[event["chain_id"]].append(event)
    quantities = {r["chain_id"]: r for r in tables["operating_quantities"]}
    if set(quantities) != set(expected) or len(quantities) != len(tables["operating_quantities"]):
        raise ValueError("Omitted or duplicate operating chain")
    for cid, chain in expected.items():
        q = quantities[cid]
        if D(q["opening_quantity"]) + D(q["received_or_produced_quantity"]) - D(
            q["released_or_accepted_quantity"]
        ) != D(q["closing_quantity"]):
            raise ValueError("Operating quantity/custody imbalance")
        if [e["stage"] for e in events[cid]] != chain["stages"]:
            raise ValueError("Omitted, reordered or invented operating event")
        if any(e["additional_gl_posting"] for e in events[cid]):
            raise ValueError("Detail creates duplicate financial posting")
        previous = None
        for event in events[cid]:
            if (
                event["predecessor_id"] != previous
                or event["legal_entity"] != chain["legal_entity"]
            ):
                raise ValueError("Broken chain or legal responsibility")
            previous = event["event_id"]
        if chain["kind"] == "production" and D(q["released_or_accepted_quantity"]):
            raise ValueError("Uranium release lacks accepted custody authority")
    # Semantic checks survive source+derivative changes; a coherent hash is not performance.
    maintenance = []
    for cid, chain in expected.items():
        steps = events[cid]
        dated = {e["stage"]: e["performed_on"] for e in steps}
        if chain["kind"] == "dispatch" and "DISPATCHED" in dated:
            if (
                "QUALIFICATION_CHECK" not in dated
                or dated["QUALIFICATION_CHECK"] > dated["DISPATCHED"]
            ):
                raise ValueError("Dispatch precedes qualification check")
        if chain["kind"] == "maintenance":
            maintenance.append((chain["asset_id"], dated["DEFECT_REPORTED"], dated.get("RELEASED")))
    for event in tables["operating_events"]:
        if expected[event["chain_id"]]["kind"] == "maintenance":
            continue
        if event["stage"] not in {
            "STORED",
            "RELEASED",
            "DISPATCHED",
            "DELIVERED",
            "PARTIAL_RELEASE",
        }:
            continue
        for asset, start, end in maintenance:
            if (
                event["asset_id"] == asset
                and start <= event["performed_on"]
                and (end is None or event["performed_on"] < end)
            ):
                raise ValueError("Operating asset used during unresolved defect hold")
    return len(expected)


def validate_tax_components(source, tables):
    from .current_records import read_current_tax_contract

    tax_contract = read_current_tax_contract()
    people = {r["person_id"]: r for r in tables["people"]}
    pay = {r["pay_id"]: r for r in tables["payroll"]}
    rows = {}
    for row in tables["tax_liabilities"]:
        key = row["pay_id"], row["tax"]
        if key in rows or row["pay_id"] not in pay:
            raise ValueError("Duplicate or unknown tax liability component")
        rows[key] = row
    journals = defaultdict(lambda: defaultdict(D))
    for row in tables["journal"]:
        journals[row["journal_id"]][row["account"]] += D(row["signed_usd"])
    expected_keys = set()
    for pid, row in pay.items():
        person = people[row["person_id"]]
        calc = withholding(
            D(row["gross_usd"]),
            D(row["opening_ytd_wages_usd"]),
            person["jurisdiction"],
            row["legal_entity"] == "BST",
        )
        ruia = (
            cents(D(tax_contract["bst_ruia_monthly_base"]) * D(tax_contract["bst_ruia_rate"]))
            if row["legal_entity"] == "BST" and row["pay_date"].endswith("14")
            else D(0)
        )
        calc["employer_ruia"] = ruia
        expected_keys.update((pid, k) for k in calc)
        for key, value in calc.items():
            evidence = rows.get((pid, key))
            if evidence is None or D(evidence["amount_usd"]) != value:
                raise ValueError("Tax liability component does not match payroll calculation")
            if (
                evidence["legal_entity"] != row["legal_entity"]
                or evidence["jurisdiction"] != person["jurisdiction"]
                or evidence["effective_period"] != row["effective_period"]
            ):
                raise ValueError("Tax liability wrong legal entity jurisdiction or period")
            if (
                D(evidence["remitted_usd"]) != value
                or D(evidence["closing_liability_usd"]) != 0
                or evidence["remitted_on"] != row["pay_date"]
            ):
                raise ValueError("Tax remittance rollforward or date mismatch")
        known = calc["employer_known_taxes"] + ruia
        if D(row["employer_known_taxes_usd"]) != known:
            raise ValueError("Employer tax counted incorrectly")
        if journals[pid]["CASH_TAX_REMITTANCE"] != -(D(row["withholding_usd"]) + known):
            raise ValueError("Tax remittance GL does not reconcile")
        if journals[pid]["CASH_BENEFIT_SETTLEMENT"] != -D(
            row["remaining_benefit_and_employer_obligations_usd"]
        ):
            raise ValueError("Benefit payment GL does not reconcile")
        if journals[pid]["WAGES_EXPENSE"] != D(row["gross_usd"]) or journals[pid][
            "EMPLOYER_COST_EXPENSE"
        ] != D(row["employer_burden_usd"]):
            raise ValueError("Payroll cost journal is duplicated or reversed")
    if set(rows) != expected_keys:
        raise ValueError("Tax liability population incomplete or extra")


def validate(source, tables):
    from .current_balances import validate as validate_balances

    validate_balances(tables)
    validate_chains(source, tables)
    quals = {r["qualification_id"]: r for r in tables["qualifications"]}
    for assignment in tables["dispatch_assignments"]:
        qualification = quals[assignment["qualification_id"]]
        valid = qualified_on(qualification, assignment["assignment_on"])
        if assignment["person_id"] != qualification["person_id"] or (
            assignment["disposition"] == "RELEASED" and not valid
        ):
            raise ValueError("Unqualified operating assignment released")
    people = tables["people"]
    ids = [r["person_id"] for r in people]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate population member")
    expected = sum(g["occupied"] for g in source["core_groups"] + source["j2_groups"])
    expected += len(read("industrial/source/finance.json")["employees"])
    expected += read("red_wash/source/core_operating_data.json")["workforce_2026"]["total_fte"]
    if len(ids) != expected:
        raise ValueError("Omitted population member")
    validate_tax_components(source, tables)
    chart_names = {
        r["person_id"]
        for r in read("docs/organization/source/chartbook.json")["nodes"]
        if r.get("type") == "person" and r.get("status") == "current_employee"
    }
    if not chart_names <= set(ids):
        raise ValueError("Accepted named leadership omitted")
    if sum(g["authorized"] for g in source["j2_groups"]) != 237:
        raise ValueError("J2 establishment changed")
    if any(
        g["occupied"] > g.get("authorized", g["occupied"])
        for g in source["core_groups"] + source["j2_groups"]
    ):
        raise ValueError("Unauthorized occupancy")
    positions = {r["position_id"]: r for r in tables["positions"]}
    for p in people:
        if positions[p["position_id"]]["person_id"] != p["person_id"]:
            raise ValueError("Position/person mismatch")
    expected_pay = {(pid, date) for pid in ids for date in source["payroll"]["pay_dates"]}
    keys = [(r["person_id"], r["pay_date"]) for r in tables["payroll"]]
    if len(keys) != len(set(keys)) or set(keys) != expected_pay:
        raise ValueError("Omitted or duplicate payroll member")
    by_id = {p["person_id"]: p for p in people}
    settlements = {r["pay_id"]: r for r in tables["settlements"]}
    if len(settlements) != len(tables["settlements"]) or set(settlements) != {
        r["pay_id"] for r in tables["payroll"]
    }:
        raise ValueError("Settlement population mismatch")
    journal = defaultdict(D)
    cash = defaultdict(D)
    for row in tables["journal"]:
        journal[row["journal_id"]] += D(row["signed_usd"])
        if row["account"] == "CASH":
            cash[row["journal_id"]] += D(row["signed_usd"])
    if any(journal.values()):
        raise ValueError("Unbalanced payroll journal")
    for row in tables["payroll"]:
        p = by_id[row["person_id"]]
        if (
            row["legal_entity"] != p["legal_employer"]
            or row["effective_period"] != source["effective_period"]
        ):
            raise ValueError("Wrong payroll legal entity or period")
        calculated = withholding(
            D(row["gross_usd"]),
            D(row["opening_ytd_wages_usd"]),
            p["jurisdiction"],
            p["legal_employer"] == "BST",
        )
        withheld = sum(v for k, v in calculated.items() if k != "employer_known_taxes")
        if D(row["withholding_usd"]) != withheld or D(row["gross_usd"]) - withheld != D(
            row["net_usd"]
        ):
            raise ValueError("Payroll gross-to-net mismatch")
        if D(settlements[row["pay_id"]]["amount_usd"]) != D(row["net_usd"]) or cash[
            row["pay_id"]
        ] != -D(row["net_usd"]):
            raise ValueError("Payroll-to-settlement/GL mismatch")
    if {r["batch_id"] for r in tables["approvals"]} != {r["batch_id"] for r in tables["payroll"]}:
        raise ValueError("Payment approval population incomplete")
    for row in tables["approvals"]:
        selected = [p for p in tables["payroll"] if p["batch_id"] == row["batch_id"]]
        if row["approved_on"] > min(p["pay_date"] for p in selected):
            raise ValueError("Late payment approval")
        if row["preparer_id"] == row["reviewer_id"] or row["reviewer_id"] not in by_id:
            raise ValueError("Independent approval missing")
    if {r["person_id"] for r in tables["access"]} != set(ids) or len(tables["access"]) != len(ids):
        raise ValueError("HR/access population mismatch")
    for row in tables["time"]:
        if D(row["worked_hours"]) + D(row["paid_leave_hours"]) != D(row["paid_hours"]):
            raise ValueError("Leave adds capacity")
    for rows in tables.values():
        for row in rows:
            if row.get("repository_source_available_at") and datetime.fromisoformat(
                row["available_at"]
            ) < datetime.fromisoformat(row["repository_source_available_at"]):
                raise ValueError("Repository evidence promoted into earlier known-on state")
            if datetime.fromisoformat(row["available_at"]) < datetime.fromisoformat(
                source["available_at"]
            ):
                raise ValueError("Future-authored evidence promoted into earlier known-on state")
    return {
        "employees": len(people),
        "named_employees": len(chart_names),
        "legal_employer_counts": dict(sorted(Counter(p["legal_employer"] for p in people).items())),
        "nonemployee_directors": len(tables["nonemployees"]),
        "positions": len(positions),
        "j2_occupied": sum(g["occupied"] for g in source["j2_groups"]),
        "j2_authorized": 237,
        "payroll_payments": len(tables["payroll"]),
        "gross_usd": money(sum(D(r["gross_usd"]) for r in tables["payroll"])),
        "net_usd": money(sum(D(r["net_usd"]) for r in tables["payroll"])),
        "withholding_usd": money(sum(D(r["withholding_usd"]) for r in tables["payroll"])),
        "employer_burden_usd": money(sum(D(r["employer_burden_usd"]) for r in tables["payroll"])),
        "source_to_enterprise_posting": (
            "COST_COMPONENTS_WITHIN_EXISTING_PAID_SOURCE; NO_ADDITIVE_PAYROLL"
        ),
        "tax_remittance": (
            "NEWLY_AUTHORED_SYNTHETIC_PAYMENT; calculated taxes and benefits paid within "
            "existing cost envelope"
        ),
        "complete_company_acceptance": False,
    }


def build(source=None):
    source = source or read(SOURCE)
    people, positions, links, nonemployees = make_roster(source)
    pay, taxes, journal, settlements, time, approvals = payroll(source, people)
    access, qualifications, events = access_and_qualifications(source, people)
    tables = dict(
        people=people,
        positions=positions,
        identity_links=links,
        nonemployees=nonemployees,
        payroll=pay,
        tax_liabilities=taxes,
        journal=journal,
        settlements=settlements,
        time=time,
        approvals=approvals,
        access=access,
        qualifications=qualifications,
        change_events=events,
    )
    tables["operating_events"], tables["operating_quantities"] = operating_records(source, people)
    tables["dispatch_assignments"] = dispatch_assignments(source, qualifications)
    tables["payroll_source_bridges"] = payroll_bridges(source, people, pay)
    from .current_records import CURRENT_SOURCE, TAX_SCOPE_SOURCE, extend, validate_current

    extend(source, tables)
    from .current_balances import extend as extend_balances

    extend_balances(source, tables)
    totals = validate(source, tables)
    totals.update(validate_current(source, tables))
    inputs = source["sources"] + [
        SOURCE,
        "enterprise/operations/completed_period.py",
        "enterprise/operations/availability.py",
        "geospatial/facilities/population/REGISTER.json",
        CURRENT_SOURCE,
        TAX_SCOPE_SOURCE,
        "enterprise/operations/current_records.py",
        "enterprise/operations/current_balances.py",
        "enterprise/operations/invoice_settlement.py",
        "enterprise/operations/source/lane_receipt_2026_09_15.json",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(set(inputs))}
    result = dict(
        record_id=source["record_id"],
        schema_version=source["schema_version"],
        authority_state=source["authority_state"],
        acceptance_state=source["acceptance_state"],
        effective_through=source["effective_through"],
        available_at=source["available_at"],
        source_hashes=hashes,
        totals=totals,
        tables=tables,
    )
    return apply_availability(result)


def visible_rows(rows, *, as_of, known_on, allow_preview=False):
    """Current-effective and known-on are independent axes, both fail closed."""
    knowledge = datetime.fromisoformat(known_on)
    if knowledge.tzinfo is None:
        raise ValueError("Known-on timestamp requires timezone")
    return [
        r
        for r in rows
        if queryable(r, allow_preview)
        and r.get(
            "effective_at",
            r.get(
                "effective_from",
                r.get("performed_on", r.get("pay_date", r["effective_period"] + "-01")),
            ),
        )[:10]
        <= as_of[:10]
        and (not r.get("effective_to") or as_of[:10] < r["effective_to"][:10])
        and datetime.fromisoformat(r["available_at"]) <= knowledge
    ]


def workforce_state(result, *, as_of, known_on, allow_preview=False):
    """Apply visible HR/access events without rewriting the August source snapshots."""
    import copy

    rows = copy.deepcopy(
        visible_rows(
            result["tables"]["people"], as_of=as_of, known_on=known_on, allow_preview=allow_preview
        )
    )
    access = copy.deepcopy(
        visible_rows(
            result["tables"]["access"], as_of=as_of, known_on=known_on, allow_preview=allow_preview
        )
    )
    changes = visible_rows(
        result["tables"]["change_events"],
        as_of=as_of,
        known_on=known_on,
        allow_preview=allow_preview,
    )
    exited = {r["person_id"] for r in changes if r["action"] == "EXIT"}
    revoked = {
        r["person_id"]
        for r in changes
        if r.get("revoked_at") and r["revoked_at"][:10] <= as_of[:10]
    }
    for row in rows:
        if row["person_id"] in exited:
            row["status"] = "EXITED"
    for row in access:
        row["status"] = "REVOKED" if row["person_id"] in revoked else "ACTIVE"
    return {
        "people": rows,
        "access": access,
        "active_employees": sum(r["status"] == "ACTIVE" for r in rows),
        "active_principals": sum(r["status"] == "ACTIVE" for r in access),
        "visible_change_events": changes,
    }


def write(result, destination=OUTPUT, check=False):
    destination = Path(destination)
    receipt = read("enterprise/operations/source/lane_receipt_2026_09_15.json")
    receipt["declared_known_on"] = receipt["known_on"]
    receipt["known_on"] = result["available_at"]
    receipt["authored_day"] = result["authored_day"]
    receipt["declared_available_precision"] = "DAY"
    receipt["publication_state"] = result["publication_state"]
    receipt["publishable_source_snapshot"] = result["publishable_source_snapshot"]
    receipt["table_counts"] = {k: len(v) for k, v in result["tables"].items()}
    receipt["reconciliation_totals"] = result["totals"]
    receipt["source_hashes"] = result["source_hashes"]
    artifacts = {"records.json": encoded(result), "lane_receipt.json": encoded(receipt)}
    for name, rows in result["tables"].items():
        import io

        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=sorted({k for r in rows for k in r}))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()}
            )
        artifacts[name + ".csv"] = stream.getvalue().encode()
    manifest = dict(
        record_id=result["record_id"],
        source_hashes=result["source_hashes"],
        totals=result["totals"],
        source_commit=__import__("subprocess")
        .check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
        .strip(),
        artifacts={p: hashlib.sha256(data).hexdigest() for p, data in artifacts.items()},
        distribution_state="REVIEWABLE_COMPANY_INPUT_PENDING_COMPOSITE_RELEASE",
        publication_state=result["publication_state"],
        publishable_source_snapshot=result["publishable_source_snapshot"],
        repository_source_available_at=result["repository_source_available_at"],
    )
    artifacts["manifest.json"] = encoded(manifest)
    if check:
        if any(
            not (destination / p).exists() or (destination / p).read_bytes() != data
            for p, data in artifacts.items()
        ):
            raise ValueError("Stale completed-period derivative")
    else:
        destination.mkdir(parents=True, exist_ok=True)
        for p, data in artifacts.items():
            (destination / p).write_bytes(data)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    write(result, args.output, args.check)
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
