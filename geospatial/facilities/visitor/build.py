"""One visitor-map draft using the accepted campus source and R01 sheet primitives."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(BASE.parent))
from r01_drawing import BLUE, FILLS, FT, GOLD, INK, MUTED, PAPER, SAGE, Sheet  # noqa: E402 — local renderer path configured above


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    source = json.loads((BASE / "SOURCE.json").read_text())
    model = json.loads((ROOT / source["geometry_source"]).read_text())
    assert model["site_id"] == source["site_id"]
    for path, digest in model["approved_reference_sha256"].items():
        assert sha(ROOT / path) == digest, f"Approved reference altered: {path}"
    assert sha(ROOT / source["reference"]) == source["reference_sha256"]
    assert {b["r01_letter"] for b in model["buildings"]} == set(source["building_labels"])
    sheet = Sheet(
        source["title"], source["subtitle"], source["site_id"], "VISITOR GUIDE", revision="V01"
    )
    # Draft purpose replaces the generic area/seat footer, retaining R01 geometry and type.
    sheet.parts = [
        p.replace(
            "Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.",
            "Fictional campus study; no actual parcel selected. Visitor access and parking arrangements remain provisional.",
        )
        for p in sheet.parts
    ]
    k = min(2284 / model["envelope_ft"][0], 1632 / model["envelope_ft"][1])
    x0, y0 = 120, 427

    def xy(x, y):
        return x0 + x * k, y0 + (600 - y) * k

    def rect(r, fill, stroke="none", width=1):
        x, y, w, h = r
        sheet.rect(*xy(x, y + h), w * k, h * k, fill, stroke, width)

    rect([0, 0, 840, 600], "#ebeee6", INK, 3)
    rect([30, 30, 780, 540], "#cbcdc8")
    rect([56, 56, 728, 488], "#ebeee6")
    drawing = model["site_drawing"]
    for r in drawing["roads_ft"]:
        rect(r, "#cbcdc8")
    for r in drawing["walks_ft"]:
        rect(r, "#dddcd5")
    rect(drawing["service_apron_ft"], "#dddcd5", MUTED)
    for lot in drawing["parking_blocks"]:
        r = lot["rect_ft"]
        rect(r, "#dfe2da", "#a7b5ae")
        x, y, w, h = r
        sheet.text(
            *xy(x + w / 2, y + h / 2 - 4), "P", 26, fill=MUTED, weight="bold", anchor="middle"
        )
        if lot["vertical"]:
            for offset in [18, w - 18]:
                sheet.line(*xy(x + offset, y), *xy(x + offset, y + h), "#bac2b8", 1)
        else:
            for offset in [18, h - 18]:
                sheet.line(*xy(x, y + offset), *xy(x + w, y + offset), "#bac2b8", 1)
    for court in drawing["courts"]:
        r = court["rect_ft"]
        rect(r, "#e1e8da", "#a7b5ae")
        x, y, w, h = r
        name = "BICYCLES" if court["name"] == "BIKES / ACCESS" else court["name"]
        sheet.text(
            *xy(x + w / 2, y + h / 2 - 2), name, 22, fill=MUTED, weight="bold", anchor="middle"
        )
    for x, y in drawing["trees_ft"]:
        sheet.circle(*xy(x, y), 7.5 * k, "#d5e1d0", "#aec0ad", 1.5)
    colors = {"blue": BLUE, "sand": GOLD, "sage": SAGE}
    entries = []
    for b in model["buildings"]:
        letter = b["r01_letter"]
        spec = source["building_labels"][letter]
        x, y, w, h = b["rect_ft"]
        color = colors[spec["color"]]
        rect(b["rect_ft"], FILLS[spec["color"]], color, 5)
        sheet.text(*xy(x + 17, y + h - 27), letter, 52, weight="bold", fill=color)
        sheet.text(*xy(x + w / 2, y + h / 2 - 5), spec["name"], 36, weight="bold", anchor="middle")
        sheet.text(
            *xy(x + w / 2, y + h / 2 - 22), spec["map_note"], 25, fill=MUTED, anchor="middle"
        )
        entry = model["access"][spec["entry_key"]][-1]
        fx, fy = [v / FT for v in entry]
        assert abs(fy - y) < 0.001 and x <= fx <= x + w, f"Entry not on south facade: {letter}"
        ex, ey = xy(fx, fy)

        entries.append(
            {"building_id": b["id"], "source_access_key": spec["entry_key"], "entry_ft": [fx, fy]}
        )
    route = model["access"][source["highlight_route"]]
    points = [xy(x / FT, y / FT) for x, y in route]
    path = "M" + " L".join(f"{x:g},{y:g}" for x, y in points)
    sheet.path(path, stroke=PAPER, width=18)
    sheet.path(path, stroke=GOLD, width=10)
    for entry in entries:
        ex, ey = xy(*entry["entry_ft"])
        letter = entry["building_id"].rsplit("-", 1)[1]
        color = colors[source["building_labels"][letter]["color"]]
        sheet.path(f"M{ex},{ey + 5} l-13,23 h26 Z", color, "none")
    drop = next(z["rect_ft"] for z in model["site_zones"] if z["name"] == "Drop-off lane")
    sheet.text(
        *xy(drop[0] + drop[2] / 2, drop[1] + drop[3] / 2 - 3),
        "DROP-OFF",
        22,
        fill=MUTED,
        anchor="middle",
    )
    ax, ay = points[0]
    sheet.circle(ax, ay - 12, 15, GOLD, PAPER, 3)
    sheet.text(ax + 38, ay - 5, "CAMPUS ARRIVAL", 27, weight="bold")
    sheet.north(2328, 665)
    sheet.scale(156, 2090, k, 100)
    sheet.text(1190, 2110, "840 × 600 ft fictional study envelope", 24, fill=MUTED, anchor="middle")
    sheet.line(2485, 397, 3133, 397, MUTED, 1.5)
    sheet.text(2485, 451, "FIND YOUR BUILDING", 34, weight="bold")
    y = 534
    for letter, spec in source["building_labels"].items():
        sheet.text(2485, y, letter, 45, fill=colors[spec["color"]], weight="bold")
        sheet.text(2559, y, spec["name"], 32, weight="bold")
        sheet.paragraph(2559, y + 48, spec["description"], width=33, size=28, leading=42)
        y += 188
    sheet.line(2485, 1285, 3133, 1285, MUTED, 1.5)
    sheet.text(2485, 1343, "ON ARRIVAL", 34, weight="bold")
    sheet.paragraph(2485, 1400, source["arrival_note"], width=39, size=30, leading=45, fill=INK)
    sheet.line(2485, 1595, 3133, 1595, MUTED, 1.5)
    sheet.text(2485, 1654, "PARKING AND ACCESS", 32, weight="bold")
    sheet.paragraph(2485, 1710, source["parking_note"], width=40, size=29, leading=43)
    sheet.line(2485, 1900, 3133, 1900, MUTED, 1.5)
    sheet.line(2485, 1950, 2540, 1950, GOLD, 9)
    sheet.text(2565, 1960, "Arrival path to A", 26)
    sheet.path("M2509,2010 l-13,23 h26 Z", INK, "none")
    sheet.text(2565, 2032, "Building entrance", 26)
    sheet.text(2510, 2100, "P", 28, fill=MUTED, weight="bold", anchor="middle")
    sheet.text(2565, 2100, "Parking", 26)
    result = sheet.save(
        BASE / "artifacts",
        "visitor-map-v01",
        {
            "title": source["title"],
            "site_id": source["site_id"],
            "status": source["status"],
            "map_id": None,
            "production_allocation": "PENDING_VISUAL_ACCEPTANCE",
        },
    )
    result["revision"] = "V01"
    result["sources"] = {
        str(p.relative_to(ROOT)): sha(p)
        for p in [
            BASE / "SOURCE.json",
            Path(__file__),
            BASE.parent / "r01_drawing.py",
            ROOT / source["geometry_source"],
            *sorted((BASE.parent / "fonts").glob("*")),
            ROOT / source["reference"],
        ]
        if p.is_file()
    }
    result["review_surface"] = {
        "path": str((BASE / "review.html").relative_to(ROOT)),
        "sha256": sha(BASE / "review.html"),
    }
    result["entrances"] = entries
    result["geometry_changes"] = []
    result["intentional_changes_from_r01"] = source["intentional_changes_from_r01"]
    (BASE / "MANIFEST.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "One visitor draft saved: SVG, PNG, PDF. Approved sources unchanged; production atlas untouched."
    )


if __name__ == "__main__":
    build()
