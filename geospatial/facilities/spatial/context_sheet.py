"""Render official regional context without placing the unsited campus."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from r01_drawing import Sheet, MUTED, INK


def render_context(root, context, identifier):
    region = context["regions"]["sacramento"]
    sheet = Sheet(
        "Sacramento regional context",
        "Official reference layers · conceptual campus remains geographically unplaced",
        identifier,
        "Regional context",
        revision="S01",
    )
    # Replace the concept-specific boilerplate with the precise reference-map boundary.
    sheet.parts = [
        p.replace(
            "Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.",
            "Real reference data; dates differ by layer. No site ownership, campus connection or current operating service is inferred.",
        )
        for p in sheet.parts
    ]
    _, _, w, h = region["extent_local_m"]
    scale = min(2090 / w, 1550 / h)
    ox, oy = 160 + (2090 - w * scale) / 2, 2040
    colors = {
        "street": "#b2b7b3",
        "rail": "#525c62",
        "water": "#a6c1ce",
        "path": "#5f8d75",
        "transit": "#b47d37",
        "terrain": "#887c6c",
    }

    def point(c):
        return ox + c[0] * scale, oy - c[1] * scale

    def draw(g, cat):
        typ = g["type"]
        c = g.get("coordinates")
        color = colors[cat]
        if typ == "GeometryCollection":
            for sub in g["geometries"]:
                draw(sub, cat)
        elif typ == "Point":
            x, y = point(c)
            sheet.circle(x, y, 4 if cat == "terrain" else 6, color, "none")
        elif typ in ("LineString", "Polygon"):
            lines = [c] if typ == "LineString" else c
            for line in lines:
                pts = [point(v) for v in line]
                sheet.path(
                    "M "
                    + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
                    + (" Z" if typ == "Polygon" else ""),
                    color if typ == "Polygon" else "none",
                    color,
                    2 if cat == "street" else 3,
                )
        elif typ.startswith("Multi"):
            for sub in c:
                draw({"type": typ[5:], "coordinates": sub}, cat)

    for cat in ("water", "street", "rail", "path", "terrain", "transit"):
        for f in region["features"]:
            if f["category"] == cat:
                draw(f["geometry"], cat)
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from r01_drawing import PAPER

    labels = []
    for name in [
        "Sacramento River",
        "American River",
        "Richards Blvd",
        "Bercut Dr",
        "Jibboom St",
        "Garden Hwy",
        "I St",
        "N 12th St",
    ]:
        features = [shape(f["geometry"]) for f in region["features"] if f["name"] == name]
        if not features:
            continue
        center = unary_union(features).centroid
        x, y = point([center.x, center.y])
        width = len(name) * 13 + 16
        x = min(max(ox + 12, x), ox + w * scale - width - 12)
        for _ in range(12):
            if not any(
                abs(y - yy) < 32 and x < xx + ww and x + width > xx for xx, yy, ww in labels
            ):
                break
            y -= 34
        sheet.rect(x - 5, y - 23, width, 30, PAPER, "none")
        sheet.text(x, y, name, 23, weight="bold")
        labels.append((x, y, width))
    samples = [f for f in region["features"] if f["category"] == "terrain"]
    for f in samples[::10]:
        x, y = point(f["geometry"]["coordinates"])
        if not ox + 60 < x < ox + w * scale - 70 or not oy - h * scale + 60 < y < oy - 40:
            continue
        value = f["source_properties"]["elevation_m"]
        sheet.rect(x + 8, y - 24, 100, 30, PAPER, "none")
        sheet.text(x + 12, y, f"{value:.1f} m", 22, fill=colors["terrain"])
    sheet.rect(ox, oy - h * scale, w * scale, h * scale, "none", MUTED, 2)
    sheet.north(2370, 520)
    for i, (cat, label) in enumerate(
        [
            ("street", "Street reference"),
            ("rail", "Rail reference"),
            ("water", "Water"),
            ("path", "Class 1 shared-use paths"),
            ("transit", "SacRT feed stop locations"),
            ("terrain", "USGS elevation samples"),
        ]
    ):
        y = 760 + i * 66
        sheet.rect(2390, y - 22, 26, 26, colors[cat], "none")
        sheet.text(2440, y, label, 24)
    sheet.paragraph(
        2390,
        1220,
        "UTM zone 10N / EPSG:26910. North up. Projected reference map, not a cadastral survey.",
        width=43,
        size=25,
    )
    sheet.paragraph(
        2390,
        1420,
        "SacRT feed: 9 Aug 2026–2 Jan 2027. Stops do not establish operating service on a particular day. Paths do not establish accessible campus connections.",
        width=43,
        size=25,
    )
    sheet.paragraph(
        2390,
        1650,
        "Terrain: 81 USGS DEM samples, not a survey or engineered contours. Roads and rail retain their individual source vintages.",
        width=43,
        size=25,
    )
    sheet.paragraph(
        2390,
        1850,
        "The approved 840 × 600 ft campus is a separate local model. It has no geographic transform, parcel fit or entrance connection.",
        width=43,
        size=25,
        weight="bold",
    )
    x, y = ox + 20, 2090
    sheet.line(x, y, x + 500 * scale, y, INK, 5)
    sheet.text(x, y - 15, "500 m", 24)
    return sheet.save(
        root / "geospatial/maps/spatial",
        identifier,
        {
            "id": identifier,
            "map_id": identifier,
            "logical_id": "SH-SITE-0001::enhanced-context",
            "kind": "enhanced-context",
            "site_id": "SH-SITE-0001",
            "title": "Sacramento regional context",
            "status": "REAL_REFERENCE_NOT_CAMPUS_SITING",
        },
    )
