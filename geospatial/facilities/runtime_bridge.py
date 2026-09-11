"""Link accepted runtime source/plans into facilities without duplicating authority.

PR119 became main during R02 closeout. Its twelve immutable publication plates
remain at their accepted paths and retain their original visual/status system.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE = ROOT / "geospatial/facilities"
SITES = ROOT / "enterprise/services/source/runtime_sites_2026-09-11.json"
CAPITAL = ROOT / "enterprise/services/source/runtime_capital_plan_2026-09-11.json"
VISUALS = ROOT / "enterprise/runtime/visuals"
REGISTER = ROOT / "geospatial/registers/MAP_ID_REGISTER.json"
OUTPUT = BASE / "RUNTIME_BRIDGE.json"
ACCEPTED_MAIN = "b83e4be2182a5e4143808a3dab5f8d929a133caf"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    from enterprise.runtime.design import floor_rooms

    source = json.loads(SITES.read_text())
    capital = json.loads(CAPITAL.read_text())["implementation_assumptions"]
    published = json.loads((VISUALS / "manifest.json").read_text())
    allocation = {r["logical_id"]: r["map_id"] for r in json.loads(REGISTER.read_text())["records"]}
    sites = []
    unknown = {
        "current_named_employees": None,
        "authorized_billets": None,
        "vacant_or_unnamed_authorized_roles": None,
        "proposed_future_positions": None,
        "remote_distributed_field_deployed": None,
        "resident_occupants": None,
        "visitors_customers_trainees": None,
        "shift_population": None,
        "maximum_concurrent_attendance": None,
        "assigned_desks": None,
        "shared_desks": None,
        "touchdown_seats": None,
        "training_seats": None,
        "meeting_seats": None,
        "basis": "Runtime authority establishes proposed technical requirements and room areas, not measured occupant or fitted-seat counts. Unknown is not zero.",
    }
    for row in source["sites"]:
        owned = row["id"] == "RUNTIME-NN-OWNED-DC"
        sites.append(
            {
                "site_id": row["geospatial_site_id"],
                "runtime_id": row["id"],
                "facility_id": row["facility_id"],
                "name": row["name"],
                "status": row["status"],
                "geometry_status": "SYNTHETIC_UNSURVEYED"
                if owned
                else "PROVIDER_GEOMETRY_UNVERIFIED",
                "geometry_basis": "Accepted 7.5-acre fictional parcel at planning pin 39.5450,-119.4550; geographic polygon in runtime_parcel.geojson. Proposed building only; no vertical construction or commissioned capacity."
                if owned
                else "Selected provider geography is accepted; exact provider building, assigned cage and tenancy remain unverified. Customer-enclosure plates are requirements, not provider floor plans.",
                "fictionality": row.get("fictionality", "REAL_EXTERNAL_PROVIDER_PROPOSED_TENANCY"),
                "tenure": "SYNTHETIC_ACQUISITION_NOT_REAL_TITLE"
                if owned
                else "PROVIDER_SELECTED_NO_EXECUTED_TENANCY",
                "occupancy_start": None,
                "planning_acquisition_date": row.get("planning_purchase_date"),
                "actual_construction_completion": None,
                "operating": row["operating"],
                "recorded_on": source["recorded_on"],
                "authoritative_base": ACCEPTED_MAIN,
                "source_path": str(SITES.relative_to(ROOT)),
                "source_runtime_id": row["id"],
                "population_and_capacity": dict(unknown),
                "horizons": [
                    {
                        "year": year,
                        "population_and_capacity": dict(unknown),
                        "status": "CURRENT_EVIDENCE_UNKNOWN"
                        if year == 2026
                        else "CONDITIONAL_REQUIREMENTS_NOT_OCCUPANCY",
                    }
                    for year in [2026, 2031, 2036]
                ],
                "floor_exemption": None
                if owned
                else "External selected provider. No occupied Sable Harbor building or assigned floor established. Reuse only topology and customer-enclosure/equipment concepts; do not invent provider interiors.",
                "buildings": [],
            }
        )
    owned = next(s for s in sites if s["site_id"] == "SH-SITE-0030")
    building_id = "SH-SITE-0030-B01"
    floor_id = building_id + "-L01"
    rooms = floor_rooms(capital)
    floor = {
        "id": floor_id,
        "name": "Northern Nevada data center / proposed level 01",
        "level": 1,
        "status": "PROPOSED_DESIGN_NOT_CONSTRUCTED",
        "gross_area_sqft": sum(r["area_sf"] for r in capital["rooms"]),
        "gross_area_m2": 12000 * 0.09290304,
        "net_assignable_area_sqft": 10350,
        "net_assignable_area_m2": 10350 * 0.09290304,
        "core_circulation_service_sqft": 1650,
        "core_circulation_service_m2": 1650 * 0.09290304,
        "planned_peak": None,
        "population_and_capacity": dict(unknown),
        "rooms": [
            {
                **r,
                "id": floor_id + f"-R{i:02}",
                "geometry_units": "feet",
                "geometry_authority": "enterprise/runtime/design.py::floor_rooms",
                "status": "PROPOSED_DESIGN_NOT_CONSTRUCTED",
            }
            for i, r in enumerate(rooms, 1)
        ],
        "source_artifact": "enterprise/runtime/visuals/04-space-block-plan.svg",
        "source_room_schedule": str(CAPITAL.relative_to(ROOT))
        + "#/implementation_assumptions/rooms",
    }
    assert floor["gross_area_sqft"] == 12000
    assert abs(sum(r["area_sf"] for r in rooms) - 10350) < 0.0001
    owned["buildings"] = [
        {
            "id": building_id,
            "name": "Northern Nevada proposed data center",
            "status": "PROPOSED_DESIGN_NOT_CONSTRUCTED",
            "floor_count": 1,
            "footprint_ft": [120, 100],
            "population_and_capacity": dict(unknown),
            "floors": [floor],
        }
    ]
    specs = [
        ("01-topology", "Three-site runtime topology", "context", "SH-SITE-0028", None, None),
        (
            "02-current-condition",
            "Northern Nevada / September current condition",
            "current_site",
            "SH-SITE-0030",
            None,
            None,
        ),
        (
            "03-site-concept",
            "Northern Nevada / proposed site relationships",
            "site",
            "SH-SITE-0030",
            None,
            None,
        ),
        (
            "04-space-block-plan",
            "Northern Nevada / proposed level 01",
            "floor",
            "SH-SITE-0030",
            building_id,
            floor_id,
        ),
        (
            "05-utility-zones",
            "Northern Nevada / utility and expansion requirements",
            "utilities",
            "SH-SITE-0030",
            None,
            None,
        ),
        (
            "06-electrical-concept",
            "Northern Nevada / electrical concept",
            "building",
            "SH-SITE-0030",
            building_id,
            None,
        ),
        (
            "07-cooling-concept",
            "Northern Nevada / cooling concept",
            "building",
            "SH-SITE-0030",
            building_id,
            None,
        ),
        (
            "08-enclosure-reno",
            "Switch Reno / customer-enclosure requirement",
            "customer_enclosure",
            "SH-SITE-0028",
            None,
            None,
        ),
        (
            "09-enclosure-boise",
            "IDACORE Boise / customer-enclosure requirement",
            "customer_enclosure",
            "SH-SITE-0029",
            None,
            None,
        ),
        (
            "10-rack-elevations",
            "Runtime / configuration-class rack elevations",
            "equipment",
            "SH-SITE-0030",
            building_id,
            None,
        ),
        (
            "11-logical-boundaries",
            "Runtime / logical and recovery boundaries",
            "context",
            "SH-SITE-0028",
            None,
            None,
        ),
        (
            "12-construction-schedule",
            "Northern Nevada / conditional construction schedule",
            "phasing",
            "SH-SITE-0030",
            None,
            None,
        ),
    ]
    maps = []
    for stem, title, kind, sid, bid, fid in specs:
        artifacts = {}
        for ext in ["svg", "png", "pdf"]:
            p = VISUALS / (stem + "." + ext)
            digest = sha(p)
            assert digest == published["files"][p.name], "stale accepted runtime artifact " + p.name
            artifacts[ext] = {"path": str(p.relative_to(ROOT)), "sha256": digest}
        maps.append(
            {
                "id": allocation["runtime::" + stem],
                "title": title,
                "kind": kind,
                "site_id": sid,
                "building_id": bid,
                "floor_id": fid,
                "related_site_ids": ["SH-SITE-0028", "SH-SITE-0029", "SH-SITE-0030"]
                if stem in ["01-topology", "10-rack-elevations", "11-logical-boundaries"]
                else [sid],
                "status": "LAND_ACQUIRED_PRECONSTRUCTION"
                if stem == "02-current-condition"
                else "SYNTHETIC_CONCEPT_NOT_AS_BUILT",
                "revision": "ACCEPTED_RUNTIME_1.0.0",
                "builder": "enterprise/runtime/render.py",
                "artifact_ownership": "LINKED_ACCEPTED_MAIN_NOT_REGENERATED_BY_FACILITY_RENDERER",
                "artifacts": artifacts,
            }
        )
    inputs = [
        Path(__file__),
        SITES,
        CAPITAL,
        VISUALS / "manifest.json",
        ROOT / "enterprise/runtime/design.py",
        ROOT / "enterprise/runtime/render.py",
        REGISTER,
        ROOT / "geospatial/geojson/runtime_parcel.geojson",
    ]
    return {
        "revision": "1.0.0",
        "integration_base": ACCEPTED_MAIN,
        "initial_facility_base": "786fc9a5311a04dde92ee6dbb08ac3b77a380200",
        "authority": "PR119 accepted by merge b83e4be; runtime source metadata saying pending merge records its preparation state and is not a reason to omit accepted main.",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "sites": sites,
        "maps": maps,
        "totals": {
            "sites": 3,
            "external_provider_exemptions": 2,
            "proposed_buildings": 1,
            "proposed_floors": 1,
            "plates": 12,
            "independent_artifacts": 36,
            "gross_area_sqft": 12000,
            "actual_named_people_added": 0,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(build(), indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != text:
            raise SystemExit("Runtime facility bridge is stale")
        print("Runtime linked program: 3 sites / 1 proposed building / 1 floor / 12 plates PASS")
    else:
        OUTPUT.write_text(text)
        print("Linked accepted runtime source and 36 unchanged visual artifacts")


if __name__ == "__main__":
    main()
