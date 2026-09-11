"""Reproducible evidence bridge; unknown actual populations never become zeros."""

from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def build():
    policy = json.loads((HERE / "policy.json").read_text())
    paths = policy["sources"]
    chart = read(paths["chart"])
    # Keep discarded identities discoverable by stable source ID, without
    # republishing superseded names in the current-facing population bridge.
    for record in chart["register_only"]:
        if "superseded" in record.get("status", "").lower():
            record["name"] = "Superseded identity (see historical source)"
            record["sources"] = [
                {key: value for key, value in source.items() if key != "evidence"}
                for source in record["sources"]
            ]
    by_person = {}
    for node in chart["nodes"]:
        if node["type"] != "person":
            continue
        pid = node["person_id"]
        if pid not in by_person:
            by_person[pid] = {
                "person_id": pid,
                "name": node["name"],
                "status": node["status"],
                "display_ids": [],
                "sources": [],
                "joining_records": [],
                "counting_weight": 1,
                "workplace_assignment": None,
                "workplace_assignment_status": "NOT_ESTABLISHED_BY_PERSON_DISPLAY",
            }
        person = by_person[pid]
        assert person["status"] == node["status"], f"conflicting status {pid}"
        person["display_ids"].append(node["id"])
        person["joining_records"].append(
            {
                "display_id": node["id"],
                "year": node.get("joined_year"),
                "basis": node.get("year_basis"),
                "not_an_occupancy_date": True,
            }
        )
        for source in node["sources"]:
            if source not in person["sources"]:
                person["sources"].append(source)
    people = sorted(by_person.values(), key=lambda x: x["person_id"])
    excluded = [
        {k: n[k] for k in ("id", "name", "status", "sources")}
        for n in chart["register_only"]
        if n["id"].startswith("P") and n["id"][1:].isdigit()
    ]
    groups = copy.deepcopy(policy["j2_billet_groups"])
    for group in groups:
        group.update(
            current_named_employees=len(group["named_person_ids"]),
            unnamed_authorized_billets=group["authorized_billets"] - len(group["named_person_ids"]),
            confirmed_vacancies=None,
            actual_occupied_billets=None,
            source=paths["establishment"],
            status="LOCKED_AUTHORIZATION_NOT_OCCUPANCY",
        )
    industrial = read(paths["industrial"])["headcount_boundaries"]
    forecast = read(paths["forecast"])
    units = []
    for node in chart["nodes"] + chart["register_only"]:
        if node.get("type") == "person" or (
            node["id"].startswith("P") and node["id"][1:].isdigit()
        ):
            continue
        units.append(
            {
                "id": node["id"],
                "name": node["name"],
                "status": node["status"],
                "sources": node["sources"],
                "unit_kind": "role_record"
                if node["id"].startswith("ROLE-")
                else "entity_or_function",
                "current_named_employees": None,
                "authorized_positions": None,
                "confirmed_vacancies": None,
                "remote_distributed_field_deployed": None,
                "resident_occupants": None,
                "visitors_customers_trainees_peak": None,
                "shift_population": None,
                "maximum_concurrent_attendance": None,
                "seat_assignment_source": "geospatial/facilities/source/campus.json",
                "assigned_desks": None,
                "shared_desks": None,
                "touchdown_seats": None,
                "training_seats": None,
                "meeting_seats": None,
                "special_use_capacity": None,
                "horizons": [
                    {
                        "year": y,
                        "proposed_future_positions": None,
                        "status": "UNRESOLVED_NO_EMPLOYMENT_CENSUS"
                        if y == 2026
                        else "UNRESOLVED_PLANNING_CAPACITY",
                        "net_assignable_area_m2": None,
                    }
                    for y in policy["horizons"]
                ],
                "rollup_rule": "NONADDITIVE_VIEW; normalized people and J2 groups control counts, site program controls physical capacity",
            }
        )
    return {
        "record_id": policy["record_id"],
        "as_of": policy["as_of"],
        "schema_version": "1.0.0",
        "source_revision": {
            "chart_publication": chart["publication_revision"],
            "chart_as_of": chart["as_of"],
            "source_sha256": {
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                for p in sorted(
                    set(paths.values()) | {str((HERE / "policy.json").relative_to(ROOT))}
                )
            },
        },
        "people": people,
        "excluded_register_people": excluded,
        "entities_functions_roles": units,
        "j2": {
            "authorized_billets": sum(g["authorized_billets"] for g in groups),
            "current_named_employees": sum(g["current_named_employees"] for g in groups),
            "unnamed_authorized_billets": sum(g["unnamed_authorized_billets"] for g in groups),
            "confirmed_vacancies": None,
            "actual_occupied_billets": None,
            "groups": groups,
        },
        "industrial": {
            "status": "ACCEPTED_SELECTED_OPERATING_CASE_NOT_SITE_ATTENDANCE",
            "source": paths["industrial"],
            "values": industrial,
            "selected_population_total": industrial["pale_sun_red_wash_total"]
            + industrial["aru_consolidated"],
            "actual_concurrent_attendance": None,
        },
        "conditional_forecast": {
            "year": forecast["start_year"],
            "status": forecast["fact_state"],
            "source": paths["forecast"],
            "groups": forecast["workforce"],
            "occupied": sum(x["occupied"] for x in forecast["workforce"].values()),
            "authorized": sum(x["authorized"] for x in forecast["workforce"].values()),
        },
        "totals": {
            "person_display_records": sum(len(p["display_ids"]) for p in people),
            "unique_display_people": len(people),
            "current_named_employees": sum(p["status"] == "current_employee" for p in people),
            "current_named_nonemployee_directors": sum(
                p["status"] == "current_nonemployee_director" for p in people
            ),
            "current_named_people": sum(p["status"].startswith("current_") for p in people),
            "former_display_people": sum(p["status"] == "former_employee" for p in people),
            "excluded_register_people": len(excluded),
            "actual_company_headcount": None,
            "actual_company_peak_attendance": None,
            "actual_company_seats": None,
        },
        "measurement_rules": policy["measurement_rules"],
        "planning_basis": policy["planning_basis"],
    }


def validate(data):
    errors = []

    def check(ok, message):
        if not ok:
            errors.append(message)

    people = data["people"]
    totals = data["totals"]
    j2 = data["j2"]
    groups = j2["groups"]
    for collection, key in [
        (people, "person_id"),
        (data["entities_functions_roles"], "id"),
        (groups, "id"),
    ]:
        ids = [x[key] for x in collection]
        check(len(ids) == len(set(ids)), f"duplicate {key}")
    check(
        all(p["counting_weight"] == 1 for p in people),
        "person counted fractionally or more than once",
    )
    displays = [d for p in people for d in p["display_ids"]]
    check(len(displays) == len(set(displays)), "display allocated to multiple people")
    for status, key in [
        ("current_employee", "current_named_employees"),
        ("current_nonemployee_director", "current_named_nonemployee_directors"),
        ("former_employee", "former_display_people"),
    ]:
        check(sum(p["status"] == status for p in people) == totals[key], f"named rollup {key}")
    check(
        totals["current_named_people"]
        == totals["current_named_employees"] + totals["current_named_nonemployee_directors"],
        "named people/director conflation",
    )
    check(totals["unique_display_people"] == len(people), "unique-person total")
    check(totals["person_display_records"] == len(displays), "display total")
    ids = [pid for g in groups for pid in g["named_person_ids"]]
    check(len(ids) == len(set(ids)), "J2 person assigned to multiple arms")
    check(
        all(
            pid in {p["person_id"] for p in people if p["status"] == "current_employee"}
            for pid in ids
        ),
        "J2 person not current employee",
    )
    for key in ["authorized_billets", "current_named_employees", "unnamed_authorized_billets"]:
        check(sum(g[key] for g in groups) == j2[key], f"J2 vertical rollup {key}")
    establishment = (ROOT / "docs/j2/J2_ESTABLISHMENT.md").read_text()
    for g in groups:
        expected = re.search(r"\| " + re.escape(g["name"]) + r" \| (\d+) \|", establishment)
        check(
            expected is not None and int(expected.group(1)) == g["authorized_billets"],
            f"J2 source authorization {g['id']}",
        )
        check(
            g["current_named_employees"] == len(g["named_person_ids"]),
            f"J2 named allocation {g['id']}",
        )
        check(
            g["current_named_employees"] + g["unnamed_authorized_billets"]
            == g["authorized_billets"],
            f"J2 horizontal rollup {g['id']}",
        )
        check(
            g["confirmed_vacancies"] is None and g["actual_occupied_billets"] is None,
            "unnamed billets conflated with vacancy/occupancy",
        )
    check(j2["authorized_billets"] == 237, "J2 locked 237 changed")
    for key in [
        "actual_company_headcount",
        "actual_company_peak_attendance",
        "actual_company_seats",
    ]:
        check(totals[key] is None, f"unsupported actual total {key}")
    f = data["conditional_forecast"]
    check(
        f["year"] == 2027 and f["status"] == "CONDITIONAL_FORECAST",
        "forecast promoted into actuals",
    )
    for key in ["occupied", "authorized"]:
        check(sum(g[key] for g in f["groups"].values()) == f[key], f"forecast rollup {key}")
    v = data["industrial"]["values"]
    check(
        v["pale_sun_platform"] + v["red_wash_site"] == v["pale_sun_red_wash_total"],
        "Pale Sun overlap",
    )
    check(v["aru_nonrail_and_corporate"] + v["bst"] == v["aru_consolidated"], "ARU overlap")
    check(
        v["pale_sun_red_wash_total"] + v["aru_consolidated"]
        == data["industrial"]["selected_population_total"],
        "industrial rollup",
    )
    for path, digest in data["source_revision"]["source_sha256"].items():
        check(
            (ROOT / path).exists()
            and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest,
            f"stale source {path}",
        )
    return errors


def bridge(data):
    t = data["totals"]
    lines = [
        "# Headcount, occupancy and space bridge",
        "",
        "Generated by `python geospatial/facilities/population/build.py`. Structured evidence: [REGISTER.json](REGISTER.json); accounting policy: [policy.json](policy.json).",
        "",
        f"As of {data['as_of']}; organization publication {data['source_revision']['chart_publication']}. Source file checksums are recorded in the register. This is a source reconciliation, not an employee census.",
        "",
        "| Measure | Population | Interpretation |",
        "|---|---:|---|",
        f"| Current named employees | {t['current_named_employees']} | Unique source-supported employee identities |",
        f"| Current nonemployee directors | {t['current_named_nonemployee_directors']} | Board/visitor planning; excluded from employee count |",
        f"| Current named people | {t['current_named_people']} | Employees plus nonemployee directors |",
        "| J2 authorized billets | 237 | Includes Education 35 and HQ support 28 |",
        "| J2 named occupants | 6 | Existing billets, no new authorization |",
        "| J2 unnamed-status billets | 231 | Occupancy/vacancy unknown |",
        "| Pale Sun / Red Wash selected population | 140 | 12 platform + 128 site |",
        "| ARU / BS&T selected population | 131 | 73 nonrail/corporate + 58 railway |",
        "| 2027 conditional Core workforce | 506 / 591 | Occupied / authorized scenario, not 2026 actual |",
        "| Actual 2026 company headcount / attendance / seats | Unknown | Not inferred by adding the above rows |",
        "",
        "The chart has 54 person displays for 52 unique identities: 51 current and Rachel Kim, a former employee. Daniel Mercer and Priya Raman each appear twice. Sixteen register-only identities remain external, historical, unconfirmed or superseded; they are not employees created by this bridge.",
        "",
        "Each entity/function/role has a nonadditive view with unknown capacity fields. Unique people control the identity total; the six disjoint J2 groups control billet authorization. Chart membership is not a workplace assignment. Other authorized offices remain role evidence, not incremental headcount. No workplace is assigned from a person’s joining year.",
        "",
        "Current need (2026), five-year capacity (2031) and ten-year capacity (2036) remain separate fields. The campus program supplies explicit design assumptions for seats, visitors, training cohorts, residents, peak attendance and area. Those proposed capacities are never written into actual employment fields. The 2027 conditional forecast is preserved as a comparison, not copied to either planning horizon.",
        "",
        "An employee attending a classroom or meeting has moved activity; the employee is not counted again. Rotating teachers and shared support retain one home population. J2 Education is inside 237; ESS does not absorb J2 or Internal Audit. Technology service work-hour/FTE requirements do not establish approved hires or reusable employees.",
        "",
        "Legacy finance numbers (including 431 CoreCo, 126 mine and 132 ARU) are synthetic calibration and cannot replace the accepted industrial selected cases or establish an actual 2026 census. Industrial employees and named leaders overlap; adding 44 named people to 271 industrial workers would double count. Industrial selected populations are not evidence that everyone occupies one office or one shift.",
        "",
        "| J2 group | Authorized | Named | Unnamed status | Proven vacancies |",
        "|---|---:|---:|---:|---|",
    ]
    for g in data["j2"]["groups"]:
        lines.append(
            f"| {g['name']} | {g['authorized_billets']} | {g['current_named_employees']} | {g['unnamed_authorized_billets']} | Unknown |"
        )
    lines += [
        "",
        "Every imported numeric source is linked and checksummed in REGISTER.json. `DISCREPANCY_REPORT.json` is generated only after horizontal and vertical checks; `--check` fails on source drift, duplicate identities, inconsistent totals, or a stale register/bridge/report.",
        "",
    ]
    return "\n".join(lines)


def outputs(data):
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "REGISTER.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        "BRIDGE.md": bridge(data),
        "DISCREPANCY_REPORT.json": json.dumps(
            {
                "record_id": data["record_id"],
                "status": "PASS",
                "errors": [],
                "totals": data["totals"],
                "checks": [
                    "identity deduplication",
                    "J2 horizontal and vertical rollups",
                    "industrial hierarchy",
                    "conditional forecast isolation",
                    "source checksums",
                    "unknown actual measures preserved",
                ],
            },
            indent=2,
        )
        + "\n",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in outputs(build()).items():
        path = HERE / name
        if args.check:
            assert path.exists() and path.read_text() == content, f"stale derivative: {path}"
        else:
            path.write_text(content)
    print("population bridge: PASS")
