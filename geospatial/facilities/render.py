"""Reproducible facility concept sheets from the governed facility source.

Local plans do not create geographic polygons or certify construction.
"""

from __future__ import annotations

import hashlib
import html
import json
import textwrap
from pathlib import Path

import cairosvg
import fitz

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/facilities"
OUT = ROOT / "geospatial/maps/facilities"
INK = "#172e40"
TEAL = "#24716d"
COLORS = {
    "staff": "#e4edf0",
    "restricted": "#d6e5e2",
    "public": "#eee6d6",
    "residential": "#e9e0d7",
    "audit_independent": "#dfddea",
    "reserve": "#f2ede3",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Sheet:
    def __init__(self, identifier, title, subtitle, status, source):
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">',
            "<style>text{font-family:DejaVu Sans,sans-serif;fill:#172e40} .muted{fill:#637078}</style>",
        ]
        self.rect(0, 0, 1600, 1000, "#faf9f5", "none")
        self.rect(0, 0, 1600, 95, INK, "none")
        self.text(45, 47, "SABLE HARBOR", 25, fill="white", weight="bold")
        self.text(1555, 43, identifier, 19, fill="white", anchor="end")
        self.text(45, 135, title, 32, weight="bold")
        self.text(45, 171, subtitle, 18)
        self.text(45, 206, status.replace("_", " "), 16, fill="#922d35")
        self.line(45, 888, 1555, 888, INK, 1)
        self.text(
            45,
            919,
            "11 SEP 2026  |  Rev 0.1.0  |  Concept design; not an occupied-building or construction record",
            16,
        )
        self.text(
            45,
            948,
            "Local metric frame; reference north ↑  |  Not surveyed; do not scale the exported page",
            15,
        )
        self.text(45, 975, "Source: " + source, 13)

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'
        )

    def line(self, x, y, x2, y2, color=INK, width=1, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="M{x:g},{y:g} L{x2:g},{y2:g}" fill="none" stroke="{color}" stroke-width="{width}"{extra}/>'
        )

    def text(self, x, y, t, size=16, fill=INK, weight="normal", anchor="start"):
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" style="fill:{fill}">{html.escape(str(t))}</text>'
        )

    def paragraph(self, x, y, t, width=34, size=16):
        lines = textwrap.wrap(t, width=width, break_long_words=False, break_on_hyphens=False)
        for i, line in enumerate(lines):
            self.text(x, y + i * (size + 6), line, size)
        return y + len(lines) * (size + 6)

    def save(self, name, metadata):
        OUT.mkdir(parents=True, exist_ok=True)
        svg = OUT / (name + ".svg")
        svg.write_text("".join(self.parts) + "</svg>\n")
        cairosvg.svg2png(url=str(svg), write_to=str(OUT / (name + ".png")))
        raw = cairosvg.svg2pdf(url=str(svg))
        doc = fitz.open(stream=raw, filetype="pdf")
        doc.set_metadata(
            {
                "title": metadata["title"],
                "author": "Sable Harbor",
                "creationDate": "D:20260911000000Z",
                "modDate": "D:20260911000000Z",
            }
        )
        doc.save(OUT / (name + ".pdf"), no_new_id=True, deflate=True)
        metadata["artifacts"] = {
            ext: {
                "path": str((OUT / (name + "." + ext)).relative_to(ROOT)),
                "sha256": sha(OUT / (name + "." + ext)),
            }
            for ext in ["svg", "png", "pdf"]
        }
        return metadata


def campus_sheet(model, number=2):
    sid = f"{model.get('map_prefix', 'SH-MAP-SAC')}-{number:03}"
    s = Sheet(
        sid,
        model["name"] + " · master plan",
        model.get(
            "subtitle",
            "Concept spatial program; current geographic context remains separately sourced",
        ),
        model["status"],
        model.get("source_path", "geospatial/facilities/source/campus.json"),
    )
    ew, eh = model["envelope_m"]
    x0, y0 = 70, 245
    k = min(740 / ew, 605 / eh)

    def xy(x, y):
        return (x0 + x * k, y0 + (eh - y) * k)

    def rect(r, fill, stroke=INK, dash=None):
        x, y, w, h = r
        s.rect(*xy(x, y + h), w * k, h * k, fill, stroke, 1.4, dash)

    rect([0, 0, ew, eh], "#f0f1e9", TEAL, "7 5")
    for z in model.get("site_zones", []):
        rect(
            z["rect_m"],
            {
                "parking": "#e0e1de",
                "landscape": "#d8e2d0",
                "reserve": "#f2ede3",
                "public": "#eee6d6",
                "industrial": "#d8dcd9",
                "service": "#d8dcd9",
            }.get(z["type"], "#e4e6df"),
            "#aab3ad",
            "5 4" if z["type"] == "reserve" else None,
        )
        x, y, w, h = z["rect_m"]
        px, py = xy(x + w / 2, y + h / 2)
        pass  # Labels are drawn after routes so they remain legible.
    for key, color, width in [
        ("fire_service_loop_m", "#9eaaa7", 14),
        ("public_arrival_m", "#ae9d7b", 8),
        ("pedestrian_spine_m", TEAL, 6),
        ("service_arrival_m", "#637078", 6),
        ("j2_controlled_entry_m", "#922d35", 5),
    ]:
        pts = model.get("access", {}).get(key, [])
        for a, b in zip(pts, pts[1:]):
            s.line(*xy(*a), *xy(*b), color, width)
    for path in model.get("access", {}).get("pedestrian_branches_m", []):
        for a, b in zip(path, path[1:]):
            s.line(*xy(*a), *xy(*b), TEAL, 4)
    for z in model.get("site_zones", []):
        x, y, w, h = z["rect_m"]
        px, py = xy(x, y + h)
        lines = textwrap.wrap(z["name"], max(10, int(w * k / 7)), break_long_words=False)
        s.rect(px + 2, py + 2, w * k - 4, min(h * k - 4, len(lines) * 15 + 6), "#f0f1e9", "none")
        for j, line in enumerate(lines):
            s.text(px + 5, py + 15 + j * 15, line, 11)
    for b in model["buildings"]:
        rect(b["rect_m"], INK)
        x, y, w, h = b["rect_m"]
        px, py = xy(x + 2, y + h - 5)
        s.rect(px - 2, py - 15, max(35, len(b["id"].split("-")[-1]) * 10), 20, INK, "none")
        s.text(px, py, b["id"].split("-")[-1], 15, fill="white", weight="bold")
        if w * k > 140 and h * k > 65:
            for j, line in enumerate(textwrap.wrap(b["name"], max(10, int(w * k / 8)))[:2]):
                s.text(px, py + 20 + j * 17, line, 12, fill="white")
        for ex in [x, x + w]:
            qx, qy = xy(ex, y + h / 2)
            s.line(qx, qy - 4, qx, qy + 4, "white", 3)
    s.line(845, 305, 845, 255, INK, 3)
    s.text(845, 244, "N", 18, anchor="middle")
    s.line(75, 862, 75 + 50 * k, 862, INK, 4)
    s.text(75, 883, "0", 13)
    s.text(81 + 50 * k, 883, "50 m", 13)
    y = 265
    blocks = [
        (
            "ONE CAMPUS",
            "11.86 acres / 48,000 m² illustrative envelope. District is accepted; property polygon and tenure are unestablished.",
        ),
        (
            "PUBLIC TO RESTRICTED",
            "Arrival to Governance and Education. J2 entry on its own controlled edge. Audit has a separately controlled suite; no ESS pre-clearance.",
        ),
        (
            "SERVICE AND RESILIENCE",
            "Perimeter emergency/service loop; north receiving route. Local edge, dual communications entries and staged utilities only; no primary data center.",
        ),
        (
            "CAPACITY AND EXPANSION",
            "200 parking / 64 bicycle spaces. Third ESS level is a future shell; west reserve supports a separately gated ten-year option.",
        ),
        (
            "LANDSCAPE AND MATERIALS",
            "Shaded pedestrian court, stormwater landscape, durable concrete/metal/stone, warm timber interiors and a restrained Sable Harbor arrival monument.",
        ),
    ]
    if model["site_id"] != "SH-SITE-0001":
        blocks = [
            (
                "SITE BASIS",
                model.get(
                    "geometry_basis", "Illustrative local design envelope; not a property polygon."
                ),
            ),
            (
                "PROGRAM",
                model.get(
                    "program_note",
                    model.get("subtitle", "Known operating functions; schematic fit-out only."),
                ),
            ),
            (
                "OWNERSHIP AND TIME",
                str(model.get("tenure", "Unestablished"))
                + ". Exact occupancy and construction dates remain unestablished.",
            ),
            (
                "DEPENDENCIES",
                "Local geometry does not relocate industrial anchors or create installed process equipment, transport rights or host ownership.",
            ),
            (
                "CAPACITY",
                model.get(
                    "capacity_note",
                    "People and seats are separate measures. See population bridge and source assumptions.",
                ),
            ),
        ]
    for title, body in blocks:
        s.text(950, y, title, 16, weight="bold")
        y = s.paragraph(950, y + 23, body, 61, 14) + 18
    s.text(900, 821, "ACCESS LEGEND", 14, weight="bold")
    for i, (name, color) in enumerate(
        [
            ("Service / emergency", "#9eaaa7"),
            ("Public arrival", "#ae9d7b"),
            ("Pedestrian", TEAL),
            ("Controlled entry", "#922d35"),
        ]
    ):
        xx = 900 + (i % 2) * 300
        yy = 843 + (i // 2) * 24
        s.line(xx, yy, xx + 28, yy, color, 4)
        s.text(xx + 36, yy + 4, name, 12)
    return s.save(
        sid,
        {
            "id": sid,
            "title": model["name"] + " master plan",
            "site_id": model["site_id"],
            "kind": "site",
            "status": model["status"],
        },
    )


def floor_sheet(model, b, f, number):
    mid = f"{model.get('map_prefix', 'SH-MAP-SAC')}-{number:03}"
    w, d = b["rect_m"][2:]
    s = Sheet(
        mid,
        b["name"] + " · " + f"Level {f['level']:02}",
        f["name"] + "  |  " + f["id"],
        f["status"],
        model.get("source_path", "geospatial/facilities/source/campus.json"),
    )
    k = min(1100 / w, 520 / d)
    x0 = 55
    y0 = 295

    def xy(x, y):
        return (x0 + x * k, y0 + (d - y) * k)

    s.rect(*xy(0, d), w * k, d * k, "#e5e5df", INK, 3)
    rh = (d - 3) / 2
    for r in [] if f["status"] == "FUTURE_SHELL" else f["rooms"]:
        x, y, rw, rd = r["rect_m"]
        px, py = xy(x, y + rd)
        s.rect(px, py, rw * k, rd * k, COLORS.get(r["access"], "#e4edf0"), INK, 1.5)
        small = rw * k < 115
        yy = s.paragraph(
            px + 5,
            py + 24,
            r["name"],
            max(7, int(rw * k / (7 if small else 9))),
            12 if small else 17,
        )
        s.text(px + 5, yy + 8, f"{rw * rd:g} m²", 11 if small else 14)
        vals = [
            (r["assigned_desks"], "assigned"),
            (r.get("shared_desks", 0), "shared"),
            (r["touchdown_seats"], "touchdown"),
            (r["training_seats"], "training"),
            (r["meeting_seats"], "meeting"),
            (r["resident_beds"], "beds"),
            (r.get("special_use_concurrent_capacity", 0), "work positions"),
        ]
        label = " · ".join(f"{v} {n}" for v, n in vals if v)
        if label:
            s.paragraph(px + 5, yy + 32, label, max(7, int(rw * k / 8)), 11 if small else 14)
        # Door opening to continuous central corridor. Furniture symbols are diagrammatic.
        dy = y + rd if y == 0 else y
        dx = x + rw / 2
        qx, qy = xy(dx, dy)
        s.line(qx - 9, qy, qx + 9, qy, "#faf9f5", 5)
        s.line(qx - 9, qy, qx - 9, qy + (16 if y else -16), INK, 1)
        count = r["assigned_desks"] + r.get("shared_desks", 0) + r["touchdown_seats"]
        for j in range(min(count, 18)):
            col = j % 6
            row = j // 6
            s.rect(
                px + 10 + col * (rw * k - 25) / 6,
                py + rd * k - 18 - row * 16,
                15,
                9,
                "#faf9f5",
                "#8b9b9e",
                0.6,
            )
        if r.get("resident_beds") == 1:
            s.rect(px + 5, py + rd * k - 60, min(46, rw * k * 0.50), 50, "#f5f1eb", "#9b9186", 1)
            s.text(px + 7, py + rd * k - 38, "Bath", 10)
            s.rect(px + 8, py + rd * k / 2, 22, 40, "#faf9f5", "#9b9186", 1)
        if r.get("training_seats", 0):
            for j in range(r["training_seats"] // 2):
                s.rect(
                    px + 12 + (j % 5) * ((rw * k - 24) / 5),
                    py + rd * k - 24 - (j // 5) * 20,
                    24,
                    12,
                    "#faf9f5",
                    "#8b9b9e",
                    0.7,
                )
    if f["status"] == "FUTURE_SHELL":
        s.text(x0 + w * k / 2, y0 + d * k / 3, "UNFITTED EXPANSION SHELL", 25, anchor="middle")
    # End cores maintain geometry across every level; service and wet zones are separate.
    for x in [] if b.get("layout_style") == "industrial" else [0, w - 6]:
        px, py = xy(x, d)
        for yy, hh, label in [
            (0, rh, "Wet / MEP"),
            (rh, 6, "Stair" if len(b["floors"]) > 1 else "Entry / exit"),
            (
                rh + 6,
                max(0, d - rh - 6),
                ("Lift / service" if x == 0 else "WC / risers")
                if len(b["floors"]) > 1
                else "Service / WC",
            ),
        ]:
            if hh <= 0:
                continue
            ax, ay = xy(x, yy + hh)
            s.rect(ax, ay, 6 * k, hh * k, "#ced4d2", INK, 1.5)
            s.paragraph(ax + 5, ay + 22, label, max(7, int(6 * k / 8)), 12)
            if label == "Stair":
                for j in range(7):
                    s.line(ax + 8, ay + 35 + j * 5, ax + 6 * k - 8, ay + 35 + j * 5, INK, 0.8)
    cy = xy(0, rh + 1.5)[1]
    if b.get("layout_style") != "industrial":
        for xx in [0, 6, w - 6, w] if f["level"] == 1 else [6, w - 6]:
            qx, qy = xy(xx, rh + 1.5)
            s.line(qx, qy - 10, qx, qy + 10, "#faf9f5", 5)
            s.line(qx, qy - 10, qx + 17, qy - 10, INK, 1)
        if f["level"] == 1:
            s.text(x0 - 5, cy + 30, "Exit", 12)
            s.text(x0 + w * k - 20, cy + 30, "Exit", 12)
    if b.get("layout_style") != "industrial":
        s.line(x0 + 6 * k, cy, x0 + (w - 6) * k, cy, TEAL, 2, "7 5")
        s.text(
            x0 + w * k / 2,
            cy - 5,
            "3 m clear circulation · two protected stair routes"
            if len(b["floors"]) > 1
            else "3 m clear circulation · two exterior exit routes",
            13,
            anchor="middle",
        )
    if b.get("layout_style") == "industrial":
        for opening in b.get("openings", []):
            edge = opening["edge"]
            pos = opening["position_m"]
            half = opening["width_m"] * k / 2
            px, py = xy(
                0 if edge == "west" else w if edge == "east" else pos, 0 if edge == "south" else pos
            )
            if edge == "south":
                s.line(px - half, py, px + half, py, "#faf9f5", 6)
            else:
                s.line(px, py - half, px, py + half, "#faf9f5", 6)
        s.text(
            x0,
            y0 + d * k + 53,
            "Perimeter openings are concept access reservations; track, doors and equipment not installed claims.",
            13,
        )
    s.text(x0 + w * k / 2, y0 - 25, f"{w:g} m overall", 16, anchor="middle")
    s.text(
        x0,
        y0 + d * k + 30,
        f"{d:g} m depth  |  "
        + (
            "Function zones; access reservations shown at perimeter"
            if b.get("layout_style") == "industrial"
            else "end service cores in grey; openings face common circulation"
        ),
        15,
    )
    s.text(
        55,
        858,
        "ZONES: blue-grey staff · green restricted · sand public · violet independent audit · tan residence",
        13,
    )
    y = 265
    rows = [
        (
            "AREA",
            f"Gross {f['gross_area_m2']:,.0f} m². Assignable {f['net_assignable_area_m2']:,.0f} m². Core/circulation/service {f['core_circulation_service_m2']:,.0f} m².",
        ),
        (
            "POPULATION",
            f"Planned peak {f.get('planned_peak', 0)} concurrent people. Desks, meeting places, beds and training seats are distinct capacities; do not add them as employees.",
        ),
        (
            "ACCESS",
            "J2 restricted staff only; guest/teaching paths remain outside this building."
            if model["site_id"] == "SH-SITE-0001" and b["id"].endswith("03")
            else "Controlled staff rooms; visitors escorted beyond reception. Audit suite access remains independent."
            if model["site_id"] == "SH-SITE-0001" and b["id"].endswith("01")
            else "Access follows room classification. Deliveries and equipment use service routes.",
        ),
        (
            "DESIGN BASIS",
            "Planning assumptions. Final fire strategy, structure, accessibility and MEP require coordinated engineering.",
        ),
        (
            "STATUS",
            "Unfitted future shell; no occupied capacity in this scenario."
            if f["status"] == "FUTURE_SHELL"
            else "Modelled fit-out; no existing floor, tenure or occupancy asserted.",
        ),
    ]
    for title, body in rows:
        s.text(1200, y, title, 17, weight="bold")
        y = s.paragraph(1200, y + 23, body, 39, 14) + 17
    return s.save(
        mid,
        {
            "id": mid,
            "title": b["name"] + " / " + f["name"],
            "site_id": model["site_id"],
            "building_id": b["id"],
            "floor_id": f["id"],
            "kind": "floor",
            "status": f["status"],
        },
    )


def stacking_sheet(model, b, number):
    mid = f"{model.get('map_prefix', 'SH-MAP-SAC')}-{number:03}"
    s = Sheet(
        mid,
        b["name"] + " · building program",
        b["id"] + "  |  same footprint, cores and access strategy across floors",
        b["status"],
        model.get("source_path", "geospatial/facilities/source/campus.json"),
    )
    y = 275
    for f in reversed(b["floors"]):
        s.rect(60, y, 900, 110, INK if f["status"] != "FUTURE_SHELL" else "#637078", "none")
        s.text(85, y + 35, f["id"] + " · " + f["name"], 22, fill="white")
        s.text(
            85,
            y + 75,
            f"{f['gross_area_m2']:,.0f} m² gross · {f.get('planned_peak', 0)} planned peak · {f['status'].replace('_', ' ')}",
            17,
            fill="white",
        )
        y += 140
    y = 275
    for title, body in [
        (
            "STRUCTURE",
            "Concept structure and spans; see source programme for technical dependencies."
            if len(b["structure"]) > 210
            else b["structure"],
        ),
        (
            "VERTICAL SERVICES",
            "Service, access and utility zones follow the floor plan. See source for engineering dependencies."
            if len(b["core_basis"]) > 210
            else b["core_basis"],
        ),
        (
            "PROGRAM",
            f"{len(b['floors'])} levels; {sum(f['gross_area_m2'] for f in b['floors']):,.0f} m² gross. Vertical access follows the floor/core plan. Mechanical loads and structure are design dependencies.",
        ),
        (
            "CONSTRUCTION STATE",
            "September 2026: modelled concept only. Acquisition, permits, shell, fit-out and commissioning dates are null until supported. 2031 and 2036 are capacity horizons, not completion promises.",
        ),
    ]:
        s.text(1040, y, title, 16, weight="bold")
        y = s.paragraph(1040, y + 23, body, 58, 14) + 20
    return s.save(
        mid,
        {
            "id": mid,
            "title": b["name"] + " stacking and program",
            "site_id": model["site_id"],
            "building_id": b["id"],
            "kind": "building",
            "status": b["status"],
        },
    )


def load_models():
    models = []
    for path in sorted((BASE / "source").glob("*.json")):
        data = json.loads(path.read_text())
        for model in data.get("sites", [data]):
            if "buildings" not in model:
                continue
            model["source_path"] = str(path.relative_to(ROOT))
            models.append(model)
    return models


def phasing_sheet(model, number):
    mid = f"SH-MAP-SAC-{number:03}"
    sheet = Sheet(
        mid,
        "Sacramento · status and capacity horizons",
        "September 2026 record state; dates are evidence dates, not inferred occupancy",
        "MODELLED_PROPOSAL",
        model["source_path"],
    )
    y = 270
    for phase in model["phases"]:
        sheet.rect(55, y, 400, 85, INK, "none")
        sheet.text(75, y + 30, phase["id"] + " · " + phase["name"], 17, fill="white")
        sheet.text(75, y + 62, phase["date"] or "Execution date unestablished", 16, fill="white")
        sheet.text(490, y + 25, phase["state"].replace("_", " "), 18, weight="bold")
        sheet.paragraph(490, y + 55, phase["dependency"], 91, 16)
        y += 115
    return sheet.save(
        mid,
        {
            "id": mid,
            "title": "Sacramento status and capacity horizons",
            "site_id": model["site_id"],
            "kind": "phasing",
            "status": "MODELLED_PROPOSAL",
        },
    )


def build():
    models = load_models()
    records = []
    register_path = ROOT / "geospatial/registers/MAP_ID_REGISTER.json"
    allocation = {
        r["logical_id"]: r["map_id"] for r in json.loads(register_path.read_text())["records"]
    }

    def number(key):
        if key not in allocation:
            raise ValueError("Allocate stable map ID before drawing: " + key)
        return int(allocation[key].rsplit("-", 1)[1])

    for model in models:
        records.append(campus_sheet(model, number(model["site_id"] + "::site")))
        for b in model["buildings"]:
            records.append(stacking_sheet(model, b, number(b["id"] + "::building")))
            for f in b["floors"]:
                records.append(floor_sheet(model, b, f, number(f["id"])))
        if model.get("phases"):
            records.append(phasing_sheet(model, number(model["site_id"] + "::phasing")))
    manifest = {
        "revision": "0.1.0",
        "base_commit": models[0]["authoritative_base"],
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [*sorted((BASE / "source").glob("*.json")), Path(__file__), register_path]
        },
        "generator_sha256": sha(Path(__file__)),
        "maps": records,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"{len(models)} sites; {sum(len(m['buildings']) for m in models)} buildings; {sum(len(b['floors']) for m in models for b in m['buildings'])} floors; {len(records)} sheets / {len(records) * 3} individual files"
    )


if __name__ == "__main__":
    build()
