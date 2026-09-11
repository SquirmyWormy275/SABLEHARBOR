"""Extend the existing map manifest; rc4 map entries and bytes remain unchanged."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def integrate():
    maps = ROOT / "geospatial/maps"
    path = maps / "MAP_MANIFEST.json"
    base = [
        r
        for r in json.loads(path.read_text())
        if r.get("builder") != "geospatial/facilities/render.py"
        and r.get("facility_integration") != "accepted_runtime_bridge"
    ]
    facility = json.loads((maps / "facilities/MANIFEST.json").read_text())
    context_hash = hashlib.sha256(
        (ROOT / "geospatial/master/sable_harbor_master_v0.1.gpkg").read_bytes()
    ).hexdigest()
    for r in facility["maps"]:
        base.append(
            {
                "map_id": r["id"],
                "title": r["title"],
                "version": facility["revision"],
                "effective_date": "2026-09-11",
                "world_state": "MODELLED_FACILITY_PROGRAM_NOT_OCCUPANCY",
                "canon_status": r["status"],
                "source_commit": facility["base_commit"],
                "source_geopackage_sha256": context_hash,
                "projection": "LOCAL_METRIC_CONCEPT_NO_GEOGRAPHIC_TRANSFORM",
                "build_timestamp": "2026-09-11T00:00:00+00:00",
                "builder": "geospatial/facilities/render.py",
                "review_status": "SEE_HASH_BOUND_FACILITY_QA",
                "source_scope": "GeoPackage is geographic context only. Facility source geometries remain illustrative local frames; no parcel geometry inserted.",
                "source_sha256": facility["source_sha256"],
                "site_id": r["site_id"],
                "building_id": r.get("building_id"),
                "floor_id": r.get("floor_id"),
                "files": {
                    ext: {
                        "path": str(Path(a["path"]).relative_to("geospatial/maps")),
                        "sha256": a["sha256"],
                    }
                    for ext, a in r["artifacts"].items()
                },
            }
        )
    bridge_path = ROOT / "geospatial/facilities/RUNTIME_BRIDGE.json"
    if bridge_path.is_file():
        bridge = json.loads(bridge_path.read_text())
        for r in bridge["maps"]:
            base.append(
                {
                    "map_id": r["id"],
                    "title": r["title"],
                    "version": "1.0.0",
                    "effective_date": "2026-09-11",
                    "world_state": "ACCEPTED_RUNTIME_DESIGN_NOT_OPERATION",
                    "canon_status": r["status"],
                    "source_commit": bridge["integration_base"],
                    "source_geopackage_sha256": context_hash,
                    "projection": "LOCAL_CONCEPT_FRAMES_NOT_SURVEYED_GEOGRAPHY",
                    "build_timestamp": "2026-09-11T00:00:00+00:00",
                    "builder": "enterprise/runtime/render.py",
                    "facility_integration": "accepted_runtime_bridge",
                    "review_status": "ACCEPTED_MAIN_RUNTIME_PUBLICATION_LINKED_UNCHANGED",
                    "source_sha256": bridge["source_sha256"],
                    "site_id": r["site_id"],
                    "building_id": r.get("building_id"),
                    "floor_id": r.get("floor_id"),
                    "files": {
                        ext: {"path": str(Path("../..") / a["path"]), "sha256": a["sha256"]}
                        for ext, a in r["artifacts"].items()
                    },
                }
            )
    assert len({r["map_id"] for r in base}) == len(base), "duplicate map ID"
    path.write_text(json.dumps(base, indent=2) + "\n")
    print(
        f"Integrated {len(facility['maps'])} R02 facility sheets and accepted runtime links; {len(base)} total map records"
    )


if __name__ == "__main__":
    integrate()
