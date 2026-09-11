#!/usr/bin/env python3
"""Reconcile upstream censuses without promoting their records to new properties."""

import collections
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "geospatial/facilities/coverage"


def read(p):
    return json.loads((ROOT / p).read_text())


CAT = "geospatial/sources/catalog.json"
CHART = "docs/organization/source/chartbook.json"
OPS = "industrial/source/operations.json"
COMP = "enterprise/services/source/components.json"
RUNTIME = "enterprise/services/source/runtime_sites_2026-09-11.json"
ACCEPTED_MAIN = "b83e4be2182a5e4143808a3dab5f8d929a133caf"
CLASSES = {
    1: "campus master plan",
    2: "operating site plan",
    3: "building and floor design",
    4: "structure/context or exemption",
    5: "external context only",
    6: "distributed/nonphysical/reference",
    7: "historical treatment",
    8: "proposed/unresolved disposition",
}
ALIASES = {
    "CORP-HQ": "SH-SITE-0001",
    "CORP-CENTER": "SH-SITE-0001",
    "J2-EDU-CAMPUS": "SH-SITE-0014",
    "J2-HQ": "SH-SITE-0015",
    "taylor-hub": "SH-SITE-0007",
    "red-wash-mine": "SH-SITE-0006",
    "red-wash-access": "SH-RAIL-0002",
    "bedford": "SH-SITE-0005",
    "fort": "SH-SITE-0003",
    "fort-big": "SH-FAC-FORT-BIG",
    "fort-small": "SH-FAC-FORT-SMALL",
    "fort-white": "SH-FAC-FORT-WHITE",
    "fort-museum": "SH-FAC-FORT-MUSEUM",
    "klein-shop": "SH-SITE-0002",
    "stream17": "SH-SITE-0023",
    "demotte-gen1": "SH-SITE-0027",
    "glasshouse": "SH-SITE-0024",
    "wallaby": "SH-SITE-0022",
    "blackridge": "SH-SITE-0009",
    "BST-MAIN": "SH-RAIL-0001",
    "BST-EAST": "SH-IND-BST-EAST",
    "BST-MINERAL": "SH-IND-BST-MINERAL",
    "FAC-HQ": "SH-SITE-0001",
    "FAC-FORT": "SH-SITE-0003",
    "FAC-BEDFORD": "SH-SITE-0005",
    "FAC-REDWASH": "SH-SITE-0006",
    "FAC-TAYLOR": "SH-SITE-0007",
    "FAC-EDUCATION": "SH-SITE-0014",
    "FAC-ALEXANDRIA": "SH-SITE-0016",
    "ROAD-RW-01": "SH-RAIL-0002",
}
BUILDINGS = {
    "SH-FAC-FORT-BIG",
    "SH-FAC-FORT-SMALL",
    "SH-FAC-FORT-WHITE",
    "SH-IND-FAC-TAY-WAREHOUSE",
    "SH-IND-FAC-RAW-WAREHOUSE",
    "SH-IND-FAC-ARU-OFFICE",
}
PARENTS = {
    **{
        i: "SH-SITE-0003"
        for i in ["SH-FAC-FORT-BIG", "SH-FAC-FORT-SMALL", "SH-FAC-FORT-WHITE", "SH-FAC-FORT-MUSEUM"]
    },
    **{
        "SH-IND-" + i: "SH-SITE-0007"
        for i in [
            "FAC-TAY-YARD",
            "FAC-TAY-TERMINAL",
            "FAC-TAY-WAREHOUSE",
            "FAC-TAY-TRUCK",
            "FAC-ARU-OFFICE",
        ]
    },
    "SH-IND-FAC-RW-RECEIVING": "SH-SITE-0006",
    "SH-IND-FAC-WAM-INT": "SH-SITE-0008",
}


def classification(x):
    i, t, _s = x["object_id"], x["object_type"], x["census_status"]
    if i in ["SH-SITE-0028", "SH-SITE-0029"]:
        return (
            5,
            "Accepted selected external provider; context only. Contract, assigned building/cage, reserved capacity and operating acceptance remain unestablished.",
        )
    if i == "SH-SITE-0030":
        return (
            2,
            "Accepted synthetic acquired parcel, preconstruction. Site and proposed building/floor concept required; no completed shell or operating data center.",
        )
    if i in BUILDINGS:
        return (
            3,
            "Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown.",
        )
    if i in ["SH-SITE-0001", "SH-SITE-0003"]:
        return 1, "Integrated campus concept required; study envelope is not a property claim."
    if i in ["SH-SITE-0002", "SH-SITE-0004", "SH-SITE-0022", "SH-SITE-0026", "SH-RAIL-0003"]:
        return (
            7,
            "Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry.",
        )
    if t in [
        "HOST_PROCESS_SITE",
        "CUSTOMER_MINE",
        "CUSTOMER_ASSET_FAMILY",
        "EXTERNAL_DELIVERY_SITE",
    ]:
        return (
            5,
            "Host/customer retains property and operating authority; only permitted context and bounded intervention are represented.",
        )
    if t == "EVENT" or i.startswith("SH-REF-"):
        return (
            6,
            "Event or real-world reference is not an enterprise property and creates no building requirement.",
        )
    if t == "RAIL_STRUCTURE":
        return (
            4,
            "Rail/civil structure; retain current engineering context. Architectural floors do not apply; no new span, clearance or civil engineering invented.",
        )
    if t in [
        "TRACK_REGISTER_SEGMENT",
        "RAIL_BRANCH",
        "RAIL_ROUTE",
        "INTERFACE_ALTERNATIVE",
        "WORKING_YARD",
    ]:
        return (
            4,
            "Linear transport or outdoor yard asset; no occupied building or architectural floor established by this record.",
        )
    if i.startswith("SH-FAC-RW-") or i.startswith("SH-BR-") and i != "SH-BR-AREA-001":
        return (
            8,
            "Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry.",
        )
    if (
        i
        in [
            "SH-SITE-0005",
            "SH-SITE-0006",
            "SH-SITE-0007",
            "SH-SITE-0008",
            "SH-SITE-0009",
            "SH-SITE-0020",
        ]
        or t == "FACILITY"
    ):
        return (
            2,
            "Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them.",
        )
    return (
        8,
        "Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy.",
    )


def build():
    records = {}
    runtime_sites = read(RUNTIME)["sites"]
    for site in runtime_sites:
        ALIASES[site["id"]] = site["geospatial_site_id"]
        ALIASES[site["facility_id"]] = site["geospatial_site_id"]
    census = []
    inputs = {}

    def source(p):
        inputs[p] = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

    def bind(p, section, ident, target):
        source(p)
        census.append(
            {"source_path": p, "section": section, "source_id": str(ident), "coverage_id": target}
        )

    for x in read(CAT)["objects"]:
        i = x["object_id"]
        cl, reason = classification(x)
        records[i] = {
            "id": i,
            "name": x["canonical_name"],
            "class": cl,
            "classification": CLASSES[cl],
            "parent_id": PARENTS.get(i),
            "reason": reason,
            "source_type": x["object_type"],
            "canon_status": x["canon_status"],
            "status": "historical"
            if cl == 7
            else "external"
            if cl == 5
            else "illustrative"
            if "SOURCE_IMAGE" in x["object_type"] or x["object_type"].startswith("GENERATED_")
            else "unresolved"
            if cl == 8
            else x["census_status"].lower(),
            "tenure": "unknown; entity affiliation is not evidence of property title",
            "occupancy_start": None,
            "occupancy_end": None,
            "relevant_date": x.get("relevant_date") or None,
            "date_precision": x.get("date_precision", "UNKNOWN"),
            "precision": x["granularity"],
            "fictionality": x["fictionality"],
            "provenance": [
                {
                    "path": x["source_path"],
                    "locator": x.get("source_locator"),
                    "source_id": x["source_id"],
                }
            ],
            "detail_issue": "#107" if cl in [1, 2, 3, 8] else "#106" if cl in [5, 7] else None,
            "geometry_issue": "#106" if cl != 6 else None,
            "required_artifacts": ["context", "site", "building_program", "floor_plans"]
            if cl == 3
            else ["context", "site", "program"]
            if cl in [1, 2]
            else ["context", "disposition"]
            if cl in [5, 7, 8]
            else ["disposition"],
            "package_required": cl in [1, 2, 3, 5, 7, 8],
            "actual_floor_count": None,
            "actual_occupancy": None,
        }
        bind(CAT, "objects", i, i)
    for site in runtime_sites:
        target = site["geospatial_site_id"]
        record = records[target]
        record["runtime_state"] = site["status"]
        record["runtime_source"] = site
        record["status"] = "external" if site.get("provider") else "land_acquired_preconstruction"
        record["tenure"] = (
            "Selected external provider; no executed contract or capacity reservation"
            if site.get("provider")
            else "Accepted fictional planning-universe acquisition, 2026-09-04; no real APN or real-world title claim"
        )
        record["provenance"].append({"path": RUNTIME, "locator": "sites/" + site["id"]})
        if not site.get("provider"):
            record["planned_building_ids"] = [target + "-B01"]
            record["planned_floor_ids"] = [target + "-B01-L01"]
            record["required_artifacts"] += ["building_program", "floor_plans"]
        bind(RUNTIME, "sites", site["id"], target)
    # Alexandria is a workload-hosting identity, not a fourth runtime property.
    records["SH-SITE-0016"]["runtime_placement_site_ids"] = [
        site["geospatial_site_id"] for site in runtime_sites
    ]
    records["SH-SITE-0016"]["reason"] = (
        "Retained Alexandria hosting identity. Accepted runtime placement uses Reno primary, Boise recovery and the proposed owned Northern Nevada end state; no separate Alexandria building is established."
    )
    for x in read(OPS)["facilities"] + read(OPS)["structures"]:
        ALIASES[x["id"]] = "SH-IND-" + x["id"]
    for i in records:
        if i.startswith("SH-IND-"):
            ALIASES[i[7:]] = i

    def extra(i, name, cl, reason, prov, status="unresolved"):
        if i not in records:
            records[i] = {
                "id": i,
                "name": name,
                "class": cl,
                "classification": CLASSES[cl],
                "parent_id": None,
                "reason": reason,
                "source_type": "SUPPLEMENTAL_CENSUS",
                "canon_status": "SOURCE_RECORD_ONLY",
                "status": status,
                "tenure": "unknown",
                "occupancy_start": None,
                "occupancy_end": None,
                "relevant_date": None,
                "date_precision": "UNKNOWN",
                "precision": "UNLOCATED",
                "fictionality": "SYNTHETIC_ENTERPRISE_RECORD",
                "provenance": prov,
                "detail_issue": "#107" if cl == 8 else None,
                "geometry_issue": "#106" if cl in [5, 7, 8] else None,
                "required_artifacts": ["context", "disposition"]
                if cl in [5, 7, 8]
                else ["disposition"],
                "package_required": cl in [5, 7, 8],
                "actual_floor_count": None,
                "actual_occupancy": None,
            }

    for section in ["nodes", "register_only"]:
        for x in read(CHART)[section]:
            source_status = x.get("status", "")
            if "superseded" in source_status.lower():
                x["name"] = "Superseded identity (see historical source)"
                x["sources"] = [
                    {key: value for key, value in source.items() if key != "evidence"}
                    for source in x.get("sources", [])
                ]
            i = x["id"]
            target = ALIASES.get(i, i if i in records else "ORG:" + i)
            if target not in records:
                cl = 6
                reason = "Person, function, organization, role, equipment or scope record does not itself establish a distinct building. Shared workplace assignment is handled by the population bridge."
                if i in [
                    "kgm",
                    "demotte",
                    "cedar",
                    "harrison-vale",
                    "wolf-ridge",
                    "juniper",
                    "mesa-lantern",
                    "salt-rim",
                    "argent-ridge",
                    "qfc",
                    "balloon",
                    "NMI",
                ]:
                    cl = 5
                    reason = "External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address."
                if i in ["FORT-TEST-RIG", "FORT-ANALYTICAL", "BEDFORD-MODULE"]:
                    cl = 8
                    reason = "Forecast equipment asset is not evidence of September 2026 installation; no occupied architectural floor is established."
                extra(
                    target,
                    x["name"],
                    cl,
                    reason,
                    x.get("sources", []),
                    "external" if cl == 5 else "nonphysical" if cl == 6 else "proposed",
                )
            if "superseded" in source_status.lower():
                records[target]["status"] = source_status
                records[target]["reason"] = (
                    "Superseded identity retained by source ID and locator; never accepted as a current occupant or physical property."
                )
            bind(CHART, section, i, target)
    for section in ["facilities", "structures", "track_segments"]:
        for x in read(OPS)[section]:
            target = ALIASES.get(x["id"], "SH-IND-" + x["id"])
            assert target in records, target
            bind(OPS, section, x["id"], target)
            if section == "facilities":
                records[target]["operating_program"] = x
                records[target]["tenure"] = (
                    x.get("owner", "unknown")
                    + " (operating source owner label; no real title claim)"
                )
    for x in read("industrial/source/entities.json")["entities"]:
        i = x["entity_id"]
        target = "ORG:" + i
        extra(
            target,
            x["legal_name"],
            6,
            "Legal entity is not a distinct property; domicile and ownership do not establish employee working base.",
            [{"path": "industrial/source/entities.json", "locator": "entities/" + i}],
            "nonphysical",
        )
        bind("industrial/source/entities.json", "entities", i, target)
    for x in read(COMP)["components"]:
        i = x["id"]
        target = ALIASES.get(i, "SERVICE:" + i)
        extra(
            target,
            x["name"],
            8 if x["type"] == "facility" else 6,
            "Facility requirement without a separately accepted runtime placement; no extra property or installed capacity inferred."
            if x["type"] == "facility"
            else "Shared team or workload environment is not another property or headcount pool.",
            [{"path": COMP, "locator": "components/" + i}],
            "unresolved" if x["type"] == "facility" else "nonphysical",
        )
        bind(COMP, "components", i, target)
    for p in ["industrial/source/geography/network.geojson"] + [
        str(x.relative_to(ROOT)) for x in sorted((ROOT / "geospatial/geojson").glob("*.geojson"))
    ]:
        for n, x in enumerate(read(p)["features"]):
            pr = x["properties"]
            i = str(x.get("id", pr.get("feature_id", n)))
            obj = pr.get("object_id")
            target = obj if obj in records else ALIASES.get(i, ALIASES.get(i.removeprefix("IND-")))
            if target not in records:
                target = "GEOMETRY:" + p.split("/")[-1] + ":" + i
                extra(
                    target,
                    pr.get("canonical_name", pr.get("name", i)),
                    6,
                    "Reference geometry or derivative network layer; geometry alone creates no additional property. Original properties retained in cited layer.",
                    [{"path": p, "locator": "features/" + i}],
                    "reference",
                )
            bind(p, "features", i, target)
    # Source locks include controlling additions beyond the framework catalog cutoff.
    for p in [
        "docs/canon/CRADLE_CLOSEOUT_2026-09-06.md",
        "docs/canon/WILLOW_KLEIN_CLOSEOUT_2026-09-06.md",
        "docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md",
        "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md",
        "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md",
        "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
        "geospatial/sources/RUNTIME_INFRASTRUCTURE_GEO_ADDENDUM_2026-09-11.md",
    ]:
        source(p)
    return {
        "schema_version": "1.0.0",
        "source_main_sha": ACCEPTED_MAIN,
        "as_of": "2026-09-11",
        "boundary": "Coverage records are not distinct site counts. Aliases map repeated census appearances to the same record. Concept design does not establish occupied floors, tenure or dates.",
        "class_definitions": CLASSES,
        "input_sha256": inputs,
        "counts": {
            "catalog_objects": len(read(CAT)["objects"]),
            "service_components": len(read(COMP)["components"]),
            "runtime_sites": len(runtime_sites),
            "census_appearances": len(census),
            "coverage_records": len(records),
            "classes": dict(
                sorted(collections.Counter(x["class"] for x in records.values()).items())
            ),
        },
        "records": list(records.values()),
        "census": census,
    }


def main():
    d = build()
    (OUT / "COVERAGE_MATRIX.json").write_text(json.dumps(d, indent=2) + "\n")
    lines = [
        "# Facility coverage matrix",
        "",
        d["boundary"],
        "",
        "Source: current main "
        + d["source_main_sha"]
        + ". Build command: `python geospatial/facilities/coverage/build_coverage.py`.",
        "",
        f"The {d['counts']['catalog_objects']} geographic catalog objects remain authoritative geographic IDs. `ORG:`, `SERVICE:` and `GEOMETRY:` keys are census-disposition keys, not newly allocated site IDs. All newly designed building IDs must be allocated by the facility program.",
        "# Counts",
        "",
        json.dumps(d["counts"], sort_keys=True),
        "",
        "# Required design queue",
        "",
        "| ID | Name | Required output | Boundary |",
        "|---|---|---|---|",
    ]
    for x in d["records"]:
        if x["package_required"]:
            lines.append(
                f"| {x['id']} | {x['name']} | {', '.join(x['required_artifacts'])} | {x['reason']} |"
            )
    lines += [
        "",
        "# Complete census",
        "",
        "Machine-readable appearances, source hashes, aliases, statuses, tenure and unknown temporal/occupancy fields are in [COVERAGE_MATRIX.json](COVERAGE_MATRIX.json). A class 8 disposition is a placeholder requirement, not permission to drop its atlas record. Class 3 requires concept floors even when measured floor counts remain unknown. Class 4 exempts outdoor, rail and civil assets from architectural floors; the existing network and structure representations remain authoritative.",
        "",
        "Foundry, Atlas Meridian and Advisory lack dedicated accepted physical footprints (SH-SITE-0017–0019). Their organizational cards are class 6 and their physical-footprint question remains class 8; this avoids multiplying business functions into sites. J2 Education (SH-SITE-0014) remains a separate unresolved residential-campus record even where the Sacramento model includes day education. Alexandria retains its existing hosting identity with explicit runtime placement links. Accepted runtime decisions select Switch Reno and IDACORE Boise; provider contracts and assigned cages remain unestablished. Northern Nevada is an acquired synthetic parcel in preconstruction with a separately proposed building/floor concept. Wallaby is historical/killed under the September 6 Cradle closeout despite the earlier catalog OPEN label. Bedford is Fairmont, not the superseded Belle study area.",
    ]
    (OUT / "COVERAGE_MATRIX.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(d["counts"], indent=2))


if __name__ == "__main__":
    main()
