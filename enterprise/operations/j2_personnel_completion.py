"""Bounded named-person and professional-history successor for existing J2 staff."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from .availability import apply, queryable, repository_context
from .completed_period import make_roster

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "enterprise/operations/source/j2_personnel_completion_2026_09_22.json"
NEW_NAMES = {
    "ROLE-39": ("SH-EMP-J2-HQ-0003", "Miriam Solano"),
    "ROLE-41": ("SH-EMP-J2-CONTACT-0002", "Owen Faraday"),
    "ROLE-50": ("SH-EMP-J2-JUDGMENT-0002", "Nadia Ivers"),
    "ROLE-55": ("SH-EMP-J2-ORIENTATION-0002", "Leila Soren"),
}
PINS = {
    "docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md",
    "enterprise/operations/source/j2_administrative_history_2026_09_22.json",
    "enterprise/operations/source/orientation_commissions_2026_09_22.json",
    "enterprise/operations/source/completed_period_2026_08.json",
    "docs/organization/source/chartbook.json",
    "docs/j2/J2_ESTABLISHMENT.md",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads((ROOT / path).read_text())


def validate(data):
    require(data["repository_state"] == "PENDING_ACCEPTANCE", "Source may not self-accept")
    require(set(data["source_hashes"]) == PINS, "Incomplete source population")
    for path, pin in data["source_hashes"].items():
        require(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == pin, "Source changed: " + path
        )
    admin = {
        r["person_id"]: r
        for r in read("enterprise/operations/source/j2_administrative_history_2026_09_22.json")[
            "events"
        ]
    }
    commissions = {
        r["person_id"]: r
        for r in read("enterprise/operations/source/orientation_commissions_2026_09_22.json")[
            "records"
        ]
    }
    source = read("enterprise/operations/source/completed_period_2026_08.json")
    people, _, _, _ = make_roster(source)
    roster = {p["person_id"]: p for p in people}
    rows = data["profiles"]
    require(
        len(rows) == 10 and {r["person_id"] for r in rows} == set(admin),
        "Missing/duplicate profile",
    )
    require(len({r["name"] for r in rows}) == 10, "Duplicate person name")
    known_names = {r["name"]: r["person_id"] for r in people if r["name"]}
    for row in rows:
        pid = row["person_id"]
        previous = admin[pid]
        require(
            row["role_id"] == previous["role_id"] and row["title"] == previous["title"],
            "Role changed",
        )
        require(
            row["legal_entity"] == roster[pid]["legal_employer"] == "SHI", "Wrong legal employer"
        )
        require(
            row["office_appointment_date"] == previous["current_office_appointment_date"],
            "Appointment changed",
        )
        require(row["joined_precision"] == "YEAR", "Hire precision invented")
        require(known_names.get(row["name"], pid) == pid, "Name collides with existing employee")
        if previous["name"]:
            require(
                row["name"] == previous["name"]
                and row["company_joined_year"] == previous["company_joined_year"],
                "Accepted identity/year changed",
            )
        else:
            require(NEW_NAMES[row["role_id"]] == (pid, row["name"]), "Wrong new name binding")
        require(
            row["professional_limits"]
            == dict(
                new_post=False,
                new_employee=False,
                new_payroll_usd="0.00",
                new_authority=False,
                degree_license_or_real_employer_confirmation_claimed=False,
            ),
            "New powers/payroll/external claim",
        )
        episodes = row["career_episodes"]
        require(
            len(episodes) == (3 if pid in commissions else 2),
            "Career episode population incomplete",
        )
        first = episodes[0]
        require(
            first["start_precision"] == first["end_precision"] == "YEAR",
            "External career precision changed",
        )
        require(
            int(first["start"]) <= int(first["end"]) < row["company_joined_year"],
            "Prior career overlaps claimed joining year",
        )
        require(
            first["organization_scope"] == "FICTIONAL_EXTERNAL_CAREER_ONLY_NOT_GROUP_ENTITY",
            "Fictional employer promoted to group entity",
        )
        require(
            episodes[1]["start"] == str(row["company_joined_year"])
            and episodes[1]["start_precision"] == "YEAR",
            "Joining year converted into exact hire",
        )
        require(
            episodes[-1]["end"] == row["office_appointment_date"]
            and episodes[-1]["end_precision"] == "DAY_EXCLUSIVE",
            "Prior/current-office bridge incorrect",
        )
        require(all(e["duties"] and e["verification"] for e in episodes), "Missing career evidence")
        q = row["qualification_review"]
        require(
            q["reviewer_person_id"] in roster
            and q["reviewer_person_id"] != pid
            and q["reviewer_is_subject"] is False,
            "Self or unknown review",
        )
        require(
            date.fromisoformat(q["completed_on"])
            < date.fromisoformat(row["office_appointment_date"]),
            "Review after appointment",
        )
        require(
            len(q["competencies"]) >= 3 and len(set(q["competencies"])) == len(q["competencies"]),
            "Incomplete skill review",
        )
        require(
            set(q["evidence"])
            == set(q["observations"])
            == {
                "bounded_work_sample",
                "source_and_uncertainty_exercise",
                "authority_boundary_case",
                "independent_review_note",
            },
            "Missing review evidence",
        )
        require(
            q["external_credential_or_license_claim"] is False, "Unverified external credential"
        )
        if pid in commissions:
            c = commissions[pid]
            require(q["commission_record_id"] == c["record_id"], "Wrong commission join")
            require(
                episodes[1]["end"] == episodes[2]["start"] == c["commission"]["start"],
                "Commission chronology changed",
            )
            require(
                row["company_joined_year"] <= int(c["apprenticeship"]["start"][:4]),
                "Joined after apprenticeship",
            )
        else:
            require(q["commission_record_id"] is None, "Non-Orientation commission invented")
    require(
        data["coverage"]
        == dict(
            required_named_offices=10,
            prior_accepted_names=6,
            new_names_existing_people=4,
            authorized_j2_billets=237,
            occupied_j2_billets=181,
            orientation_commissions=18,
            other_named_identity_required_for_declared_scope=0,
            other_staff_identification=(
                "Existing stable employee IDs suffice for remaining "
                "payroll/access/qualification populations; "
                "no extra named personnel requirement created"
            ),
        ),
        "Declared scope changed",
    )
    return dict(
        profiles=10,
        preserved_names=6,
        new_names_existing_people=4,
        career_episodes=22,
        internal_reviews=10,
        additional_employees=0,
        additional_cash_usd="0.00",
    )


def build(context=None):
    data = read(SOURCE)
    result = deepcopy(data)
    result["counts"] = validate(data)
    for row in result["profiles"]:
        row.update(available_at="2026-09-22T00:00:00Z", recorded_at="2026-09-22T00:00:00Z")
    return apply(result, context or repository_context(ROOT))


def join_people(people, *, known_on, context=None):
    """Copy a complete current people population; change only supported display fields."""
    result = build(context)
    cutoff = datetime.fromisoformat(known_on)
    require(cutoff.tzinfo is not None, "Known-on timezone required")
    updates = {
        r["person_id"]: r
        for r in result["profiles"]
        if queryable(r) and datetime.fromisoformat(r["available_at"]) <= cutoff
    }
    ids = [p["person_id"] for p in people]
    require(len(set(ids)) == len(ids), "Duplicate employee")
    require(set(updates) <= set(ids), "Missing profile employee from declared population")
    output = deepcopy(people)
    for person in output:
        if row := updates.get(person["person_id"]):
            require(
                person["legal_employer"] == row["legal_entity"],
                "Employee legal-entity join differs",
            )
            person.update(
                name=row["name"],
                position_title=row["title"],
                original_hire_year=row["company_joined_year"],
            )
    return output


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
