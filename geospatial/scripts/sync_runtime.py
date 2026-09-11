#!/usr/bin/env python3
"""Synchronize runtime facts into the existing catalog; preserve unrelated identities."""

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from enterprise.runtime import model  # noqa: E402 — direct script entry point sets repository import root


def parcel(site):
    from pyproj import Geod, Transformer
    from shapely.geometry import Polygon, mapping

    lon, lat = site["planning_lon_lat"]
    forward = Transformer.from_crs(4326, 32611, always_xy=True)
    reverse = Transformer.from_crs(32611, 4326, always_xy=True)
    x, y = forward.transform(lon, lat)
    side = (site["parcel_acres_planning"] * 4046.8564224) ** 0.5
    # Correct projected scale using independent ellipsoidal area, without cadastral data.
    for _ in range(3):
        corners = [
            reverse.transform(x + dx * side / 2, y + dy * side / 2)
            for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]
        ]
        poly = Polygon(corners)
        area = abs(Geod(ellps="WGS84").geometry_area_perimeter(poly)[0]) / 4046.8564224
        side *= (site["parcel_acres_planning"] / area) ** 0.5
    if abs(area - 7.5) > 0.001:
        raise ValueError("Synthetic parcel area discrepancy")
    return mapping(poly), area


def synchronize(catalog, runtime):
    model.validate(runtime, ROOT)
    result = copy.deepcopy(catalog)
    source_id, decision_id = "SRC-RUNTIME-20260911", "GEO-RUNTIME-20260911"
    path = model.FILES["sites"]
    result["sources"] = [s for s in result["sources"] if s["source_id"] != source_id]
    result["sources"].append(
        dict(
            source_id=source_id,
            title="Runtime estate September 2026",
            publisher_or_author="Sable Harbor synthetic archive",
            source_type="STRUCTURED_OWNER_DECISION",
            publication_date="2026-09-11",
            accessed_date="2026-09-11",
            url_or_repo_path=path,
            repository_commit=None,
            file_sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
            license="Owner-authorized synthetic project material",
            citation=path,
            coverage="Reno/Boise selected relationships and synthetic owned parcel",
            source_quality="OWNER_AUTHORIZED_PENDING_MERGE",
            notes="No tenancy, real property title, or operating effectiveness asserted.",
        )
    )
    result["decisions"] = [d for d in result["decisions"] if d["decision_id"] != decision_id]
    result["decisions"].append(
        dict(
            decision_id=decision_id,
            decision_date="2026-09-11",
            decision_title="Runtime selection and synthetic parcel integration",
            decision_type="RUNTIME_SUCCESSOR",
            affected_object_ids=[s["geospatial_site_id"] for s in runtime["sites"]["sites"]],
            decision_status="OWNER_AUTHORIZED_PENDING_MERGE",
            deciding_authority="Owner PR119 mandate",
            source_conversation="Repository handover",
            source_document=path,
            rationale="Selected geography is distinct from occupancy and construction.",
            alternatives_considered="Preserve existing Alexandria hosting concept ID.",
            supersedes_decision_id=None,
            notes="Source-prepared September 11; effective land event September 4.",
        )
    )
    result["objects"] = [o for o in result["objects"] if o.get("source_id") != source_id]
    result["relationships"] = [
        r for r in result["relationships"] if r.get("source_id") != source_id
    ]
    features = []
    for site in model.world_state(runtime):
        existing = next(
            (o for o in result["objects"] if o["object_id"] == site["geospatial_site_id"]), None
        )
        if existing:
            raise ValueError(
                f"Runtime crosswalk collides with existing object {existing['object_id']}"
            )
        result["objects"].append(
            dict(
                object_id=site["geospatial_site_id"],
                canonical_name=site["name"],
                object_type="COMPUTE_INFRASTRUCTURE",
                entity_id="SH-ENT-001",
                place=site["geography"],
                granularity="PLANNING_PIN" if "planning_lon_lat" in site else "REGIONAL_CONSTRAINT",
                census_status="REGISTERED",
                canon_status="PROPOSED",
                fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
                source_id=source_id,
                source_path=path,
                source_commit=None,
                source_locator=site["id"],
                exact_source_wording=site["status"],
                relevant_date=site.get("planning_purchase_date", "2026-09-11"),
                date_precision="DAY",
                conflict_id="",
                next_action="Procurement/design acceptance and evidence gates",
                notes=f"{site['status']}; provider facility reference is not Sable Harbor occupancy.",
                decision_id=decision_id,
            )
        )
        result["relationships"].append(
            dict(
                relationship_id="REL-" + site["id"],
                subject_id="SH-SITE-0016",
                predicate="PLANNED_HOSTING_AT"
                if site["id"] != "RUNTIME-BOISE-DR"
                else "PLANNED_RECOVERY_AT",
                object_id=site["geospatial_site_id"],
                valid_from="2026-09-11",
                valid_to=None,
                date_text="2026-09-11",
                canon_status="PROPOSED",
                source_id=source_id,
                decision_id=decision_id,
                notes="No installed placement; owned migration requires accepted commissioning and recovery.",
            )
        )
        if "planning_lon_lat" not in site:
            continue  # Precise provider coordinates have not been independently verified.
        geometry, acres = parcel(site)
        properties = dict(
            feature_id="RT-PARCEL-001",
            object_id=site["geospatial_site_id"],
            canonical_name=site["name"] + " — acquired / preconstruction",
            fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
            real_world_relation="SYNTHETIC_PLANNING_ENVELOPE",
            canon_status="PROPOSED",
            geometry_status="SYNTHETIC_UNSURVEYED",
            location_method="ENGINEERED_FROM_CONSTRAINTS",
            precision_class="PLANNING_PIN_WITH_SYNTHETIC_ENVELOPE",
            horizontal_accuracy_m=None,
            public_precision="UNSURVEYED",
            source_id=source_id,
            decision_id=decision_id,
            valid_from="2026-09-04",
            valid_to=None,
            recorded_at="2026-09-11T00:00:00Z",
            source_effective_date="2026-09-04",
            world_state_date="2026-09-11",
            owner_entity="SH-ENT-001",
            rights_type="SYNTHETIC_ACQUISITION_NOT_REAL_TITLE",
            geometry_area_acres=acres,
            engineering_status="LAND_ACQUIRED_PRECONSTRUCTION",
            commissioned_it_kw=0,
            shell_complete=False,
            construction_method="EPSG:32611 square centered on owner anchor, scaled to WGS84 ellipsoidal 7.5 acres; no cadastral tracing",
            notes="0% vertical construction; 0 kW commissioned. No real APN. Forecast completion never creates history.",
        )
        features.append(
            dict(type="Feature", id="RT-PARCEL-001", geometry=geometry, properties=properties)
        )
    result["geometry_layers"]["runtime_parcel"] = "runtime_parcel"
    return result, dict(type="FeatureCollection", features=features)


def main():
    path = ROOT / "geospatial/sources/catalog.json"
    catalog, geo = synchronize(json.loads(path.read_text()), model.load())
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "geospatial/geojson/runtime_parcel.geojson").write_text(
        json.dumps(geo, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
