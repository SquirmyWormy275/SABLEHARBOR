"""Dimensioned site alternatives screened only against archived reference linework."""

import json
import math
from pyproj import Transformer
from shapely.geometry import box, mapping, shape, LineString
from shapely.ops import transform, unary_union, nearest_points
from geospatial.chronology.build import ROOT, sha

SPECS = [
    dict(
        object_id="SH-SITE-0001",
        name="Sacramento headquarters",
        prefix="sacramento",
        study="SH-GEO-0001",
        epsg=26910,
        size=[256.032, 182.88],
        min_acres=8,
        max_acres=15,
        authority="geospatial/sources/MASTER_EXECUTION_MANDATE.md",
        note="Preserves the approved R01-derived 840 by 600 ft local campus envelope. This placement alternative does not rotate or redraw approved building references.",
    ),
    dict(
        object_id="SH-SITE-0003",
        name="The Fort / Willow",
        prefix="hazelwood",
        study="SH-GEO-0002",
        epsg=26917,
        size=[300, 220],
        min_acres=10,
        max_acres=20,
        authority="docs/canon/WILLOW_KLEIN_CLOSEOUT_2026-09-06.md",
        note="Separate premises from the Klein shop. The Hazelwood study window supplies regional context only; this is not a reuse of the historical shop's property or a claim on Hazelwood Green tenants.",
    ),
    dict(
        object_id="SH-SITE-0005",
        name="Bedford / Cradle",
        prefix="fairmont",
        study="SH-GEO-BEDFORD-001",
        epsg=26917,
        size=[330, 220],
        min_acres=15,
        max_acres=20,
        authority="docs/canon/CRADLE_CLOSEOUT_2026-09-06.md",
        note="Fairmont-area development/upgrading center, separate from Demotte. Brownfield condition is a fictional design requirement; no contamination clearance, river berth or rail connection is inferred.",
    ),
]


def build():
    studies = {
        r["id"]: r
        for r in json.loads((ROOT / "geospatial/geojson/locked_search_areas.geojson").read_text())[
            "features"
        ]
    }
    sites, access, reports = [], [], []
    for spec in SPECS:
        forward = Transformer.from_crs(4326, spec["epsg"], always_xy=True).transform
        reverse = Transformer.from_crs(spec["epsg"], 4326, always_xy=True).transform
        study = transform(forward, shape(studies[spec["study"]]["geometry"]))
        refs, hashes = {}, {}
        for path in sorted((ROOT / "geospatial/reference").glob(spec["prefix"] + "_*.geojson")):
            if not any(k in path.stem for k in ["roads", "highways", "hydro", "rail"]):
                continue
            raw = path.read_bytes()
            hashes[str(path.relative_to(ROOT))] = sha(raw)
            refs[path.stem] = unary_union(
                [transform(forward, shape(r["geometry"])) for r in json.loads(raw)["features"]]
            )
        roads = unary_union([g for k, g in refs.items() if "roads" in k and not g.is_empty])
        obstacles = unary_union(
            [g.buffer(12 if "roads" in k else 25) for k, g in refs.items() if not g.is_empty]
        )
        w, h = spec["size"]
        minx, miny, maxx, maxy = study.bounds
        # A fixed projected grid and a published deterministic ranking make every
        # considered alternative reproducible. No cadastral suitability score.
        candidates = []
        step = 40 if spec["prefix"] != "fairmont" else 160
        tested = 0
        for x in range(math.ceil(minx / step) * step, int(maxx), step):
            for y in range(math.ceil(miny / step) * step, int(maxy), step):
                geom = box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                tested += 1
                if not study.covers(geom) or obstacles.intersects(geom):
                    continue
                a, b = nearest_points(geom.boundary, roads)
                distance = a.distance(b)
                if not 12 <= distance <= 600:
                    continue
                candidates.append((round(distance, 6), x, y, geom, LineString([a, b])))
        candidates.sort(key=lambda r: r[:3])
        chosen = []
        for candidate in candidates:
            if any(candidate[3].intersects(r[3].buffer(30)) for r in chosen):
                continue
            chosen.append(candidate)
            if len(chosen) == 3:
                break
        if len(chosen) != 3:
            raise ValueError("Insufficient screened alternatives: " + spec["name"])
        reports.append(
            dict(
                **spec,
                grid_centers_tested=tested,
                reference_clear_candidates=len(candidates),
                alternatives=3,
                reference_sha256=hashes,
                authority_sha256=sha((ROOT / spec["authority"]).read_bytes()),
                study_sha256=sha(json.dumps(studies[spec["study"]], sort_keys=True).encode()),
            )
        )
        for i, (distance, x, y, geom, connector) in enumerate(chosen, 1):
            ident = spec["object_id"] + f"-OPTION-{i}"
            props = dict(
                option_id=ident,
                object_id=spec["object_id"],
                name=spec["name"],
                status="UNSELECTED_ENGINEERING_ALTERNATIVE",
                fictionality="SYNTHETIC_DESIGN_IN_REAL_REFERENCE_CONTEXT",
                precision="DIMENSIONED_DESIGN_NOT_SURVEY",
                area_acres=geom.area / 4046.8564224,
                width_m=w,
                depth_m=h,
                study_id=spec["study"],
                projected_epsg=spec["epsg"],
                reference_access_gap_m=distance,
                occupancy_start=None,
                occupancy_end=None,
                owner_entity=None,
                valid_from=None,
                valid_to=None,
                source_note=spec["note"],
                unavailable_screens=[
                    "cadastral interests",
                    "building occupancy",
                    "zoning",
                    "floodplain/waterbody polygons",
                    "terrain/geotechnical",
                    "contamination",
                    "utilities",
                    "public-road access permission",
                ],
                ranking="Shortest straight-line gap to archived ordinary road linework; not a suitability ranking.",
            )
            sites.append(
                dict(
                    type="Feature",
                    id=ident,
                    geometry=mapping(transform(reverse, geom)),
                    properties=props,
                )
            )
            access.append(
                dict(
                    type="Feature",
                    id=ident + "-ACCESS",
                    geometry=mapping(transform(reverse, connector)),
                    properties=dict(
                        option_id=ident,
                        object_id=spec["object_id"],
                        status="UNAPPROVED_STRAIGHT_LINE_ACCESS_TEST",
                        length_m=distance,
                        access_rights=None,
                        note="Geometric gap only. Not an engineered drive, route clearance, public access or easement.",
                    ),
                )
            )
    return (
        dict(type="FeatureCollection", features=sites),
        dict(type="FeatureCollection", features=access),
        reports,
    )


def write(output):
    output.mkdir(parents=True, exist_ok=True)
    sites, access, reports = build()
    for name, value in [
        ("SITE_OPTIONS.geojson", sites),
        ("ACCESS_TESTS.geojson", access),
        ("SITE_SCREEN.json", reports),
    ]:
        (output / name).write_text(json.dumps(value, indent=2) + "\n")
    return sites, access, reports


if __name__ == "__main__":
    write(ROOT / "geospatial/completion")
