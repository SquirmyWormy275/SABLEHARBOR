"""Scoped admissions/commission history for the existing 18 Orientation occupants."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from .availability import apply, queryable, repository_context
from .completed_period import make_roster

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "enterprise/operations/source/orientation_commissions_2026_09_22.json"
SOURCES = {
    "docs/j2/ORIENTATION_OFFICER_PROFESSION.md",
    "docs/j2/J2_ESTABLISHMENT.md",
    "docs/structured/j2_leadership_2026-09-10.json",
    "enterprise/operations/source/completed_period_2026_08.json",
    "enterprise/operations/source/j2_administrative_history_2026_09_22.json",
    "docs/organization/source/chartbook.json",
    "industrial/source/finance.json",
    "red_wash/source/core_operating_data.json",
    "geospatial/facilities/population/REGISTER.json",
}
RESTRICTIONS = {
    "PERMANENT_NO_LATER_LINE_EXECUTIVE_AUTHORITY",
    "NO_SERVING_VOTING_BOARD_SEAT",
    "NONEXECUTIVE_BOARD_ONLY_AFTER_FIVE_YEAR_COOLING_AND_DISCLOSURE",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def day(value):
    return date.fromisoformat(value)


def assignment_allowed(record, start, end_exclusive, *, line_authority=False, voting_seat=False):
    c = record["commission"]
    return (
        not line_authority
        and not voting_seat
        and day(c["start"]) <= day(start) < day(end_exclusive) <= day(c["end_exclusive"])
    )


def validate(data):
    require(data["repository_state"] == "PENDING_ACCEPTANCE", "Source cannot self-accept")
    require(set(data["source_hashes"]) == SOURCES, "Source population incomplete")
    for path, expected in data["source_hashes"].items():
        require(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
            "Changed source: " + path,
        )
    source = json.loads(
        (ROOT / "enterprise/operations/source/completed_period_2026_08.json").read_text()
    )
    people, positions, _, _ = make_roster(source)
    roster = {p["person_id"]: p for p in people if p["unit"] == "J2-ORIENTATION"}
    require(len(roster) == 18, "Current occupied population changed")
    authorized = [p for p in positions if p["unit"] == "J2-ORIENTATION"]
    require(len(authorized) == 24, "Authorized population changed")
    rows = data["records"]
    require(
        len(rows) == 18 and {r["person_id"] for r in rows} == set(roster),
        "Omitted/duplicate member",
    )
    require(len({r["commission"]["pin_id"] for r in rows}) == 18, "Duplicate commission pin")
    require(len({r["record_id"] for r in rows}) == 18, "Duplicate admission record")
    require(
        data["population"]
        == dict(authorized=24, occupied=18, vacant=6, new_people=0, new_payroll_usd="0.00"),
        "Scope or payroll changed",
    )
    appointments = json.loads(
        (
            ROOT / "enterprise/operations/source/j2_administrative_history_2026_09_22.json"
        ).read_text()
    )
    office = {r["person_id"]: r["current_office_appointment_date"] for r in appointments["events"]}
    failures = []
    for row in rows:
        pid = row["person_id"]
        require(row["position_id"] == roster[pid]["position_id"], "Wrong occupied position")
        require(row["origin"] == "NEWLY_AUTHORED_FICTIONAL_HISTORY", "Historical origin concealed")
        require(
            row["name"] == ("Grant Kohrs" if pid == "P067" else None), "New or changed identity"
        )
        recs = row["recommendations"]
        require(
            len(recs) == 3 and {r["perspective"] for r in recs} == {"senior", "peer", "junior"},
            "Three recommendation perspectives required",
        )
        require(
            len({r["reviewer_ref"] for r in recs}) == 3, "Recommendation perspectives collapsed"
        )
        packet = row["packet"]
        require(
            set(packet["components"])
            == {
                "background_records",
                "prior_work",
                "writing_sample",
                "written_problems",
                "interview",
            },
            "Incomplete admission packet",
        )
        attempts = row["attempts"]
        require(1 <= len(attempts) <= 2, "More than two career AS attempts")
        previous = day(packet["reviewed_on"])
        require(all(day(r["date"]) <= previous for r in recs), "Recommendations after packet")
        for i, attempt in enumerate(attempts):
            require(attempt["attempt"] == i + 1, "Attempt sequence")
            require(
                previous < day(attempt["start"]) <= day(attempt["end"]), "Assessment chronology"
            )
            require(
                5 <= (day(attempt["end"]) - day(attempt["start"])).days + 1 <= 7,
                "AS length outside doctrine",
            )
            outcome = "PASSED_TO_APPRENTICESHIP" if i == len(attempts) - 1 else "NOT_SELECTED"
            require(
                attempt["outcome"] == outcome, "Failed assessment erased or unqualified admission"
            )
            if outcome == "NOT_SELECTED":
                failures.append(pid)
            previous = day(attempt["end"])
        app, council, commission = row["apprenticeship"], row["council"], row["commission"]
        require(
            previous
            < day(app["start"])
            < day(app["end"])
            < day(council["decision_on"])
            < day(commission["start"]),
            "Commission before completed admission",
        )
        require(
            330 <= (day(app["end"]) - day(app["start"])).days <= 400,
            "Apprenticeship not approximately one year",
        )
        require(
            len(app["reviews"]) == 4
            and app["reviews"] == sorted(set(app["reviews"]))
            and all(day(app["start"]) <= day(t) <= day(app["end"]) for t in app["reviews"]),
            "Missing or invalid apprenticeship reviews",
        )
        require(
            council["decision"] == "ADMIT"
            and council["body"] == "ADMISSIONS_COUNCIL"
            and council["candidate_is_reviewer"] is False
            and council["appointment_to_permanent_governance_body"] is False,
            "Unsupported admission authority",
        )
        start = day(commission["start"])
        require(
            commission["standard_years"] == 6
            and day(commission["end_exclusive"]) == start.replace(year=start.year + 6),
            "Unauthorized term or extension",
        )
        require(
            commission["renewals"] == [] and commission["waivers"] == [],
            "Unapproved renewal or waiver",
        )
        require(
            set(commission["restrictions"]) == RESTRICTIONS, "Professional restrictions changed"
        )
        require(
            commission["acknowledgement_on"] == commission["start"],
            "Missing restrictions acknowledgement",
        )
        if pid == "P067":
            require(
                day(recs[0]["date"]).year >= 2020, "Grant history precedes accepted joining year"
            )
        if pid in office:
            require(
                start <= day(office[pid]) < day(commission["end_exclusive"]),
                "Current office conflicts with commission",
            )
        assignment = row["assignment"]
        require(
            assignment["authority"] == "ORIENTATION_OBSERVATION_NOT_LINE_COMMAND",
            "Line authority invented",
        )
        require(
            assignment_allowed(
                row,
                assignment["start"],
                assignment["end_exclusive"],
                line_authority=assignment["line_executive_role"],
                voting_seat=assignment["voting_board_seat"],
            ),
            "Assignment outside commission or prohibited office",
        )
        require(
            assignment_allowed(row, "2026-08-01", "2026-09-01"),
            "Not commissioned during declared current period",
        )
        if assignment["post"] in {"OFFICE_OF_CEO", "BOARD", "CFO_OBSERVATION"}:
            require(
                730 <= (day(assignment["end_exclusive"]) - day(assignment["start"])).days <= 1096,
                "Office posting outside 24–36 month rotation",
            )
        transition = row["transition"]
        require(
            day(transition["review_due"]) < day(commission["end_exclusive"])
            and transition["no_automatic_renewal"] is True,
            "Missing transition guard",
        )
    cohorts = Counter(r["commission"]["start"][:4] for r in rows)
    require(all(1 <= n <= 3 for n in cohorts.values()), "Intake outside authored annual scope")
    require(failures == ["SH-EMP-J2-ORIENTATION-0012"], "Declared failed attempt lost")
    posts = Counter(r["assignment"]["post"] for r in rows)
    require(posts["OFFICE_OF_CEO"] == posts["BOARD"] == 1, "Separate CEO/Board posts required")
    grades = Counter(r["assignment"]["grade"] for r in rows)
    require(
        grades
        == {"HEAD": 1, "DEPUTY": 1, "SENIOR_ORIENTATION_OFFICER": 4, "ORIENTATION_OFFICER": 12},
        "Occupied grade scope changed",
    )
    return dict(
        occupied=18,
        authorized=24,
        vacant=6,
        admissions_attempts=19,
        preserved_nonselections=1,
        active_standard_commissions=18,
        waivers=0,
        renewals=0,
        cohorts=dict(cohorts),
    )


def build(context=None):
    data = json.loads((ROOT / SOURCE).read_text())
    result = deepcopy(data)
    result["counts"] = validate(data)
    for row in result["records"]:
        row.update(available_at="2026-09-22T00:00:00Z", recorded_at="2026-09-22T00:00:00Z")
    return apply(result, context or repository_context(ROOT))


def known_on(result, timestamp):
    cutoff = datetime.fromisoformat(timestamp)
    return [
        r
        for r in result["records"]
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
