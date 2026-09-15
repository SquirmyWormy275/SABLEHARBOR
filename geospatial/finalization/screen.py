"""Reproduce compatibility screens from retained federal reference bytes."""

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import shape, Polygon
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/finalization"
SPECS = {
    "HQ-F": ("SH-SITE-0001", "Sacramento headquarters", 26910, 8, 15, "sacramento"),
    "FORT-NORTH": ("SH-SITE-0003", "The Fort / Willow", 26917, 10, 20, "hazelwood"),
    "BEDFORD-F": ("SH-SITE-0005", "Bedford / Cradle", 26917, 15, 20, "fairmont"),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(
        gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    )


def esri_polygon(rings):
    # ArcGIS rings: clockwise exteriors, counterclockwise holes. Symmetric
    # difference preserves nested islands and holes without relying on winding.
    result = Polygon()
    for ring in rings:
        poly = Polygon(ring)
        if not poly.is_valid:
            from shapely import make_valid

            poly = make_valid(poly)
        result = result.symmetric_difference(poly)
    return result


def equivalent(actual, expected):
    """Allow sub-micrometre floating-point platform noise, not evidence drift."""
    import math

    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and actual.keys() == expected.keys()
            and all(equivalent(actual[k], v) for k, v in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(equivalent(a, b) for a, b in zip(actual, expected))
        )
    if isinstance(expected, float):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-7)
        )
    return type(actual) is type(expected) and actual == expected


def screen():
    refs = BASE / "reference"
    manifest = read_json(refs / "MANIFEST.json")
    for r in manifest["records"]:
        for file_key, hash_key in [
            ("file", "sha256"),
            ("metadata_file", "metadata_sha256"),
        ]:
            if file_key in r and digest((refs / r[file_key]).read_bytes()) != r[hash_key]:
                raise ValueError("Reference checksum differs: " + r[file_key])
    records = []
    features = read_json(BASE / "SITE_SELECTIONS.geojson")["features"]
    for f in features:
        ident = f["properties"]["option_id"]
        oid, name, epsg, minimum, maximum, prefix = SPECS[ident]
        project = Transformer.from_crs(4326, epsg, always_xy=True).transform
        geo = shape(f["geometry"])
        g = transform(project, geo)
        acres = g.area / 4046.8564224
        if not geo.is_valid or not minimum <= acres <= maximum:
            raise ValueError(f"{ident}: invalid geometry/acreage {acres}")
        evidence = [r for r in manifest["records"] if r["option_id"] == ident]
        dem = next(r for r in evidence if r["kind"] == "elevation")
        with rasterio.open(refs / dem["file"]) as src:
            a = src.read(1)
            mask = geometry_mask(
                [f["geometry"]], transform=src.transform, invert=True, out_shape=a.shape
            )
            values = a[mask & np.isfinite(a) & (a > -1000) & (a < 9000)]
            if not len(values) or len(values) != int(mask.sum()):
                raise ValueError("No valid elevation cells")
            elev = dict(
                min_m=float(values.min()),
                max_m=float(values.max()),
                relief_m=float(np.ptp(values)),
                p10_p50_p90_m=np.percentile(values, [10, 50, 90]).tolist(),
                valid_cells=len(values),
                sampling="Exported 256 × 256 F32 context raster, polygon-center mask; terrain screen, not finished grades or a geotechnical survey.",
            )
        catalog = read_json(refs / f"{ident}-naip.json.gz")
        imagery_sources = []
        for item in catalog["features"]:
            attrs = item["attributes"]
            if attrs["Category"] == 1:
                imagery_sources.append(
                    dict(
                        name=attrs["Name"],
                        acquisition_date=datetime.fromtimestamp(
                            attrs["acquisition_date"] / 1000, timezone.utc
                        )
                        .date()
                        .isoformat(),
                        resolution_m=attrs["resolution_value"],
                        catalog_query_scope="Point at polygon vertex-mean; not a guarantee of every mosaic pixel acquisition.",
                    )
                )
        if not imagery_sources:
            raise ValueError("No dated imagery source")
        flood_doc = read_json(refs / f"{ident}-flood.json.gz")
        if flood_doc.get("error") or flood_doc.get("exceededTransferLimit"):
            raise ValueError("Incomplete FEMA response")
        flood_geometries = []
        floods = []
        for item in flood_doc["features"]:
            fg = esri_polygon(item["geometry"]["rings"])
            flood_geometries.append(fg)
            intersection = transform(project, fg.intersection(geo))
            attrs = item["attributes"]
            floods.append(
                dict(
                    zone=attrs["FLD_ZONE"],
                    subtype=attrs["ZONE_SUBTY"],
                    sfha=attrs["SFHA_TF"],
                    dfirm_id=attrs["DFIRM_ID"],
                    intersection_acres=intersection.area / 4046.8564224,
                )
            )
        if transform(project, geo.difference(unary_union(flood_geometries))).area > 1:
            raise ValueError("FEMA coverage does not cover selected footprint")
        reference_distances = []
        for path in sorted((ROOT / "geospatial/reference").glob(prefix + "_*.geojson")):
            if not any(k in path.stem for k in ["roads", "highways", "hydro", "rail"]):
                continue
            raw = path.read_bytes()
            context = unary_union(
                [
                    transform(project, shape(item["geometry"]))
                    for item in json.loads(raw)["features"]
                ]
            )
            if context.is_empty:
                continue
            reference_distances.append(
                dict(
                    path=str(path.relative_to(ROOT)),
                    sha256=digest(raw),
                    distance_m=g.distance(context),
                    intersects=bool(g.intersects(context)),
                    interpretation="Archived centerline context, not a cadastral or right-of-way survey. Imagery and current primary-source exclusions control discrepancies.",
                )
            )
        if not reference_distances or any(r["intersects"] for r in reference_distances):
            raise ValueError("Selected footprint crosses an archived context line")
        records.append(
            dict(
                option_id=ident,
                object_id=oid,
                name=name,
                epsg=epsg,
                area_acres=acres,
                geometry_sha256=digest(
                    json.dumps(f["geometry"], sort_keys=True, separators=(",", ":")).encode()
                ),
                elevation=elev,
                imagery_sources=imagery_sources,
                flood_intersections=floods,
                archived_reference_screen=reference_distances,
                selection="AUTHORED_FICTIONAL_PLANNING_FOOTPRINT",
                precision="DESIGN_COORDINATES_NOT_SURVEY",
                unavailable_certifications=[
                    "real cadastral interests and tenancy",
                    "approved zoning and access permits",
                    "geotechnical/foundation design",
                    "contamination cleanup certification",
                    "installed utility capacity",
                ],
                authority="docs/canon/GEOGRAPHIC_COMPLETION_2026-09-13.md",
            )
        )
    return dict(
        as_of="2026-09-13",
        records=records,
        limitations="2022 imagery supplemented with dated public planning/occupancy sources. Fictional sites do not prove real property availability. FEMA mapping is not assurance against flooding; DEM is terrain, not finished floor levels.",
    )


if __name__ == "__main__":
    result = screen()
    (BASE / "SITE_SCREEN.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                r["option_id"]: dict(
                    acres=r["area_acres"],
                    relief=r["elevation"]["relief_m"],
                    line_intersections=[
                        x["path"] for x in r["archived_reference_screen"] if x["intersects"]
                    ],
                )
                for r in result["records"]
            },
            indent=2,
        )
    )
