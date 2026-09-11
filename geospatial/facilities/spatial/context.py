"""Read-only, source-pinned geographic context; never site the conceptual campus."""

from __future__ import annotations

import argparse
import csv
import math
import hashlib
import json
from pathlib import Path
import sqlite3

from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import transform

BASE = "geospatial/facilities/spatial"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_region(root: Path, region: dict, sources: list[dict]) -> dict:
    projector = Transformer.from_crs("EPSG:4326", region["crs"], always_xy=True)
    west, south, east, north = region["extent_wgs84"]
    geographic_window = box(west, south, east, north)
    projected_window = transform(projector.transform, geographic_window)
    x0, y0, x1, y1 = projected_window.bounds
    features = []
    for source in sources:
        for feature in json.loads((root / source["path"]).read_text())["features"]:
            geometry = shape(feature["geometry"])
            if not geometry.is_valid:
                raise ValueError(f"invalid source geometry: {source['id']}/{feature.get('id')}")
            clipped = geometry.intersection(geographic_window)
            if clipped.is_empty:
                continue
            projected = transform(projector.transform, clipped)
            local = transform(lambda x, y, z=None: (x - x0, y - y0), projected)
            props = feature.get("properties", {})
            features.append(
                {
                    "id": str(
                        feature.get("id", props.get("permanent_identifier", props.get("objectid")))
                    ),
                    "category": source["category"],
                    "name": props.get("name")
                    or props.get("gnis_name")
                    or props.get("railowner")
                    or source["category"].title(),
                    "geometry": mapping(local),
                    "source_id": source["id"],
                    "source_path": source["path"],
                    "source_properties": props,
                    "fictionality": "REAL_REFERENCE",
                    "campus_connection": None,
                }
            )
    return {
        **region,
        "origin_projected_m": [x0, y0],
        "extent_local_m": [0, 0, x1 - x0, y1 - y0],
        "coordinate_units": "metres",
        "axis_direction": "x east, y north; renderer inverts y for screen",
        "features": features,
        "campus_geometry": None,
    }


def navigation_scope(graph: dict, maps: dict) -> dict:
    """Hash consumed navigation semantics, excluding downstream spatial derivatives."""
    coverage = {row["coverage_id"]: row for row in graph["coverage"]}
    nodes = []
    referenced = set()
    for node in graph["nodes"]:
        if node.get("kind") != "site":
            continue
        sid = node["id"]
        record = coverage.get(sid, {})
        context_ids = record.get("context_map_ids", [])
        referenced.update(context_ids)
        nodes.append(
            {
                "id": sid,
                "name": node.get("name", node.get("title", sid)),
                "status": record.get("status", "SEE_ACCEPTED_RUNTIME_SOURCE"),
                "context_map_ids": context_ids,
            }
        )
    entries = []
    for mid in sorted(referenced):
        row = maps[mid]
        entries.append(
            {
                "map_id": mid,
                "title": row["title"],
                "layers": row.get("layers", []),
                "files": {
                    fmt: {"path": v["path"], "sha256": v["sha256"]}
                    for fmt, v in row["files"].items()
                },
            }
        )
    payload = {"site_nodes": nodes, "referenced_context_maps": entries}
    return {
        "paths": [
            "geospatial/maps/facilities/ATLAS_LINKS.json",
            "geospatial/maps/MAP_MANIFEST.json",
        ],
        "sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "scope": "Only consumed site IDs/names/status/context-map IDs and referenced context map titles/layers/files. Unrelated graph edges, generated spatial map records and full-file hashes are excluded to avoid a dependency cycle.",
        "payload": payload,
    }


def metric_coordinates(value):
    """Serialize derived projected metres to 1 mm, not machine-dependent sub-nanometres.

    This precision controls reproducibility; it does not assert survey accuracy.
    Original geographic snapshots and source properties are never rounded here.
    """
    if isinstance(value, (tuple, list)):
        return [metric_coordinates(v) for v in value]
    if isinstance(value, (float, int)):
        return round(value, 3)
    return value


def metric_geometry(geometry):
    if "coordinates" in geometry:
        geometry["coordinates"] = metric_coordinates(geometry["coordinates"])
    for child in geometry.get("geometries", []):
        metric_geometry(child)
    return geometry


def build_context(root: Path) -> dict:
    root = root.resolve()
    config_path = root / BASE / "CONTEXT_SOURCES.json"
    config = json.loads(config_path.read_text())
    source_hashes = {str(config_path.relative_to(root)): sha(config_path)}
    for source in (
        [config["reference_manifest"]] + config["sources"] + config.get("supplemental_sources", [])
    ):
        p = root / source["path"]
        if sha(p) != source["sha256"]:
            raise ValueError(f"stale context source: {source['path']}")
        source_hashes[source["path"]] = source["sha256"]
    for name, expected in config.get("supporting_snapshot_sha256", {}).items():
        if sha(root / name) != expected:
            raise ValueError(f"stale supporting snapshot: {name}")
        source_hashes[name] = expected
    # Verify the existing accepted master is available without writing or deriving property positions.
    gpkg = root / config["gpkg_readonly"]
    with sqlite3.connect(gpkg.as_uri() + "?mode=ro", uri=True) as connection:
        available_layers = {
            row[0] for row in connection.execute("select table_name from gpkg_contents")
        }
    for source in config["sources"]:
        if source["gpkg_layer"] not in available_layers:
            raise ValueError(f"missing master reference layer: {source['gpkg_layer']}")
    regions = {}
    for key, region in config["regions"].items():
        sources = [s for s in config["sources"] if s["region"] == key]
        regions[key] = project_region(root, region, sources)
        regions[key]["sources"] = sources
        regions[key]["layer_dispositions"] = {
            **{
                category: "SUPPORTED_COMMITTED_REFERENCE"
                for category in sorted({s["category"] for s in sources})
            },
            **{
                k: {"status": "UNSUPPORTED_NO_GEOMETRY", "reason": v}
                for k, v in config["unsupported_layers"].items()
            },
        }
    for source in config.get("supplemental_sources", []):
        path = root / source["path"]
        features = []
        if source["category"] == "transit":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    features.append(
                        {
                            "id": "SACRT-STOP-" + row["stop_id"],
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [float(row["stop_lon"]), float(row["stop_lat"])],
                            },
                            "properties": {**row, "name": row["stop_name"]},
                        }
                    )
        elif source["category"] == "terrain":
            for index, row in enumerate(json.loads(path.read_text())["samples"]):
                value = float(row["value"])
                if not math.isfinite(value):
                    raise ValueError("nonfinite terrain sample")
                features.append(
                    {
                        "id": f"USGS-DEM-SAMPLE-{index:03}",
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [row["location"]["x"], row["location"]["y"]],
                        },
                        "properties": {
                            "name": f"{value:.1f} m DEM sample",
                            "elevation_m": value,
                            "source_raster_id": row.get("rasterId"),
                            "source_resolution": row.get("resolution"),
                        },
                    }
                )
        elif source["category"] == "path":
            response = json.loads(path.read_text())
            if response.get("exceededTransferLimit"):
                raise ValueError("incomplete SACOG path snapshot")
            for row in response["features"]:
                props = row["attributes"]
                if str(props["BIKE_CLASS"]) != "1":
                    continue
                features.append(
                    {
                        "id": "SACOG-PATH-" + str(props["OBJECTID"]),
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiLineString",
                            "coordinates": row["geometry"]["paths"],
                        },
                        "properties": {
                            **props,
                            "name": props.get("Name")
                            or props.get("FULLSTREET")
                            or "Shared-use path",
                            "pedestrian_use": "Class1 multi-use path; access conditions unverified",
                        },
                    }
                )
        projector = Transformer.from_crs("EPSG:4326", regions["sacramento"]["crs"], always_xy=True)
        x0, y0 = regions["sacramento"]["origin_projected_m"]
        window = box(*regions["sacramento"]["extent_wgs84"])
        for feature in features:
            geometry = shape(feature["geometry"]).intersection(window)
            if geometry.is_empty:
                continue
            local = transform(
                lambda x, y, z=None: (x - x0, y - y0), transform(projector.transform, geometry)
            )
            regions["sacramento"]["features"].append(
                {
                    "id": feature["id"],
                    "category": source["category"],
                    "name": feature["properties"]["name"],
                    "geometry": mapping(local),
                    "source_id": source["id"],
                    "source_path": source["path"],
                    "source_properties": feature["properties"],
                    "fictionality": "REAL_REFERENCE",
                    "campus_connection": None,
                }
            )
        regions["sacramento"]["sources"].append(source)
        regions["sacramento"]["layer_dispositions"][source["category"]] = (
            "SUPPORTED_DATED_OFFICIAL_SNAPSHOT"
        )
    imagery_manifest = root / "geospatial/sources/site_reference/manifest.json"
    image_record = next(
        r for r in json.loads(imagery_manifest.read_text()) if r["name"] == "sacramento"
    )
    source_hashes[str(imagery_manifest.relative_to(root))] = sha(imagery_manifest)
    for filename, digest_key in [
        ("sacramento.png", "raster_sha256"),
        ("sacramento_export.json", "metadata_sha256"),
        ("sacramento_catalog.json", "catalog_sha256"),
    ]:
        path = root / "geospatial/sources/site_reference" / filename
        if sha(path) != image_record[digest_key]:
            raise ValueError(f"stale imagery snapshot: {filename}")
        source_hashes[str(path.relative_to(root))] = sha(path)
    regions["sacramento"]["imagery"] = {
        **image_record,
        "path": "geospatial/" + image_record["raster_file"],
        "role": "OPTIONAL_HISTORICAL_REFERENCE_ONLY_NOT_TERRAIN",
        "effective_date": None,
        "occupancy_evidence": False,
    }
    graph_path = root / "geospatial/maps/facilities/ATLAS_LINKS.json"
    graph = json.loads(graph_path.read_text())
    coverage = {r["coverage_id"]: r for r in graph["coverage"]}
    map_path = root / "geospatial/maps/MAP_MANIFEST.json"
    maps = {r["map_id"]: r for r in json.loads(map_path.read_text())}
    navigation = navigation_scope(graph, maps)
    sites = []
    for node in graph["nodes"]:
        if node.get("kind") != "site":
            continue
        sid = node["id"]
        record = coverage.get(sid, {})
        context_ids = record.get("context_map_ids", [])
        links = []
        for mid in context_ids:
            entry = maps[mid]
            links.append(
                {
                    "map_id": mid,
                    "title": entry["title"],
                    "layers": entry.get("layers", []),
                    "files": {
                        fmt: {"path": "geospatial/maps/" + v["path"], "sha256": v["sha256"]}
                        for fmt, v in entry["files"].items()
                    },
                }
            )
        region = (
            "sacramento"
            if sid == "SH-SITE-0001"
            else "hazelwood"
            if sid == "SH-SITE-0003"
            else "fairmont"
            if sid == "SH-SITE-0005"
            else "wamsutter"
            if sid == "SH-IND-FAC-WAM-INT"
            else None
        )
        sites.append(
            {
                "site_id": sid,
                "name": node.get("name", node.get("title", sid)),
                "region_key": region,
                "status": record.get("status", "SEE_ACCEPTED_RUNTIME_SOURCE"),
                "context_links": links,
                "reference_layers": [s for s in config["sources"] if s["region"] == region],
                "disposition": "EXISTING_CONTEXT_LINKED"
                if links
                else "REGIONAL_ANCHOR_OR_CONTEXT_NOT_ESTABLISHED_HERE",
                "limitations": "Reference layers do not establish property rights, precise building position, transport access, operating occupancy or campus connections. Runtime regional/provider evidence remains in its accepted source; no guessed street connections.",
                "unsupported_layers": config["unsupported_layers"],
            }
        )
    for region in regions.values():
        region["origin_projected_m"] = metric_coordinates(region["origin_projected_m"])
        region["extent_local_m"] = metric_coordinates(region["extent_local_m"])
        region["derived_metric_serialization_m"] = 0.001
        region["precision_caveat"] = (
            "Millimetre serialization removes platform floating-point noise; source accuracy remains unestablished and is not millimetre survey precision."
        )
        for feature in region["features"]:
            metric_geometry(feature["geometry"])
    return {
        "revision": config["revision"],
        "boundary": config["boundary"],
        "source_sha256": source_hashes,
        "navigation_scope": navigation,
        "master_layers_checked_readonly": sorted(available_layers),
        "regions": regions,
        "sites": sites,
        "conceptual_campus": {
            "site_id": "SH-SITE-0001",
            "georeferenced": False,
            "transform_to_real_world": None,
            "frame_ft": [840, 600],
            "source": "geospatial/facilities/source/campus.json",
            "separation": "Draw as a separate diagram only. Neither translation, rotation nor scale implies a real parcel placement.",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    print(json.dumps(build_context(args.root), indent=2, allow_nan=False))
