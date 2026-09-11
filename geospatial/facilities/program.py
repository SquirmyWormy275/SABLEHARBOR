"""Derive the spatial/attendance/financial planning bridge without changing payroll."""

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/facilities"
SEATS = [
    "assigned_desks",
    "shared_desks",
    "touchdown_seats",
    "training_seats",
    "meeting_seats",
    "resident_beds",
    "dining_seats",
]


def register_errors(actual, expected):
    return [] if actual == expected else ["stale spatial register"]


def build(check=False):
    sources = []
    sites = []
    buildings = []
    floors = []
    for p in sorted((BASE / "source").glob("*.json")):
        d = json.loads(p.read_text())
        for m in d.get("sites", [d]):
            if "buildings" not in m:
                continue
            sources.append(str(p.relative_to(ROOT)))
            site = {
                "id": m["site_id"],
                "name": m["name"],
                "status": m["status"],
                "envelope_m2": m["envelope_m"][0] * m["envelope_m"][1],
                "actual_occupants": None,
                "construction_completion": None,
                "source": str(p.relative_to(ROOT)),
                "gross_area_m2": 0,
                "net_assignable_area_m2": 0,
                "core_circulation_service_m2": 0,
                **{k: 0 for k in SEATS},
            }
            for b in m["buildings"]:
                building = {
                    "id": b["id"],
                    "site_id": m["site_id"],
                    "name": b["name"],
                    "floor_ids": [],
                    "actual_occupants": None,
                    "status": b["status"],
                    "source": str(p.relative_to(ROOT)),
                    "gross_area_m2": 0,
                    "net_assignable_area_m2": 0,
                    "core_circulation_service_m2": 0,
                    **{k: 0 for k in SEATS},
                }
                for f in b["floors"]:
                    row = {
                        "id": f["id"],
                        "building_id": b["id"],
                        "source": str(p.relative_to(ROOT)),
                        "site_id": m["site_id"],
                        "status": f["status"],
                        "gross_area_m2": f["gross_area_m2"],
                        "net_assignable_area_m2": f["net_assignable_area_m2"],
                        "core_circulation_service_m2": f["core_circulation_service_m2"],
                        "planned_peak": f["planned_peak"],
                        "actual_occupants": None,
                        **{k: sum(r.get(k, 0) for r in f["rooms"]) for k in SEATS},
                    }
                    floors.append(row)
                    building["floor_ids"].append(f["id"])
                    for k in SEATS + [
                        "gross_area_m2",
                        "net_assignable_area_m2",
                        "core_circulation_service_m2",
                    ]:
                        building[k] += row[k]
                        site[k] += row[k]
                buildings.append(building)
            sites.append(site)
    sac = next(s for s in sites if s["id"] == "SH-SITE-0001")
    m = json.loads((BASE / "source/campus.json").read_text())
    economics = {
        "status": "ILLUSTRATIVE_UNFUNDED_CAPACITY_COMPARISON",
        "currency": "USD",
        "basis": "Analyst synthetic allowances; not quotes, valuation, appropriations or construction contracts. Land, financing, tax, abnormal ground and offsite utility costs unknown and excluded, not zero. No offset against current finance allowance or payroll.",
        "gross_area_m2": sac["gross_area_m2"],
        "shell_rate_usd_m2": 2500,
        "fitout_rate_usd_m2": 900,
        "site_rate_usd_m2": 125,
        "contingency_fraction": 0.25,
        "land_cost_usd": None,
        "annual_facilities_allowance_existing_conditional": 1140000,
        "existing_allowance_source": "enterprise/business/source/policy.json /corporate_monthly_facility_usd ×12; 2027 conditional",
        "existing_allowance_credit": None,
    }
    shell = sum(
        f["gross_area_m2"]
        for b in m["buildings"]
        for f in b["floors"]
        if "UNFITTED_SHELL" in f["status"]
    )
    economics["unfitted_shell_area_m2"] = shell
    finance_policy = json.loads((ROOT / "enterprise/business/source/policy.json").read_text())
    economics["annual_facilities_allowance_existing_conditional"] = (
        finance_policy["corporate_monthly_facility_usd"] * 12
    )
    sources.append("enterprise/business/source/policy.json")
    economics["initial_fitted_area_m2"] = sac["gross_area_m2"] - shell
    subtotal = (
        sac["gross_area_m2"] * 2500
        + economics["initial_fitted_area_m2"] * 900
        + sac["envelope_m2"] * 125
    )
    economics["base_allowance_usd"] = subtotal
    economics["contingency_usd"] = subtotal * 0.25
    economics["total_excluding_unknowns_usd"] = subtotal * 1.25
    measurement_basis = {
        "source": "geospatial/facilities/population/policy.json /planning_basis",
        "status": "ACTUAL_SPATIAL_ASSIGNMENTS_NOT_ESTABLISHED",
        "meaning": "Organizational people and billet totals are not evidence of assignment to these concept spaces. Null is unknown; physical capacity is recorded separately.",
        "current_named_employees_assigned": None,
        "authorized_positions_assigned": None,
        "vacant_authorized_positions": None,
        "unnamed_authorized_positions": None,
        "remote_staff": None,
        "distributed_staff": None,
        "field_staff": None,
        "deployed_staff": None,
        "resident_occupants": None,
        "visitors": None,
        "customers": None,
        "trainees": None,
        "cohort_peak": None,
        "shift_population": None,
        "observed_maximum_concurrent_attendance": None,
        "proposed_future_positions_by_horizon": {"2026": None, "2031": None, "2036": None},
    }
    for row in sites + buildings + floors:
        row["population_measurements"] = measurement_basis.copy()
    report = {
        "revision": "0.2.0",
        "sources": sorted(set(sources)),
        "population_source": "geospatial/facilities/population/REGISTER.json",
        "scope": "Architectural planning capacities; no actual enterprise census or payroll restatement. Site floor maxima are not additive when cohorts move.",
        "sites": sites,
        "buildings": buildings,
        "floors": floors,
        "sacramento_scenarios": m["attendance_scenarios"],
        "sacramento_economics": economics,
    }
    sac_buildings = [b for b in buildings if b["site_id"] == m["site_id"]]
    sac_floors = [f for f in floors if f["site_id"] == m["site_id"]]
    totals = {
        "buildings": len(sac_buildings),
        "floors": len(sac_floors),
        "gross_area_sqft": sum(f["gross_area_sqft"] for b in m["buildings"] for f in b["floors"]),
        "fitted_staff_workplaces": sum(sac[k] for k in SEATS[:3]),
        "single_rooms": sum(
            r.get("single_room", False)
            for b in m["buildings"]
            for f in b["floors"]
            for r in f["rooms"]
        ),
        "campus_dining_seats": sac["dining_seats"],
        "resident_beds": sac["resident_beds"],
    }
    for key, value in totals.items():
        if key in m["program_totals"] and value != m["program_totals"][key]:
            raise ValueError(f"Campus source rollup mismatch: {key}")
    for f in floors:
        if not math.isclose(
            f["gross_area_m2"],
            f["net_assignable_area_m2"] + f["core_circulation_service_m2"],
            abs_tol=0.01,
        ):
            raise ValueError(f"Floor area does not reconcile: {f['id']}")
    for scenario in m["attendance_scenarios"]:
        if (
            "floor_populations" in scenario
            and sum(scenario["floor_populations"].values()) != scenario["people"]
        ):
            raise ValueError(f"Scenario floor attendance mismatch: {scenario['id']}")
        if (
            "workers" in scenario
            and sum(scenario[k] for k in ("workers", "trainees", "other_visitors"))
            != scenario["people"]
        ):
            raise ValueError(f"Scenario person category mismatch: {scenario['id']}")
    report["sacramento_totals"] = totals
    report["sacramento_phases"] = m["phases"]
    report["sacramento_reference_sha256"] = m["approved_reference_sha256"]
    report["sacramento_assumptions"] = m["assumptions"]
    report["sacramento_conditional_workforce_comparison"] = {
        "status": finance_policy["fact_state"],
        "horizon": finance_policy["start_year"],
        "source": "enterprise/business/source/policy.json /workforce",
        "foundry_field_occupied_scenario": finance_policy["workforce"]["foundry-field"]["occupied"],
        "atlas_meridian_occupied_scenario": finance_policy["workforce"]["atlas-meridian"][
            "occupied"
        ],
        "meaning": "R01 floor labels repeat these conditional planning populations. They do not establish actual 2026 employees, daily campus attendance or assigned desks.",
    }
    register_text = json.dumps(report, indent=2) + "\n"
    lines = [
        "# Headcount, occupancy and space program",
        "",
        report["scope"],
        "",
        "Every site, building and floor explicitly records unknown actual named assignments, authorized/unnamed/vacant positions, remote/distributed/field/deployed staff, residents, visitors/customers/trainees, shift/cohort peaks and proposed positions at 2026/2031/2036 horizons. Null means evidence is missing. Design capacity does not fill these fields with assumed employees.",
        "",
        "[Population evidence](population/BRIDGE.md) separates 44 named employees, seven nonemployee directors and J2’s 237 authorized billets. The 231 J2 billets without named occupants are not proven vacancies. Education’s 35 billets and headquarters’ 28 are inside the 237. JAG remains six five-person teams; its twelve touchdown desks do not reduce its authorization to twelve people.",
        "",
        "The [R02 source](source/campus.json) preserves the [approved R01 visual baseline](../../docs/facilities/references/sacramento-hq/r01-approved/START_HERE_CODEX.md). Four buildings and ten floors provide 362 fitted workplaces and 60 single rooms within the 840 × 600 ft study envelope. Seven floor layouts extend the three approved reference floors. These are modelled designs, not as-built or occupied premises. SH-SITE-0014 retains the unresolved actual Education location; co-location here is a design assumption. Tenure and construction/occupancy dates remain unestablished.",
        "",
        "## Sacramento attendance and capacity",
        "",
        "| Scenario | Horizon | Concurrent people | Status |",
        "|---|---:|---:|---|",
    ]
    for scenario in m["attendance_scenarios"]:
        lines.append(
            f"| {scenario['id']} | {scenario['horizon']} | {scenario['people']} | {scenario['status']} |"
        )
    lines += [
        "",
        "The 2026 day scenario contains 362 workplace users, four shared hospitality attendees, 120 learners and 18 visitors: 504 people. This is a design load, not observed attendance or hiring authorization. Forty-eight resident learners are already inside the 120. The separate night scenario provides 48 cohort rooms and twelve faculty/visitor rooms, one resident per room. Day and night populations are not added together.",
        "",
        "Corporate has 200 workplaces (40/112/48 by floor); J2 has 130 (62/68); Education has 32 (4/28). Corporate L02 preserves Foundry Field’s 80 workstations and Atlas Meridian’s 32. The R01 labels of 160 Foundry staff and 36 Atlas staff repeat the conditional 2027 workforce scenario in enterprise/business/source/policy.json; they do not prove actual 2026 payroll, Sacramento assignments or simultaneous attendance. Shared desks and distributed work explain why staffing scenarios and fitted seats differ, without asserting an unsupported attendance ratio.",
        "",
        "Education L01 has a 120-seat hall and two 24-seat classrooms. Upper-floor classrooms provide further alternative teaching arrangements. The same cohort moves among these spaces; the campus learner scenario remains 120. Meeting and dining capacities similarly accommodate people already counted. Dining is a separate category: 80 seats in Corporate and 80 in Education, served by one production kitchen in Education. Both 2031 and 2036 hold the same fitted capacity; no future positions, extra shell, wing or construction schedule is authorized.",
        "",
        "## Area and seat schedule",
        "",
        "| Building | Floors | Gross m² | Assignable m² | Core/service m² | Workplaces¹ | Training | Meeting | Dining | Beds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for b in buildings:
        lines.append(
            f"| {b['name']} ({b['id']}) | {len(b['floor_ids'])} | {b['gross_area_m2']:,.1f} | {b['net_assignable_area_m2']:,.1f} | {b['core_circulation_service_m2']:,.1f} | {sum(b[k] for k in SEATS[:3])} | {b['training_seats']} | {b['meeting_seats']} | {b['dining_seats']} | {b['resident_beds']} |"
        )
    lines += [
        "",
        f"Sacramento totals: {totals['buildings']} buildings, {totals['floors']} floors, {totals['gross_area_sqft']:,.0f} sf ({sac['gross_area_m2']:,.1f} m²), {totals['fitted_staff_workplaces']} workplaces and {totals['resident_beds']} beds in {totals['single_rooms']} single rooms.",
        "",
        "¹ Assigned, shared/hot and touchdown desks remain separate in SPACE_REGISTER.json. No desk type is an employee count. Room rectangles determine assignable area, including explicitly programmed support rooms. Fixed cores and circulation are separately partitioned from rooms and remain stacked across each building. Exact arithmetic checks the model; it does not claim surveyed or construction precision. Floor peak capacities are not summed into an enterprise workforce census.",
        "",
        "## Master, access and technical boundaries",
        "",
        "Corporate houses officers, ESS services, Advisory, product organizations and a separately controlled Internal Audit suite. Audit remains accountable to the Board boundary. J2 occupies its own controlled building outside ESS, with reception and interview access separated from restricted work. Education and residence use the shared pedestrian network with distinct teaching and quiet residential arrivals. The coordinated R01 master controls footprints, access, courts, parking and the perimeter emergency/service loop. Local edge/communications rooms do not constitute a primary production data center.",
        "",
        f"Parking records {m['access']['parking_spaces']} drawn bays before accessible-bay conversion. Bicycle capacity, mode shares, event overflow and demand remain unresolved; no unsupported 200-space supply/demand balance is claimed. The 840 × 600 ft local frame is not a surveyed parcel. Structural member sizes, accessible and protected egress, sanitary provision, mechanical loads, fire access turning, utility connections, flood/brownfield and stormwater engineering remain technical dependencies.",
        "",
        "## Capital and facilities bridge",
        "",
        f"Gross area {sac['gross_area_m2']:,.1f} m² includes {shell:,.1f} m² explicitly designated unfitted shell, derived from floor status. All ten R02 floors are conceptually programmed, with no construction completion claim. Synthetic shell allowance $2,500/m², fit-out $900/m² and site works $125/m² produce ${subtotal:,.0f} before 25% contingency and ${subtotal * 1.25:,.0f} including contingency. Land, abnormal ground, offsite utilities, financing and tax remain unknown and excluded. These rates are illustrative comparison inputs, not researched market prices, quotes, valuation or funding approval.",
        "",
        f"The existing {finance_policy['start_year']} conditional corporate facilities allowance of ${economics['annual_facilities_allowance_existing_conditional']:,.0f}/year is preserved from enterprise/business/source/policy.json and receives no automatic credit. Capital, depreciation, recurring facilities expense and payroll are distinct. This comparison does not alter the finance model or claim its allowance funds construction. A successor financial decision requires supported tenure, procurement, engineering, lifecycle costs and staffing evidence.",
        "",
        "## September state and phasing",
        "",
        "| Phase | Evidence date | State | Dependency |",
        "|---|---|---|---|",
    ]
    for phase in m["phases"]:
        lines.append(
            f"| {phase['name']} | {phase['date'] or 'Unestablished'} | {phase['state']} | {phase['dependency']} |"
        )
    lines += [
        "",
        "Sources, category definitions, floor rollups, capacities, scenarios and assumptions are machine readable in [SPACE_REGISTER.json](SPACE_REGISTER.json). Existing industrial facility assigned FTE 137 equals 131 ARU/BS&T plus six receiving staff already within Red Wash’s 128. Facility assignments do not form an additive enterprise employee total.",
        "",
        "Regenerate with `.venv/bin/python geospatial/facilities/program.py`; verify exact derived content with the same command plus `--check`. The generator rejects conflicting source totals, floor area sums and scenario rollups; the facilities validator also checks geometry, coverage and category distinctions.",
    ]
    text = "\n".join(lines) + "\n"
    if check:
        errors = register_errors(json.loads((BASE / "SPACE_REGISTER.json").read_text()), report)
        if (BASE / "PROGRAM.md").read_text() != text:
            errors.append("stale human-readable space program")
        if errors:
            raise SystemExit("\n".join(errors))
    else:
        (BASE / "SPACE_REGISTER.json").write_text(register_text)
        (BASE / "PROGRAM.md").write_text(text)
    print(f"{len(sites)} sites / {len(buildings)} buildings / {len(floors)} floors reconciled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    build(check=parser.parse_args().check)
