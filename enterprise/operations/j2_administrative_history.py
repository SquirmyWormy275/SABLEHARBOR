"""Dated administrative history successor; never mutates accepted roster/census."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from .availability import apply, queryable, repository_context
from .completed_period import make_roster

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "enterprise/operations/source/j2_administrative_history_2026_09_22.json"
REQUIRED_SOURCES = {
    "docs/j2/J2_HEADQUARTERS.md",
    "enterprise/operations/source/completed_period_2026_08.json",
    "docs/j2/J2_ESTABLISHMENT.md",
    "geospatial/facilities/population/REGISTER.json",
    "docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md",
    "docs/j2/ORIENTATION_OFFICER_PROFESSION.md",
    "docs/organization/source/chartbook.json",
    "industrial/source/finance.json",
    "red_wash/source/core_operating_data.json",
    "docs/structured/j2_leadership_2026-09-10.json",
}
ANONYMOUS = {
    "ROLE-39": "SH-EMP-J2-HQ-0003",
    "ROLE-41": "SH-EMP-J2-CONTACT-0002",
    "ROLE-50": "SH-EMP-J2-JUDGMENT-0002",
    "ROLE-55": "SH-EMP-J2-ORIENTATION-0002",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data, root=ROOT):
    require(data["repository_state"] == "PENDING_ACCEPTANCE", "Source cannot self-accept")
    require(set(data["source_hashes"]) == REQUIRED_SOURCES, "Source hash population incomplete")
    for path, expected in data["source_hashes"].items():
        require(
            hashlib.sha256((root / path).read_bytes()).hexdigest() == expected,
            "Changed controlling source: " + path,
        )
    accepted = json.loads((root / "docs/structured/j2_leadership_2026-09-10.json").read_text())
    prior = {row["person_id"]: row for row in accepted["people"]}
    source = json.loads(
        (root / "enterprise/operations/source/completed_period_2026_08.json").read_text()
    )
    people, positions, _, _ = make_roster(source)
    employees = {p["person_id"]: p for p in people}
    rows = data["events"]
    require(
        len(rows) == 10 and len({r["person_id"] for r in rows}) == 10,
        "Exact ten incumbents required",
    )
    require(len({r["role_id"] for r in rows}) == 10, "Duplicate role")
    require(
        {r["person_id"] for r in rows} == set(prior) | set(ANONYMOUS.values()),
        "Incumbent population changed",
    )
    require(sum(g["authorized"] for g in source["j2_groups"]) == 237, "Establishment changed")
    require(sum(g["occupied"] for g in source["j2_groups"]) == 181, "Occupied population changed")
    for row in rows:
        person = employees[row["person_id"]]
        require(
            person["legal_employer"] == "SHI" and person["unit"].startswith("J2-"),
            "Wrong employer/unit",
        )
        require(
            person["position_id"] in {p["position_id"] for p in positions if p["person_id"]},
            "Missing occupied billet",
        )
        appointment = date.fromisoformat(row["current_office_appointment_date"])
        require(appointment <= date(2026, 8, 1), "Appointment contradicts August incumbent")
        require(
            appointment
            <= date.fromisoformat(row["acknowledgement_date"])
            <= date.fromisoformat(row["hr_record_date"])
            <= date.fromisoformat(row["current_confirmation_date"]),
            "Administrative chronology inverted",
        )
        require(
            row["appointment_precision"] == "DAY"
            and row["appointment_origin"].startswith("NEWLY_AUTHORED_"),
            "Date precision/provenance lost",
        )
        require(
            row["new_authority"] is False and row["incremental_salary_usd"] == "0.00",
            "Unauthorized powers/payroll",
        )
        if row["person_id"] in prior:
            old = prior[row["person_id"]]
            for field in ["name", "role_id", "title"]:
                require(row[field] == old[field], "Accepted identity/office changed")
            require(
                row["company_joined_year"] == old["joined_year"]
                and row["company_joined_precision"] == "YEAR",
                "Joining year/precision changed",
            )
            require(
                appointment.year > old["joined_year"],
                "Appointment mechanically assigned from joining year",
            )
        else:
            require(
                ANONYMOUS.get(row["role_id"]) == row["person_id"] and row["name"] is None,
                "New identity or wrong anonymous role join",
            )
            require(row["company_joined_year"] is None, "Unestablished hire history invented")
        if row["role_id"] in {"ROLE-54", "ROLE-55"}:
            require(
                row["commission_history_state"] == "OPEN_ORIENTATION_TERM_HISTORY",
                "Office appointment promoted to commission",
            )
        require(
            "commission_date" not in row and "commission_expiry" not in row,
            "Unsupported commission terms",
        )
    return {
        "administrative_incumbencies": 10,
        "accepted_named_leaders": 6,
        "existing_anonymous_occupants": 4,
        "authorized_billets": 237,
        "occupied_august": 181,
        "additional_employees": 0,
        "additional_payroll_usd": "0.00",
    }


def build(context=None):
    data = json.loads((ROOT / SOURCE).read_text())
    counts = validate(data)
    result = deepcopy(data)
    for row in result["events"]:
        row.update(available_at="2026-09-22T00:00:00Z", recorded_at="2026-09-22T00:00:00Z")
    result["counts"] = counts
    return apply(result, context or repository_context(ROOT))


def known_on(result, timestamp):
    cutoff = datetime.fromisoformat(timestamp)
    return [
        r
        for r in result["events"]
        if queryable(r) and datetime.fromisoformat(r["available_at"]) <= cutoff
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["counts"], sort_keys=True))
