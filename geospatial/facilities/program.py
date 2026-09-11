"""Derive the spatial/attendance/financial planning bridge without changing payroll."""

import argparse
import json
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
                    "gross_area_m2": 0,
                    "net_assignable_area_m2": 0,
                    "core_circulation_service_m2": 0,
                    **{k: 0 for k in SEATS},
                }
                for f in b["floors"]:
                    row = {
                        "id": f["id"],
                        "building_id": b["id"],
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
    shell = m["buildings"][1]["floors"][2]["gross_area_m2"]
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
        "revision": "0.1.0",
        "sources": sorted(set(sources)),
        "population_source": "geospatial/facilities/population/REGISTER.json",
        "scope": "Architectural planning capacities; no actual enterprise census or payroll restatement. Site floor maxima are not additive when cohorts move.",
        "sites": sites,
        "buildings": buildings,
        "floors": floors,
        "sacramento_scenarios": m["attendance_scenarios"],
        "sacramento_economics": economics,
    }
    register_text = json.dumps(report, indent=2) + "\n"
    lines = [
        "# Headcount, occupancy and space program",
        "",
        report["scope"],
        "",
        "Every site, building and floor explicitly records unknown actual named assignments, authorized/unnamed/vacant positions, remote/distributed/field/deployed staff, residents, visitors/customers/trainees, shift/cohort peaks and proposed positions at 2026/2031/2036 horizons. These nulls preserve missing workforce evidence; the separate design scenarios and seat capacities do not fill them with assumed employees.",
        "",
        "[Population evidence](population/BRIDGE.md) separates 44 named employees, seven nonemployee directors, J2’s237 authorized billets and conditional financial populations. 231 J2 billets lack named occupants; that is not231 proven vacancies.",
        "",
        "The [source program](source/campus.json) is the authority for this planning option. Geometry and capacities are assumptions under SAC-A01–05. Education co-location and residence are modelled here; SH-SITE-0014 remains the unresolved record for actual Education location. All acquisition, construction, commissioning and occupancy dates are null.",
        "",
        "## Sacramento scenario reconciliation",
        "",
        "| Scenario | Horizon | Concurrent people | Meaning |",
        "|---|---:|---:|---|",
    ]
    for s in m["attendance_scenarios"]:
        lines.append(f"| {s['id']} | {s['horizon']} | {s['people']} | {s['status']} |")
    lines += [
        "",
        "The 2026 design-event scenario has 272 anonymous worker places, 120 trainees and 28 other visitors: 420 people. 46 resident trainees are already within the 120 and move to residence overnight. Night 50 comprises 46 trainees and 4 duty staff. These are design loads, not a finding of current attendance or approval of 272 positions. Meeting/dining seats accommodate the same people across the day. The five-year shell option adds 64 concurrent places; the ten-year reserved-wing option adds 80. Those increments authorize no hiring or construction and need new fit-out/parking design before execution.",
        "",
        "## Area and seat schedule",
        "",
        "| Building | Floors | Gross m² | Assignable m² | Core/service m² | Work seats¹ | Training | Meeting | Beds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for b in buildings:
        lines.append(
            f"| {b['name']} | {len(b['floor_ids'])} | {b['gross_area_m2']:,.1f} | {b['net_assignable_area_m2']:,.1f} | {b['core_circulation_service_m2']:,.1f} | {sum(b[k] for k in SEATS[:3])} | {b['training_seats']} | {b['meeting_seats']} | {b['resident_beds']} |"
        )
    lines += [
        "",
        "¹ Assigned, shared/hot and touchdown desks remain separate in SPACE_REGISTER.json. No desk type is an employee count. Room rectangles determine assignable area; the difference from footprint×levels determines circulation/core/service area. Exact arithmetic describes the model, not measurement precision. Room-level service areas are included in assignable room totals where the programme allocates them explicitly; common end cores/circulation are additional.",
        "",
        "## Sacramento master and access",
        "",
        "Governance and ESS share the public arrival edge. Internal Audit has a separate controlled suite with Board access. J2 occupies a separate building with a controlled entrance and no public through-route. Education/classrooms and residential approach use the pedestrian network. North delivery and the perimeter emergency loop separate receiving from ordinary arrival. Bicycles 64 and parking 200 are explicit assumptions: 420×55% car mode / 1.2 persons per vehicle ≈ 193 spaces. Later horizons require a revised mobility scheme.",
        "",
        "The 6 m planning grid is schematic; final column/slab design, fire separation, corridor clearances, protected stairs, sanitary demand, accessible suites and lifts, mechanical zoning, flood/brownfield screening, utility diversity and stormwater discharge require coordinated engineering. Local plans are not transformed into geographic parcel polygons. Durable restrained modernism uses concrete/metal/stone, warm interior timber, shaded paths and a modest signature arrival monument.",
        "",
        "## Capital and facilities bridge",
        "",
        f"Sacramento gross area {sac['gross_area_m2']:,.0f} m² includes {shell:,.0f} m² unfitted shell. Illustrative shell $2,500/m², fit-out $900/m² and site works $125/m² yield ${subtotal:,.0f} before 25% contingency, or ${subtotal * 1.25:,.0f} excluding unknown land/offsite/abnormal/financing costs. These synthetic rates are comparison inputs, not researched market prices or an approved funding request.",
        "",
        "The existing 2027 conditional corporate facilities allowance of $1,140,000/year is retained and receives no automatic credit. Capital, depreciation, lease/operating expense and staffing are not interchangeable. This unfunded space scenario does not amend the finance model or claim that its recurring allowance pays for the campus. Procurement must reconcile actual tenure, lease versus build, lifecycle maintenance, rates and funded staffing before a financial successor adopts costs.",
        "",
        "## September state and phasing",
        "",
        "| Phase | State as of 11 September 2026 | Dependency |",
        "|---|---|---|",
        "| District and institutional direction | Accepted canon | Preserve Sacramento / Railyards–River District |",
        "| Parcel / title / site studies | Unestablished | Supported siting, access, utilities and environmental review |",
        "| Master programme and concept floors | Modelled proposal | Integrated programme acceptance |",
        "| Shell, fit-out and commissioning | No completion asserted | Approved capital, coordinated engineering and execution evidence |",
        "| 2031 shell use / 2036 reserve | Conditional capacity options | Demand and mobility review; no scheduled delivery dates |",
        "",
        "Sources, floor rollups and capacities are machine readable in [SPACE_REGISTER.json](SPACE_REGISTER.json). Existing industrial facility assigned FTE 137 equals 131 ARU/BS&T plus six receiving staff already within Red Wash 128. No enterprise employee total is obtained by adding facility assignments.",
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
