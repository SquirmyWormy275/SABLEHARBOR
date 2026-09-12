"""V03: architectural linework and compact visitor hierarchy; V01 stays immutable."""

from __future__ import annotations
import math
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
FACILITIES = BASE.parents[1]
sys.path.insert(0, str(FACILITIES))
from r01_drawing import INK, MUTED, PAPER, GOLD, FT, Sheet  # noqa: E402 — local renderer path configured above


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    source = json.loads((BASE / "SOURCE.json").read_text())
    model = json.loads((ROOT / source["geometry_source"]).read_text())
    for path, digest in model["approved_reference_sha256"].items():
        assert sha(ROOT / path) == digest, path
    s = Sheet(
        source["title"], source["subtitle"], source["site_id"], "VISITOR GUIDE", revision="V03"
    )
    s.parts = [
        p.replace(
            "Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.",
            "Fictional campus study. No actual parcel or operating visitor access is established.",
        )
        for p in s.parts
    ]
    # A warmer visitor-facing headline; the institutional wordmark stays unchanged.
    s.parts = [
        part.replace(">CAMPUS VISITOR GUIDE</text>", ">Campus visitor guide</text>")
        .replace('y="249" font-size="62.5"', 'y="249" font-size="76"')
        .replace(
            'y="249" font-size="76" fill="#223740" font-weight="bold"',
            'y="249" font-size="76" fill="#223740" font-weight="normal"',
        )
        for part in s.parts
    ]
    k = 2.72
    x0 = 120
    y0 = 427

    def xy(x, y):
        return x0 + x * k, y0 + (600 - y) * k

    def rect(r, fill="none", stroke="none", sw=1):
        x, y, w, h = r
        s.rect(*xy(x, y + h), w * k, h * k, fill, stroke, sw)

    # Quiet ground, articulated roads and parking; all coordinates from the accepted model.
    rect([0, 0, 840, 600], "#e4e8d8", "#b4bba6", 1.5)
    rect([30, 30, 780, 540], "#ccc9c0", "#b3b2a8", 1.5)
    rect([56, 56, 728, 488], "#e4e8d8", "#b3b2a8", 1.5)
    drawing = model["site_drawing"]
    for r in drawing["roads_ft"]:
        rect(r, "#ccc9c0")
    for r in drawing["walks_ft"]:
        rect(r, "#f0e7d4", "#d2c4a8", 1)
    rect(drawing["service_apron_ft"], "#ddd5c5", "#b6beb5", 1)
    for lot in drawing["parking_blocks"]:
        x, y, w, h = lot["rect_ft"]
        n = lot["columns"]
        rect(lot["rect_ft"], "#dcdad0", "#b0b1a3", 1.5)
        for i in range(n + 1):
            if lot["vertical"]:
                for xx in [x, x + w - 18]:
                    s.line(*xy(xx, y + i * h / n), *xy(xx + 18, y + i * h / n), "#b4b6a9", 1.2)
            else:
                for yy in [y, y + h - 18]:
                    s.line(*xy(x + i * w / n, yy), *xy(x + i * w / n, yy + 18), "#b4b6a9", 1.2)
        if lot["vertical"]:
            for xx in [x + 18, x + w - 18]:
                s.line(*xy(xx, y), *xy(xx, y + h), "#b4b6a9", 1.2)
        else:
            for yy in [y + 18, y + h - 18]:
                s.line(*xy(x, yy), *xy(x + w, yy), "#b4b6a9", 1.2)
        px, py = xy(x + w / 2, y + h / 2)
        s.rect(px - 18, py - 22, 36, 36, PAPER, "none")
        s.text(px, py + 4, "P", 27, fill=INK, weight="bold", anchor="middle")
    for court in drawing["courts"]:
        x, y, w, h = court["rect_ft"]
        rect(court["rect_ft"], "#e9ddc5", "#c7bda6", 1.2)
        name = {
            "CENTRAL QUAD": "CENTRAL QUAD",
            "J2 RECEPTION COURT": "RECEPTION COURT",
            "RESIDENTIAL COURT": "RESIDENTIAL COURT",
            "BIKES / ACCESS": "BICYCLES",
        }[court["name"]]
        s.text(*xy(x + w / 2, y + h / 2 - 2), name.title(), 23, fill="#697354", anchor="middle")
    # Tree centers stay fixed. Canopy outline and shadow are cartographic symbols.
    canopy_colors = ["#9baa81", "#a9b48e", "#93a17b", "#b1bb95"]
    for i, (x, y) in enumerate(drawing["trees_ft"]):
        px, py = xy(x, y)
        radius = 22 + (i % 3) * 1.5

        def crown(cx, cy):
            points = []
            for j in range(48):
                angle = 2 * math.pi * j / 48
                r = radius * (
                    1 + 0.065 * math.sin(angle * 7 + i * 0.8) + 0.035 * math.cos(angle * 5 + i)
                )
                points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
            return "M" + " L".join(f"{xx:.2f},{yy:.2f}" for xx, yy in points) + " Z"

        s.path(crown(px + 5, py + 7), "#c6cbb6", "none")
        s.path(crown(px, py), canopy_colors[i % len(canopy_colors)], "#899877", 1)
        s.path(
            f"M{px - 12},{py + 3} Q{px - 16},{py - 13} {px + 3},{py - 15}",
            stroke="#c2ccad",
            width=1.5,
        )
    entries = []
    for b in model["buildings"]:
        letter = b["r01_letter"]
        spec = source["building_labels"][letter]
        x, y, w, h = b["rect_ft"]
        rect([x + 3, y - 4, w, h], "#c4c3b4", "none")
        rect(b["rect_ft"], "#faf5e9", INK, 3)
        # Inner keyline is a drawing convention, not a proposed wall thickness or roof design.
        rect([x + 3, y + 3, w - 6, h - 6], "none", "#d9d0bc", 1)
        px, py = xy(x, y + h)
        s.text(px + 33, py + 69, letter, 54, fill=INK, weight="bold")
        s.text(
            *xy(x + w / 2, y + h / 2 - 9),
            (spec["name"].title() if letter != "B" else "J2"),
            38,
            weight="normal",
            anchor="middle",
        )
        entry = [v / FT for v in model["access"][spec["entry_key"]][-1]]
        assert abs(entry[1] - y) < 0.001 and x <= entry[0] <= x + w
        entries.append(
            {"building_id": b["id"], "source_access_key": spec["entry_key"], "entry_ft": entry}
        )
    points = [xy(x / FT, y / FT) for x, y in model["access"][source["highlight_route"]]]
    d = "M" + " L".join(f"{x:g},{y:g}" for x, y in points)
    s.path(d, stroke=PAPER, width=16)
    s.parts.append(
        f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for e in entries:
        x, y = xy(*e["entry_ft"])
        # Clear entrance gap and a single directional symbol; no duplicated reception label.
        s.line(x - 12, y, x + 12, y, "white", 7)
        s.path(f"M{x},{y + 6} l-12,22 h24 Z", INK, "none")
    ax, ay = points[0]
    s.circle(ax, ay - 10, 13, GOLD, PAPER, 3)
    s.text(ax + 37, ay - 1, "South arrival", 28, weight="bold")
    dx, dy, dw, dh = next(z["rect_ft"] for z in model["site_zones"] if z["name"] == "Drop-off lane")
    s.text(*xy(dx + dw / 2, dy + dh / 2 - 3), "Drop-off", 23, fill="#556159", anchor="middle")
    s.north(2345, 637)
    s.scale(156, 2090, k, 100)
    s.text(
        1470, 2113, "CONCEPT GEOMETRY  /  NORTH IS UP", 21, fill=MUTED, tracking=1, anchor="middle"
    )
    # Compact directory; one use of each building name and no explanatory cards.
    s.line(2490, 427, 3133, 427, INK, 2)
    s.text(2490, 488, "On campus", 34, weight="normal")
    lines = [
        ("A", "Corporate", "Corporate and client reception"),
        ("B", "J2", "Separate reception"),
        ("C", "Education", "Teaching and campus dining"),
        ("D", "Residence", "Cohort and visitor rooms"),
    ]
    y = 582
    for letter, name, description in lines:
        s.text(2490, y, letter, 35, weight="bold")
        s.text(2560, y, name, 33, weight="bold")
        s.text(2560, y + 44, description, 25, fill=MUTED)
        s.line(2490, y + 82, 3133, y + 82, "#ccd1c9", 1)
        y += 140
    s.text(2490, 1270, "When you arrive", 34, weight="normal")
    s.paragraph(2490, 1327, source["arrival_note"], width=37, size=29, fill=INK, leading=44)
    s.line(2490, 1515, 3133, 1515, "#ccd1c9", 1)
    s.line(2490, 1580, 2540, 1580, GOLD, 8)
    s.text(2570, 1590, "Path to Corporate reception", 25)
    s.path("M2515,1650 l-12,22 h24 Z", INK, "none")
    s.text(2570, 1673, "Building entrance", 25)
    s.text(2515, 1755, "P", 29, weight="bold", anchor="middle")
    s.text(2570, 1755, "Parking area", 25)
    s.line(2490, 1878, 3133, 1878, "#ccd1c9", 1)
    s.paragraph(2490, 1940, source["parking_note"], width=39, size=25, fill=MUTED, leading=38)
    result = s.save(
        BASE / "artifacts",
        "visitor-map-v03",
        {
            "title": source["title"],
            "site_id": source["site_id"],
            "status": source["status"],
            "map_id": None,
            "production_allocation": "PENDING_VISUAL_ACCEPTANCE",
        },
    )
    result["review_surface"] = {
        "path": str((BASE / "review.html").relative_to(ROOT)),
        "sha256": sha(BASE / "review.html"),
    }
    result["revision"] = "V03"
    result["geometry_changes"] = []
    result["entrances"] = entries
    dependencies = [
        BASE / "SOURCE.json",
        Path(__file__),
        FACILITIES / "r01_drawing.py",
        ROOT / source["geometry_source"],
        *sorted((FACILITIES / "fonts").glob("*")),
        *[ROOT / p for p in model["approved_reference_sha256"]],
    ]
    result["sources"] = {str(p.relative_to(ROOT)): sha(p) for p in dependencies if p.is_file()}
    result["intentional_changes"] = source["intentional_changes_from_r01"] + [
        "Inner building keyline is graphic articulation only, not new engineering."
    ]
    (BASE / "MANIFEST.json").write_text(json.dumps(result, indent=2) + "\n")
    print("V03 saved independently; V01 and V02 preserved.")


if __name__ == "__main__":
    build()
