"""R02 editable successors measured from the four immutable approved R01 PNGs.

Do not edit reference bytes. All geometry is local planning geometry, never a parcel.
"""

from __future__ import annotations

import hashlib
import html
import os
from pathlib import Path
import textwrap

from PIL import ImageFont

os.environ["FONTCONFIG_FILE"] = str(Path(__file__).parent / "fonts/fonts.conf")

import cairosvg
import fitz

ROOT = Path(__file__).resolve().parents[2]
INK = "#223740"
MUTED = "#687b80"
PAPER = "#f7f6f1"
BLUE = "#3f7088"
SAGE = "#729085"
GOLD = "#a48a54"
FILLS = {
    "blue": "#e3edf0",
    "sage": "#e5ece5",
    "sand": "#f0eadd",
    "neutral": "#e7e9e5",
    "white": "#ffffff",
}
FT = 0.3048


def esc(value):
    return html.escape(str(value))


class Sheet:
    def __init__(
        self, title, subtitle, identifier, short_name, location="SACRAMENTO", revision="R02"
    ):
        self.identifier = identifier
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="3240" height="2304" viewBox="0 0 3240 2304">',
            "<style>text{font-family:DejaVu Sans,sans-serif}</style>",
        ]
        self.rect(0, 0, 3240, 2304, PAPER, "none")
        self.text(108, 107, "SABLE HARBOR", 42, weight="bold", tracking=11)
        self.text(
            3133,
            102,
            location.upper() + " / INSTITUTIONAL CAMPUS"
            if location == "SACRAMENTO"
            else location.upper() + " / FACILITY STUDY",
            28,
            anchor="end",
        )
        self.line(107, 149, 3135, 149, INK, 3)
        self.text(108, 249, title.upper(), 62.5, weight="bold")
        self.text(108, 313, subtitle, 31, fill=MUTED)
        self.rect(2645, 203, 489, 64, INK, "none")
        self.text(
            2890,
            241,
            "CONCEPT REVIEW / " + revision,
            26,
            fill="white",
            weight="bold",
            anchor="middle",
        )
        self.line(107, 2147, 3135, 2147, INK, 3)
        self.text(108, 2205, "COORDINATED DESIGN STUDY  •  11 SEPTEMBER 2026", 24, fill=MUTED)
        self.text(
            108,
            2248,
            "Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.",
            23,
            fill=MUTED,
        )
        self.text(3133, 2216, identifier, 44, weight="bold", anchor="end")
        self.text(3133, 2267, short_name.upper() + " / " + revision, 22, fill=MUTED, anchor="end")

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=2, dash=None):
        attrs = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:g}"{attrs}/>'
        )

    def line(self, x, y, x2, y2, color=INK, width=2, dash=None):
        attrs = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="M{x:g},{y:g} L{x2:g},{y2:g}" fill="none" stroke="{color}" stroke-width="{width:g}"{attrs}/>'
        )

    def path(self, d, fill="none", stroke=INK, width=2):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>'
        )

    def circle(self, x, y, r, fill, stroke=MUTED, width=1):
        self.parts.append(
            f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>'
        )

    def text(self, x, y, value, size=28, fill=INK, weight="normal", anchor="start", tracking=None):
        extra = f' letter-spacing="{tracking}"' if tracking else ""
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{extra}>{esc(value)}</text>'
        )

    def paragraph(self, x, y, value, width=42, size=28, fill=MUTED, leading=None, weight="normal"):
        lines = textwrap.wrap(str(value), width, break_long_words=False, break_on_hyphens=False)
        for i, line in enumerate(lines):
            self.text(x, y + i * (leading or size * 1.5), line, size, fill=fill, weight=weight)
        return y + len(lines) * (leading or size * 1.5)

    def north(self, x=2375, y=508):
        self.text(x, y - 35, "N", 30, weight="bold", anchor="middle")
        self.path(f"M{x},{y} l-14,45 l14,-13 l14,13 Z", INK, "none")

    def scale(self, x, y, pixels_per_foot, length):
        w = length * pixels_per_foot / 4
        for i in range(4):
            self.rect(x + i * w, y, w, 14, INK if i % 2 == 0 else PAPER, INK, 1.5)
        for n in [0, length / 2, length]:
            self.text(x + n * pixels_per_foot, y + 44, f"{n:g}", 21, anchor="middle")
        self.text(x + 4 * w + 30, y + 16, "FEET", 21, fill=MUTED)

    def note(self, x, y, number, title, body, width=50):
        self.text(x, y, f"{number:02}", 30, fill=BLUE, weight="bold")
        self.text(x + 72, y, title.upper(), 29, weight="bold")
        self.paragraph(x + 72, y + 46, body, width, 27)

    def save(self, out, name, metadata):
        out.mkdir(parents=True, exist_ok=True)
        svg = out / (name + ".svg")
        svg.write_text("".join(self.parts) + "</svg>\n")
        cairosvg.svg2png(url=str(svg), write_to=str(out / (name + ".png")))
        doc = fitz.open(stream=cairosvg.svg2pdf(url=str(svg)), filetype="pdf")
        doc.set_metadata(
            {
                "title": metadata["title"],
                "author": "Sable Harbor",
                "creationDate": "D:20260911000000Z",
                "modDate": "D:20260911000000Z",
            }
        )
        doc.save(out / (name + ".pdf"), garbage=4, deflate=True, no_new_id=True)
        metadata["revision"] = "R02"
        metadata["visual_reference"] = "SH-FAC-REF-SAC-R01"
        metadata["artifacts"] = {
            ext: {
                "path": str((out / (name + "." + ext)).relative_to(ROOT))
                if (out / (name + "." + ext)).is_relative_to(ROOT)
                else str(out / (name + "." + ext)),
                "sha256": hashlib.sha256((out / (name + "." + ext)).read_bytes()).hexdigest(),
            }
            for ext in ["svg", "png", "pdf"]
        }
        return metadata


def fit_lines(text, pixels, size, bold=False):
    font = ImageFont.truetype(
        str(
            Path(__file__).parent / "fonts" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        ),
        int(size),
    )
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if line and font.getlength(trial) > pixels:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def workseats(building):
    return sum(
        sum(r.get(k, 0) for k in ["assigned_desks", "shared_desks", "touchdown_seats"])
        for f in building["floors"]
        for r in f["rooms"]
    )


def master(model, mid, out):
    sac = model["site_id"] == "SH-SITE-0001"
    sheet = Sheet(
        "ONE CAMPUS / FOUR CONNECTED BUILDINGS" if sac else model["name"],
        "Sacramento primary operating base  •  Coordinated conceptual site  •  North is up"
        if sac
        else "Operating context and local planning envelope  •  Reference north is up",
        "MP-001" if sac else mid,
        "MASTER PLAN",
        location="SACRAMENTO" if sac else model["name"].split("—")[0].strip()[:38],
    )
    ew, eh = model["envelope_m"]
    k = min(2284 / ew, 1632 / eh)
    x0, y0 = 120, 427

    def xy(x, y):
        return x0 + x * k, y0 + (eh - y) * k

    def rect(r, fill, stroke=INK, sw=2, dash=None):
        x, y, w, h = r
        sheet.rect(*xy(x, y + h), w * k, h * k, fill, stroke, sw, dash)

    rect([0, 0, ew, eh], "#ebeee6", INK, 3)
    if sac:
        # R01 perimeter road, access spines and parking geometry measured against the actual master PNG.
        rect([30 * FT, 30 * FT, 780 * FT, 540 * FT], "#cbcdc8", "none")
        rect([56 * FT, 56 * FT, 728 * FT, 488 * FT], "#ebeee6", "none")
        drawing = model["site_drawing"]
        for r in drawing["roads_ft"]:
            rect([v * FT for v in r], "#cbcdc8", "none")
        for r in drawing["walks_ft"]:
            rect([v * FT for v in r], "#dddcd5", "none")
        rect([v * FT for v in drawing["service_apron_ft"]], "#dddcd5", MUTED, 1)
        parks = [(p["rect_ft"], p["columns"], p["vertical"]) for p in drawing["parking_blocks"]]
        for r, n, vertical in parks:
            rr = [v * FT for v in r]
            rect(rr, "#dfe2da", "#9eaaa5", 1)
            x, y, w, h = rr
            for i in range(n + 1):
                if vertical:
                    for xx in [x, x + w - 18 * FT]:
                        sheet.line(
                            *xy(xx, y + i * h / n), *xy(xx + 18 * FT, y + i * h / n), "#9eaaa5", 1
                        )
                else:
                    for yy in [y, y + h - 18 * FT]:
                        sheet.line(
                            *xy(x + i * w / n, yy), *xy(x + i * w / n, yy + 18 * FT), "#9eaaa5", 1
                        )
            if vertical:
                for xx in [x + 18 * FT, x + w - 18 * FT]:
                    sheet.line(*xy(xx, y), *xy(xx, y + h), "#9eaaa5", 1)
            else:
                for yy in [y + 18 * FT, y + h - 18 * FT]:
                    sheet.line(*xy(x, yy), *xy(x + w, yy), "#9eaaa5", 1)
        for court in drawing["courts"]:
            r, name = court["rect_ft"], court["name"]
            color = {"blue": BLUE, "sage": SAGE, "neutral": INK}[court["color_group"]]
            rect([v * FT for v in r], "#e1e8da", "#a7b5ae", 1.5)
            x, y, w, h = r
            sheet.text(
                *xy((x + w / 2) * FT, (y + h / 2) * FT),
                name,
                22,
                fill=color,
                weight="bold",
                anchor="middle",
            )
        for x, y in drawing["trees_ft"]:
            sheet.circle(*xy(x * FT, y * FT), 21, "#d8e3d1", "#9fb49c", 1.5)
        for px, py in [(488, 1340), (2190, 1300)]:
            sheet.parts.append(
                f'<text x="{px}" y="{py}" transform="rotate(-90 {px} {py})" font-family="DejaVu Sans" font-size="21" fill="{MUTED}">STAFF PARKING</text>'
            )
    else:
        for z in model.get("site_zones", []):
            rect(
                z["rect_m"],
                FILLS["sage"] if z["type"] == "landscape" else FILLS["neutral"],
                "#a7b5ae",
                1.5,
            )
            zx, zy, zw, zh = z["rect_m"]
            tx, ty = xy(zx + zw / 2, zy + zh / 2)
            font = min(25, max(18, zh * k * 0.22))
            lines = fit_lines(z["name"].upper(), zw * k - 24, font, True)
            for i, line in enumerate(lines):
                sheet.text(
                    tx,
                    ty + (i - (len(lines) - 1) / 2) * (font + 5),
                    line,
                    font,
                    fill=MUTED,
                    weight="bold",
                    anchor="middle",
                )
        for key in [
            "fire_service_loop_m",
            "public_arrival_m",
            "pedestrian_spine_m",
            "service_arrival_m",
        ]:
            points = model.get("access", {}).get(key, [])
            for a, b in zip(points, points[1:]):
                sheet.line(*xy(*a), *xy(*b), "#bdc5c0", 14)
    for b in model["buildings"]:
        r = b["rect_m"]
        x, y, w, h = r
        letter = b.get("r01_letter", b["id"].split("-")[-1])
        color = BLUE if letter in ["A", "B"] else GOLD if letter == "C" else SAGE
        px, py = xy(x, y + h)
        sheet.rect(px + 8, py + 8, w * k, h * k, "#cdd5cb", "none")
        sheet.rect(px, py, w * k, h * k, "white", color, 5)
        sheet.rect(px, py, 21, h * k, color, "none")
        if sac:
            sheet.text(px + 58, py + 72, letter, 54, fill=color, weight="bold")
            cy = py + h * k / 2
            sheet.text(
                px + w * k / 2,
                cy,
                b["name"]
                .replace("Building " + letter + " — ", "")
                .replace("Building " + letter + " - ", "")
                .upper(),
                36,
                weight="bold",
                anchor="middle",
            )
            beds = sum(r.get("resident_beds", 0) for f in b["floors"] for r in f["rooms"])
            sheet.text(
                px + w * k / 2,
                cy + 48,
                f"{len(b['floors'])} FLOORS  /  {beds if beds else workseats(b)} {'ROOMS' if beds else 'DESKS'}",
                25,
                fill=MUTED,
                anchor="middle",
            )
            qx, qy = xy(x + (44 * FT if letter == "C" else w / 2), y)
            sheet.path(f"M{qx},{qy} l-14,20 h28 Z", color, "none")
        else:
            sheet.rect(px + 3, py + 3, max(70, len(letter) * 17), 35, INK, "none")
            sheet.text(px + 8, py + 29, letter, 24, fill="white", weight="bold")
            if w * k > 220 and h * k > 100:
                sheet.paragraph(px + 15, py + 70, b["name"], int(w * k / 15), 24, fill=INK)
    sheet.north(2327, 665)
    sheet.line(2483, 396, 3133, 396, "#a5b4b2", 2)
    sheet.text(2483, 456, "CAMPUS SCHEDULE" if sac else "SITE PROGRAM", 31, weight="bold")
    y = 540
    if sac:
        for letter, name, body, color in [
            ("A", "CORPORATE", "Corporate · Foundry Field · Atlas · Advisory", BLUE),
            ("B", "J2", "Contact · Judgment · Orientation · JAG · HQ", BLUE),
            ("C", "EDUCATION", "Teaching · Faculty · Shared hospitality", GOLD),
            ("D", "RESIDENCE", "Cohorts · Visiting faculty", SAGE),
        ]:
            sheet.text(2483, y, letter, 42, fill=color, weight="bold")
            sheet.text(2555, y - 5, name, 32, weight="bold")
            sheet.paragraph(2555, y + 40, body, 36, 27)
            y += 168
        sheet.line(2483, 1110, 3133, 1110, "#a5b4b2", 2)
        sheet.text(2483, 1168, "ONE COORDINATED PROGRAM", 30, weight="bold")
        sheet.paragraph(
            2483,
            1240,
            "A 69,984 gross sq ft | B 44,928 gross sq ft | C 30,240 gross sq ft | D 30,240 gross sq ft",
            39,
            29,
            fill=INK,
        )
        sheet.paragraph(
            2483,
            1420,
            "175,392 gross sq ft total across ten floors. R02 continues the approved R01 composition and floorplates.",
            39,
            29,
            fill=INK,
        )
        sheet.paragraph(
            2483,
            1610,
            "362 fitted staff workplaces + 60 residential rooms. Meeting, learning and dining seats are counted separately.",
            39,
            29,
            fill=INK,
        )
        sheet.paragraph(
            2483,
            1810,
            "252 drawn parking bays before accessible-bay conversion. Transport demand and event overflow remain to be resolved.",
            39,
            27,
        )
        sheet.text(*xy(258 * FT, 88 * FT), "PARKING COURT", 21, fill=MUTED, anchor="middle")
        sheet.text(*xy(630 * FT, 91 * FT), "DROP-OFF LANE", 21, fill=MUTED, anchor="middle")
        sheet.text(
            *xy(420 * FT, 16 * FT), "PRIMARY CAMPUS ARRIVAL", 24, weight="bold", anchor="middle"
        )
        sheet.scale(158, 2088, k * FT, 100)
        sheet.text(
            900,
            2116,
            "840′ × 600′ / 11.57-acre fictional study envelope / No actual parcel selected",
            25,
            fill=MUTED,
        )
    else:
        for b in model["buildings"]:
            labels = fit_lines(b["id"].split("-")[-1] + " / " + b["name"], 650, 27, True)
            for line in labels:
                sheet.text(2483, y, line, 27, weight="bold")
                y += 35
            y -= 35
            y = (
                sheet.paragraph(
                    2483,
                    y + 43,
                    f"{len(b['floors'])} levels; {sum(f['gross_area_m2'] for f in b['floors']):,.0f} m² concept gross area.",
                    40,
                    26,
                )
                + 40
            )
        for title, body in [
            ("STATUS", model["status"].replace("_", " ")),
            (
                "PRECISION",
                "Local concept envelope, not a surveyed parcel or installed equipment record.",
            ),
            (
                "DEPENDENCIES",
                model.get("floor_exemption")
                or "; ".join(model.get("dependencies", []))
                or "Source geometry and actual access/tenure remain governed by the existing geographic register.",
            ),
        ]:
            sheet.text(2483, y, title, 28, weight="bold")
            y = sheet.paragraph(2483, y + 43, body, 40, 26) + 40
        sheet.scale(
            158,
            2088,
            k * FT,
            min([20, 40, 100, 200, 500, 1000, 2000], key=lambda length: abs(length * k * FT - 400)),
        )
        sheet.text(
            900,
            2116,
            "Planning envelope / Reference north / Geometry and tenure status remain separate",
            24,
            fill=MUTED,
        )
    sheet.text(2483, 2050, model["site_id"] + " / " + mid, 18, fill=MUTED)
    return sheet.save(
        out,
        mid,
        {
            "id": mid,
            "title": model["name"] + " / master site plan",
            "site_id": model["site_id"],
            "kind": "site",
            "status": model["status"],
        },
    )


def draw_workplaces(
    sheet, x, y, w, h, count, group=4, teaching=False, columns=None, team_labels=False
):
    """Draw exactly count chairs with useful worktables, in R01's restrained symbol language."""
    if not count or w < 20 or h < 20:
        return
    import math

    groups = math.ceil(count / group)
    columns = columns or min(groups, max(1, math.ceil(math.sqrt(groups * w / max(h, 1) / 1.6))))
    rows = math.ceil(groups / columns)
    cw, ch = w / columns, h / rows
    remaining = count
    for i in range(groups):
        n = min(group, remaining)
        remaining -= n
        cx, cy = x + (i % columns + 0.5) * cw, y + (i // columns + 0.5) * ch
        tw = min(100, cw * 0.65)
        th = min(52, ch * 0.4)
        chair = min(19, tw * 0.18, ch * 0.13)
        sheet.rect(cx - tw / 2, cy - th / 2, tw, th, "white", MUTED, 1.4)
        if team_labels:
            sheet.text(cx, cy - th / 2 - 18, f"TEAM {i + 1}", 19, fill=MUTED, anchor="middle")
        if n >= 2 and not teaching:
            sheet.line(cx, cy - th / 2, cx, cy + th / 2, MUTED, 1)
        if n >= 4 and not teaching:
            sheet.line(cx - tw / 2, cy, cx + tw / 2, cy, MUTED, 1)
        for j in range(n):
            if n == 1:
                dx, dy = 0, th / 2 + chair
            elif n == 2:
                dx, dy = (-tw / 4 if j == 0 else tw / 4), th / 2 + chair
            else:
                dx, dy = (
                    (-tw / 4 if j % 2 == 0 else tw / 4),
                    (-th / 2 - chair if j < 2 else th / 2 + chair),
                )
            sheet.rect(cx + dx - chair / 2, cy + dy - chair / 2, chair, chair, PAPER, MUTED, 1)
            if teaching:
                continue
            sheet.line(
                cx + dx - chair * 0.4,
                cy + (-th * 0.2 if dy < 0 else th * 0.2),
                cx + dx + chair * 0.4,
                cy + (-th * 0.2 if dy < 0 else th * 0.2),
                MUTED,
                1.4,
            )


def draw_meeting(sheet, x, y, w, h, count, columns=None):
    if not count:
        return
    import math

    groups = math.ceil(count / 8)
    cols = columns or min(groups, max(1, math.ceil(math.sqrt(groups * w / max(h, 1)))))
    rows = math.ceil(groups / cols)
    cw, ch = w / cols, h / rows
    remaining = count
    for i in range(groups):
        n = min(8, remaining)
        remaining -= n
        cx, cy = x + (i % cols + 0.5) * cw, y + (i // cols + 0.5) * ch
        tw, th = min(100, cw * 0.5), min(55, ch * 0.35)
        chair = min(20, cw * 0.12, ch * 0.14)
        sheet.rect(cx - tw / 2, cy - th / 2, tw, th, PAPER, MUTED, 1.3)
        pos = [
            (-tw * 0.25, -th / 2 - chair),
            (tw * 0.25, -th / 2 - chair),
            (-tw * 0.25, th / 2 + chair),
            (tw * 0.25, th / 2 + chair),
            (-tw / 2 - chair, -th * 0.25),
            (tw / 2 + chair, -th * 0.25),
            (-tw / 2 - chair, th * 0.25),
            (tw / 2 + chair, th * 0.25),
        ]
        for dx, dy in pos[:n]:
            sheet.rect(cx + dx - chair / 2, cy + dy - chair / 2, chair, chair, PAPER, MUTED, 1)


def floor(model, b, f, mid, out):
    sac = model["site_id"] == "SH-SITE-0001"
    r01 = b.get("layout_style") == "r01"
    letter = b.get("r01_letter", b["id"].split("-")[-1])
    level = int(f.get("level", f["id"].rsplit("L", 1)[-1]))
    code = f"{letter}-{100 + level:03}" if sac else mid
    name = (
        b["name"]
        .replace("Building " + letter + " — ", "")
        .replace("Building " + letter + " - ", "")
    )
    sheet = Sheet(
        name + " / LEVEL " + f"{level:02}",
        f.get("subtitle", f.get("name", "Coordinated function plan"))
        + "  •  One floor shown  •  North is up",
        code,
        name + " / FLOOR PLAN",
        location="SACRAMENTO" if sac else model["name"].split("—")[0].strip()[:38],
    )
    sheet.text(3133, 287, f["id"] + "  /  " + mid, 18, fill=MUTED, anchor="end")
    w, d = b["rect_m"][2:]
    k = min(2176 / w, 1142 / d)
    x0, y0 = 133, 577

    def xy(x, y):
        return x0 + x * k, y0 + (d - y) * k

    def rect(r, fill, stroke=INK, sw=2):
        x, y, rw, rh = r
        sheet.rect(*xy(x, y + rh), rw * k, rh * k, fill, stroke, sw)

    rect([0, 0, w, d], FILLS["neutral"], INK, 5)
    cores = b.get("core_zones", [])
    circulation = f.get("circulation_zones", [])
    if not r01 and b.get("layout_style") != "industrial":
        circulation = [{"rect_m": [6, d / 2 - 1.5, w - 12, 3], "name": "SHARED CIRCULATION"}]
        cores = []
        for xx in [0, w - 6]:
            cores.extend(
                [
                    {
                        "rect_m": [xx, 0, 6, max(0, d / 2 - 4.5)],
                        "name": "WET / SERVICES",
                        "type": "service",
                    },
                    {
                        "rect_m": [xx, d / 2 - 4.5, 6, 9],
                        "name": "STAIR" if len(b["floors"]) > 1 else "EXIT / ACCESS",
                        "type": "stair" if len(b["floors"]) > 1 else "service",
                    },
                    {
                        "rect_m": [xx, d / 2 + 4.5, 6, max(0, d / 2 - 4.5)],
                        "name": "LIFT / SERVICE" if len(b["floors"]) > 1 else "EQUIPMENT",
                        "type": "lift" if len(b["floors"]) > 1 else "service",
                    },
                ]
            )
    for z in cores:
        r = z["rect_m"]
        rect(r, FILLS["neutral"])
        x, y, rw, rh = r
        px, py = xy(x, y + rh)
        if z.get("type") == "stair":
            for step in range(12):
                sheet.line(
                    px + rw * k * 0.17,
                    py + 35 + step * min(16, (rh * k - 70) / 12),
                    px + rw * k * 0.83,
                    py + 35 + step * min(16, (rh * k - 70) / 12),
                    MUTED,
                    1.2,
                )
        label = z.get("display_name", z["name"]).upper()
        font = min(23, max(16, rw * k / 9))
        lines = fit_lines(label, rw * k - 24, font, True)
        base = min(py + rh * k * 0.68, py + rh * k - 18 - (len(lines) - 1) * (font + 5))
        for i, line in enumerate(lines):
            sheet.text(px + 12, base + i * (font + 5), line, font, weight="bold")
    for z in circulation:
        rect(z["rect_m"], FILLS["neutral"], "none")
        x, y, rw, rh = z["rect_m"]
        px, py = xy(x + rw / 2, y + rh / 2)
        if rw * k > 180 and rh * k > 35:
            sheet.text(
                px,
                py + 7,
                z.get("name", "CIRCULATION").upper(),
                min(23, rw * k / max(1, len(z.get("name", "CIRCULATION"))) * 1.5),
                fill=MUTED,
                anchor="middle",
            )
    for room in f["rooms"]:
        r = room["rect_m"]
        x, y, rw, rh = r
        px, py = xy(x, y + rh)
        group = room.get("color_group")
        if group not in FILLS:
            group = {
                "staff": "blue",
                "restricted": "blue",
                "public": "sand",
                "residential": "sage",
                "audit_independent": "sage",
                "reserve": "neutral",
            }.get(room.get("access"), "neutral")
        if b.get("layout_style") == "industrial":
            sheet.rect(px, py, rw * k, rh * k, FILLS[group], MUTED, 2, dash="9 6")
        else:
            rect(r, FILLS[group], INK, 2.5)
        available_w, available_h = rw * k, rh * k
        title = room.get("display_name", room["name"]).upper()
        count = sum(room.get(t, 0) for t in ["assigned_desks", "shared_desks", "touchdown_seats"])
        training, meeting, dining, beds = (
            room.get(t, 0)
            for t in ["training_seats", "meeting_seats", "dining_seats", "resident_beds"]
        )
        if count:
            label = f"{count} " + (
                "DESK"
                if count == 1
                else "TOUCHDOWN DESKS"
                if room.get("touchdown_seats") == count
                else "WORKSTATIONS"
            )
        elif training:
            label = f"{training} TEACHING SEATS"
        elif dining:
            label = f"{dining} DINING SEATS"
        elif meeting:
            label = f"{meeting} MEETING SEATS"
        elif beds:
            label = "SINGLE ROOM"
        else:
            label = room.get("purpose", "")
        if room.get("display_detail"):
            label = room["display_detail"]
        font = 28 if available_w > 250 else 23 if available_w > 145 else 18
        margin = 12 if available_h < 180 else 20
        if not sac:
            margin = 45
        while True:
            lines = fit_lines(title, available_w - 24, font, True)
            label_font = max(13, font - 4)
            wrapped = fit_lines(label, available_w - 24, label_font) if label else []
            text_height = len(lines) * (font + 4) + len(wrapped) * (label_font + 4) + margin
            measure = ImageFont.truetype(
                str(Path(__file__).parent / "fonts/DejaVuSans-Bold.ttf"), int(font)
            )
            fits_width = all(measure.getlength(line) <= available_w - 24 for line in lines)
            if (text_height <= available_h * 0.55 and fits_width) or font <= 14:
                break
            font -= 1
        yy = py + margin + font
        for line in lines:
            sheet.text(px + available_w / 2, yy, line, font, weight="bold", anchor="middle")
            yy += font + 4
        for line in wrapped:
            sheet.text(px + available_w / 2, yy, line, label_font, fill=MUTED, anchor="middle")
            yy += label_font + 4
        fx, fy = px + margin, yy + 8
        fw, fh = available_w - 2 * margin, py + available_h - margin - fy
        if count:
            if sac and letter == "B" and level == 1 and "reception" in room["name"].lower():
                fw *= 0.45
            draw_workplaces(
                sheet,
                fx,
                fy,
                fw,
                fh,
                count,
                group=2
                if room.get("touchdown_seats") or (sac and letter == "C" and level == 1)
                else 4,
                columns=5 if count == 40 and sac and letter == "A" and level == 2 else None,
                team_labels=bool(
                    sac and letter == "B" and level == 1 and room.get("touchdown_seats")
                ),
            )
        elif room.get("kind") == "hall" and training:
            sheet.rect(fx + fw * 0.08, fy, fw * 0.84, 28, "#dddcd3", "#a7b5ae", 1)
            rows = 10
            cols = math_ceil(training / rows)
            size = min(23, (fw - 50) / (cols + 3), (fh - 65) / (rows + 1))
            for i in range(training):
                col, row = i % cols, i // cols
                gap = 40 if col >= cols / 2 else 0
                xx = fx + (fw - (cols + 1) * (size + 10) - 40) / 2 + col * (size + 10) + gap
                sheet.rect(xx, fy + 50 + row * (size + 7), size, size, PAPER, MUTED, 1)
        elif training:
            draw_workplaces(sheet, fx, fy, fw, fh, training, 4, teaching=True)
        elif meeting or dining:
            draw_meeting(
                sheet, fx, fy, fw, fh, meeting or dining, columns=4 if dining == 80 else None
            )
        elif beds:
            bw, bh = min(fw * 0.35, 3.2 * FT * k), min(fh * 0.6, 6.7 * FT * k)
            sheet.rect(fx + fw * 0.08, fy + 12, bw, bh, "white", MUTED, 1.5)
            sheet.rect(fx + fw * 0.08 + 4, fy + 16, bw - 8, bh * 0.19, PAPER, MUTED, 1)
            aw, ah = min(fw * 0.42, 7 * FT * k), min(fh * 0.34, 8 * FT * k)
            sheet.rect(fx + fw - aw, fy + fh - ah, aw, ah, FILLS["neutral"], MUTED, 1.3)
            sheet.text(fx + fw - aw / 2, fy + fh - ah / 2, "BATH", 16, fill=MUTED, anchor="middle")
            sheet.line(
                fx + fw - aw, fy + fh - ah * 0.45, fx + fw - aw, fy + fh - ah * 0.1, "white", 5
            )
        elif "kitchen" in room["name"].lower() and fh > 40:
            sheet.rect(fx + 10, fy + 15, fw - 20, 26, PAPER, MUTED, 1.5)
            # Freestanding preparation counters leave the west dining-service doorway clear.
            sheet.rect(
                fx + fw * 0.32, fy + fh * 0.78, fw * 0.46, min(35, fh * 0.16), PAPER, MUTED, 1.5
            )
            sheet.rect(
                fx + fw * 0.32, fy + fh * 0.5, fw * 0.46, min(45, fh * 0.22), PAPER, MUTED, 1.5
            )
            for i in range(4):
                sheet.circle(fx + 65 + i * 27, fy + 28, 7, PAPER, MUTED)
            sheet.text(
                fx + fw * 0.55,
                fy + fh * 0.5 - 10,
                "PREP / SERVICE",
                17,
                fill=MUTED,
                anchor="middle",
            )
    if b.get("layout_style") == "industrial":
        bounds = sorted(
            {
                0,
                d,
                *(r["rect_m"][1] for r in f["rooms"]),
                *(r["rect_m"][1] + r["rect_m"][3] for r in f["rooms"]),
            }
        )
        for low, high in zip(bounds, bounds[1:]):
            if high < d - 0.01 and not any(
                r["rect_m"][1] < high - 0.001 and r["rect_m"][1] + r["rect_m"][3] > low + 0.001
                for r in f["rooms"]
            ):
                px, py = xy(w / 2, (low + high) / 2)
                sheet.text(
                    px,
                    py + 8,
                    "SHARED CIRCULATION / SERVICE ACCESS",
                    min(23, (high - low) * k * 0.4),
                    fill=MUTED,
                    anchor="middle",
                )
        top = max(r["rect_m"][1] + r["rect_m"][3] for r in f["rooms"])
        if top < d - 0.01:
            px, py = xy(w / 2, (top + d) / 2)
            sheet.text(
                px,
                py + 8,
                "CIRCULATION / WET AND SERVICE RESERVE · INTERNAL PARTITIONS UNRESOLVED",
                min(23, w * k / 65),
                fill=MUTED,
                anchor="middle",
            )
    # R01 exterior window strokes are diagrammatic openings, not a glazing specification.
    for room in f["rooms"]:
        x, y, rw, rh = room["rect_m"]
        if room.get("kind") not in ["support"] and b.get("layout_style") != "industrial":
            for edge in ([0] if abs(y) < 0.001 else []) + ([d] if abs(y + rh - d) < 0.001 else []):
                for a, beta in [(0.08, 0.35), (0.55, 0.85)]:
                    sheet.line(*xy(x + rw * a, edge), *xy(x + rw * beta, edge), BLUE, 5)
    # Room and circulation apertures are sourced independently of occupant counts.
    doors = f.get("doors", [])
    if not doors and not r01 and b.get("layout_style") != "industrial":
        for room in f["rooms"]:
            x, y, rw, rh = room["rect_m"]
            north = y < d / 2
            doors.append(
                {
                    "x_m": x + rw / 2,
                    "y_m": y + rh if north else y,
                    "width_m": min(1.1, rw * 0.3),
                    "wall": "north" if north else "south",
                }
            )
    if not r01 and b.get("layout_style") != "industrial":
        for xx, wall in [(6, "east"), (w - 6, "west")]:
            doors.append({"x_m": xx, "y_m": d / 2, "width_m": 1.2, "wall": wall})
        for xx in [3, w - 3]:
            for yy, wall in [(d / 2 - 4.5, "north"), (d / 2 + 4.5, "south")]:
                doors.append({"x_m": xx, "y_m": yy, "width_m": 1.1, "wall": wall})
        if level == 1:
            for xx, wall in [(0, "west"), (w, "east")]:
                doors.append(
                    {"x_m": xx, "y_m": d / 2, "width_m": 1.2, "wall": wall, "swing": "out"}
                )
    for door in doors:
        wall = door.get("wall", door.get("edge", "south"))
        if "x_m" in door:
            dx, dy = door["x_m"], door["y_m"]
        else:
            fraction = door.get("position_fraction", 0.5)
            dx = w * fraction if wall in ["north", "south"] else (0 if wall == "west" else w)
            dy = d * fraction if wall in ["west", "east"] else (0 if wall == "south" else d)
        px, py = xy(dx, dy)
        dw = door.get("width_m", 1.1) * k
        if door.get("leaves") == 2 and wall in ["north", "south"]:
            sheet.line(px - dw / 2, py, px + dw / 2, py, PAPER, 8)
            leaf = dw / 2
            sign = (1 if wall == "north" else -1) * (-1 if door.get("swing") == "out" else 1)
            for side in [-1, 1]:
                hinge = px + side * leaf
                sheet.line(hinge, py, hinge, py + sign * leaf, MUTED, 1.5)
                sheet.path(
                    f"M{px},{py} A{leaf},{leaf} 0 0 {1 if sign * side < 0 else 0} {hinge},{py + sign * leaf}",
                    stroke=MUTED,
                    width=1.5,
                )
            continue
        if wall in ["north", "south"]:
            sheet.line(px - dw / 2, py, px + dw / 2, py, PAPER, 8)
            sign = (1 if wall == "north" else -1) * (-1 if door.get("swing") == "out" else 1)
            sheet.line(px - dw / 2, py, px - dw / 2, py + sign * dw, MUTED, 1.5)
            sheet.path(
                f"M{px + dw / 2},{py} A{dw},{dw} 0 0 {1 if sign > 0 else 0} {px - dw / 2},{py + sign * dw}",
                stroke=MUTED,
                width=1.5,
            )
        else:
            sheet.line(px, py - dw / 2, px, py + dw / 2, PAPER, 8)
            sign = (1 if wall == "west" else -1) * (-1 if door.get("swing") == "out" else 1)
            sheet.line(px, py - dw / 2, px + sign * dw, py - dw / 2, MUTED, 1.5)
            sheet.path(
                f"M{px},{py + dw / 2} A{dw},{dw} 0 0 {0 if sign > 0 else 1} {px + sign * dw},{py - dw / 2}",
                stroke=MUTED,
                width=1.5,
            )
    if b.get("layout_style") == "industrial":
        for opening in b.get("openings", []):
            side = opening.get("side", opening.get("wall", opening.get("edge", "south")))
            offset = opening.get(
                "offset_m",
                opening.get("position_m", w / 2 if side in ["north", "south"] else d / 2),
            )
            width = opening.get("width_m", 1.2)
            if side in ["north", "south"]:
                y = d if side == "north" else 0
                sheet.line(*xy(offset - width / 2, y), *xy(offset + width / 2, y), PAPER, 9)
            else:
                x = 0 if side == "west" else w
                sheet.line(*xy(x, offset - width / 2), *xy(x, offset + width / 2), PAPER, 9)
    # Dimension strings are drawing dimensions, not fabricated geographic precision.
    wf, df = w / FT, d / FT
    sheet.line(x0, 505, x0 + w * k, 505, MUTED, 1)
    ticks = 6 if sac and letter == "C" else 8
    for i in range(ticks + 1):
        xx = x0 + i * w * k / ticks
        sheet.line(xx, 505, xx, y0 - 10, "#a2b0af", 1)
        sheet.text(xx, 463, f"{wf * i / ticks:.0f}", 20, fill=MUTED, anchor="middle")
    sheet.text(x0 + w * k / 2, 417, f"{wf:.0f}′ OVERALL", 27, weight="bold", anchor="middle")
    sheet.line(x0 - 60, y0, x0 - 60, y0 + d * k, MUTED, 1.5)
    dimx, dimy = 53, y0 + d * k / 2
    sheet.parts.append(
        f'<text x="{dimx}" y="{dimy}" transform="rotate(-90 {dimx} {dimy})" text-anchor="middle" font-size="22" fill="{MUTED}">{df:.0f}′</text>'
    )
    if sac and level == 1:
        entries = (
            [(44, "CAMPUS ENTRY"), (138, "CATERING / SERVICE")]
            if letter == "C"
            else [
                (
                    84 if letter == "D" else 108,
                    "RESIDENTIAL ENTRY" if letter == "D" else "CAMPUS ENTRY",
                )
            ]
        )
        for xf, label in entries:
            px, py = xy(xf * FT, 0)
            sheet.text(px, py + 40, label, 18, fill=MUTED, anchor="middle")
    if sac and letter == "B" and level == 1:
        px, py = xy(108 * FT, 25 * FT)
        sheet.text(px, py - 8, "CONTROLLED", 15, fill=BLUE, anchor="middle")
    sheet.north()

    def total(key):
        return sum(r.get(key, 0) for r in f["rooms"])

    desks = sum(total(key) for key in ["assigned_desks", "shared_desks", "touchdown_seats"])
    sheet.line(2483, 396, 3133, 396, "#a5b4b2", 2)
    sheet.text(2483, 456, "THIS FLOOR", 31, weight="bold")
    y = 550
    metrics = [(desks, "FITTED WORKPLACES"), (f["gross_area_m2"] / FT**2, "GROSS SQUARE FEET")]
    if letter == "C" and level == 1 and sac:
        metrics = [(120, "HALL SEATS"), ("2 × 24", "CLASSROOM SEATS"), (80, "DINING SEATS")]
    elif total("resident_beds"):
        metrics = [
            (total("resident_beds"), "RESIDENTIAL ROOMS"),
            (f["gross_area_m2"] / FT**2, "GROSS SQUARE FEET"),
        ]
    for value, label in metrics:
        sheet.text(
            2483,
            y,
            f"{value:,.0f}" if isinstance(value, (int, float)) else value,
            62,
            weight="bold",
        )
        sheet.text(2483, y + 55, label, 24, fill=MUTED)
        y += 160
    sheet.line(2483, y - 30, 3133, y - 30, "#a5b4b2", 2)
    y += 28
    side_notes = f.get("sheet_notes", [])
    if sac:
        common = {
            "title": "DESIGN LOAD / STATUS",
            "body": f"{f['gross_area_m2'] / FT**2:,.0f} gross sq ft; {f['planned_peak']} planned concurrent occupants. R02 concept only; actual staffing, occupancy and construction remain unestablished.",
        }
        if letter == "A" and level == 2:
            side_notes = [
                {
                    "title": "STAFF ≠ DESKS",
                    "body": "Foundry Field: 160 modelled staff / 80 desks here. Atlas Meridian: 36 modelled staff / 32 desks here. These R01 scenario counts are not an actual employee census.",
                },
                {
                    "title": "IN THE SAME BUILDING",
                    "body": "L01: Advisory, client reception, visiting workplaces and commons. L03: corporate officers, ESS and an independently secured Internal Audit suite. Product organizations retain separate leadership.",
                },
                common,
            ]
        elif letter == "B" and level == 1:
            side_notes = [
                {
                    "title": "WORKPLACE ALLOCATION",
                    "body": "48 Contact workplaces include Head Mara Hammer and Deputy; 12 JAG touchdown desks serve six five-person returning teams; 2 HQ reception/support desks. Desk allocation does not reduce team size.",
                },
                {
                    "title": "UPSTAIRS / LEVEL 02",
                    "body": "30 Judgment + 16 Orientation + 22 J2 HQ desks. Building total: 130 workplaces. Education's 35 billets are already within J2's 237 authorized billets; actual occupied staff by arm remain unknown.",
                },
                common,
            ]
        elif letter == "C" and level == 1:
            side_notes = [
                {
                    "title": "ONE EDUCATION ARM",
                    "body": "35 Education billets are already within J2. Four program/registrar workplaces here plus 28 upstairs = 32 fitted desks. Hall and classrooms are alternative configurations within the 120 day-learner cap.",
                },
                {
                    "title": "RESIDENTIAL COURT / D",
                    "body": "60 single rooms across the quiet court: 48 cohort rooms and 12 faculty/visitor rooms. Resident learners remain inside the day cohort. One production kitchen serves 80 dining seats here and 80 in A.",
                },
                common,
            ]
        elif letter == "D":
            side_notes = [
                {
                    "title": "QUIET RESIDENTIAL EDGE",
                    "body": "20 single rooms on this level: 16 cohort and 4 faculty/visitor rooms. The building provides 60 rooms across three floors. Beds do not create employees or increase the 120 day-learner cap.",
                },
                {
                    "title": "SHARED HOSPITALITY",
                    "body": "Education's single production kitchen supports the campus dining program. Residential arrivals remain separate from teaching, J2 reception and corporate visitor paths.",
                },
                common,
            ]
        else:
            side_notes = [
                {
                    "title": "FLOOR PROGRAM",
                    "body": " · ".join(
                        r["name"]
                        for r in f["rooms"]
                        if sum(
                            r.get(t, 0)
                            for t in ["assigned_desks", "shared_desks", "touchdown_seats"]
                        )
                        > 0
                    ),
                },
                {
                    "title": "INSTITUTIONAL BOUNDARY",
                    "body": "Board governs, CEO directs and ESS administers shared services. Internal Audit retains independently controlled Board access; J2 and business product organizations retain their separate authority.",
                },
                common,
            ]
    if isinstance(side_notes, dict):
        side_notes = [{"title": k, "body": v} for k, v in side_notes.items()]
    if not side_notes:
        side_notes = [
            {
                "title": "PEOPLE / CAPACITY",
                "body": f"Planned concurrent load: {f['planned_peak']}. Fitted workplaces, meeting seats, learners and residents are separate measures; actual occupancy remains unestablished.",
            },
            {
                "title": "COORDINATED BUILDING",
                "body": f"{len(b['floors'])} levels use the same footprint and aligned service/core positions. Rooms are local concept allocations, not an as-built survey.",
            },
            {
                "title": "ACCESS AND STATUS",
                "body": f.get(
                    "egress_concept",
                    "Access follows the sourced circulation and room classification. Geometry, services and final code review remain design dependencies.",
                ),
            },
        ]
    for note in side_notes[:3]:
        title = note.get("title", "DESIGN BASIS")
        body = note.get("body", note.get("text", ""))
        sheet.text(2483, y, title.upper(), 28, weight="bold")
        y = sheet.paragraph(2483, y + 50, body, 39, 27, fill=INK) + 48
    notes = f.get("design_notes", [])
    if not notes:
        notes = [
            {
                "title": "COORDINATED ACCESS",
                "body": "Room entries connect to shared or controlled circulation; vertical cores are coordinated across the building.",
            },
            {
                "title": "PLANNING BOUNDARY",
                "body": "Local concept geometry preserves current functions. Occupancy, construction, engineering and exact parcel evidence remain separately governed.",
            },
        ]
    if b.get("layout_style") == "industrial":
        notes = [
            {
                "title": "OPERATIONAL ZONES",
                "body": "Dashed lines allocate work areas, not walls or installed equipment. Internal thresholds and engineered handling paths remain unresolved.",
            },
            {
                "title": "PERIMETER ACCESS",
                "body": "Sourced openings reserve personnel and handling interfaces. The service band remains inside the gross area; final fire, utility and accessibility design requires engineering.",
            },
        ]
    for i, n in enumerate(notes[:2]):
        if isinstance(n, str):
            n = {
                "title": f.get("design_note_headings", ["DESIGN BASIS", "DESIGN BASIS"])[i],
                "body": n,
            }
        sheet.note(
            137 + i * 1180,
            1828,
            i + 1,
            n.get("title", "DESIGN BASIS"),
            n.get("body", n.get("text", "")),
            width=49,
        )
    sheet.scale(162, 2050, k * FT, 40 if wf > 180 else 28)
    sheet.text(
        1010,
        2090,
        f.get(
            "legend_text",
            "Blue: operational work  /  Sage: secondary program  /  Sand: shared and visitor areas",
        ),
        23,
        fill=MUTED,
    )
    return sheet.save(
        out,
        mid,
        {
            "id": mid,
            "title": name + " / " + f["name"],
            "site_id": model["site_id"],
            "building_id": b["id"],
            "floor_id": f["id"],
            "kind": "floor",
            "status": f["status"],
        },
    )


def math_ceil(value):
    return int(-(-value // 1))


def stacking(model, b, mid, out):
    name = b["name"]
    sac = model["site_id"] == "SH-SITE-0001"
    sheet = Sheet(
        name + " / BUILDING PROGRAM",
        "Coordinated floor stack  •  Same footprint and fixed service cores",
        mid,
        "BUILDING PROGRAM",
        location="SACRAMENTO" if sac else model["name"].split("—")[0].strip()[:38],
    )
    y = 530
    for f in reversed(b["floors"]):
        sheet.rect(133, y, 2176, 300, FILLS["blue"], INK, 3)
        level_name = f"L{int(f.get('level', f['id'].rsplit('L', 1)[-1])):02} / " + f["name"].upper()
        size = 38
        while (
            ImageFont.truetype(
                str(Path(__file__).parent / "fonts/DejaVuSans-Bold.ttf"), size
            ).getlength(level_name)
            > 2070
        ):
            size -= 1
        sheet.text(178, y + 65, level_name, size, weight="bold")
        desks = sum(
            sum(r.get(k, 0) for k in ["assigned_desks", "shared_desks", "touchdown_seats"])
            for r in f["rooms"]
        )
        sheet.text(
            178,
            y + 120,
            f"{f['gross_area_m2'] / FT**2:,.0f} gross sq ft  /  {desks} workplaces  /  {f['planned_peak']} planned peak",
            29,
            fill=MUTED,
        )
        functions = [
            r["name"]
            for r in f["rooms"]
            if any(
                r.get(t, 0)
                for t in [
                    "assigned_desks",
                    "shared_desks",
                    "touchdown_seats",
                    "training_seats",
                    "dining_seats",
                    "resident_beds",
                ]
            )
        ]
        if not functions or not sac:
            functions = [r["name"] for r in f["rooms"] if r.get("kind") != "support"]
        description = " · ".join(dict.fromkeys(functions))
        lines = fit_lines(description, 2070, 26)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1].rsplit(" ", 1)[0] + " … (see individual floor)"
        for i, line in enumerate(lines):
            sheet.text(178, y + 185 + i * 39, line, 26, fill=INK)
        y += 350
    y = 465
    for title, body in [
        (
            "PROGRAM",
            f"{len(b['floors'])} floors / {sum(f['gross_area_m2'] for f in b['floors']) / FT**2:,.0f} gross sq ft. Staff workplaces, training, meeting, dining and residence remain separate capacities.",
        ),
        (
            "STRUCTURE / SERVICES",
            b.get(
                "structure",
                "Concept spans and services; engineering and utility loads require site-specific verification.",
            ),
        ),
        (
            "CORE COORDINATION",
            b.get(
                "core_basis",
                "Use the sourced structure plan; industrial layouts do not receive invented office cores or installed equipment.",
            ),
        ),
        (
            "SEPTEMBER 2026",
            "Concept design only. Parcel, tenure, permit, construction and occupancy evidence remain separate. No completed facility is asserted.",
        ),
    ]:
        sheet.line(2483, y - 35, 3133, y - 35, "#a5b4b2", 2)
        sheet.text(2483, y, title, 28, weight="bold")
        y = sheet.paragraph(2483, y + 48, body, 39, 27, fill=INK) + 75
    sheet.note(
        137,
        1840,
        1,
        "ONE BUILDING",
        "Floorplates and service shafts align vertically. Detailed engineering and fire strategy remain coordinated design dependencies.",
        61,
    )
    sheet.text(162, 2080, b["id"] + " / LOCAL CONCEPT STACK / NOT TO SCALE", 24, fill=MUTED)
    return sheet.save(
        out,
        mid,
        {
            "id": mid,
            "title": name + " / building program",
            "site_id": model["site_id"],
            "building_id": b["id"],
            "kind": "building",
            "status": b["status"],
        },
    )


def phasing(model, mid, out):
    sheet = Sheet(
        "CAMPUS / STATUS AND CAPACITY",
        "September 2026 evidence state  •  Planning horizons are not completion dates",
        mid,
        "STATUS AND PHASING",
    )
    y = 510
    for i, p in enumerate(model["phases"]):
        sheet.line(133, y - 42, 2310, y - 42, "#a5b4b2", 2)
        sheet.text(133, y, f"{i + 1:02}", 40, fill=BLUE, weight="bold")
        sheet.text(240, y, p["name"].upper(), 33, weight="bold")
        sheet.text(240, y + 55, p["state"].replace("_", " "), 27, fill=MUTED)
        sheet.paragraph(240, y + 110, p["dependency"], 97, 27, fill=INK)
        y += 260
    sheet.text(2483, 460, "SOURCE-BOUND STATUS", 30, weight="bold")
    sheet.paragraph(
        2483,
        530,
        "R01 approved the drawing system and campus planning baseline. R02 extends the remaining floors and publication system. Neither approval is a land purchase, building permit, staffing authorization or completed construction record.",
        38,
        29,
        fill=INK,
    )
    sheet.paragraph(
        2483,
        1050,
        "Actual dates remain null until supported. Growth horizons reserve choices; capacity changes require a source-based successor and transport/engineering review.",
        38,
        29,
        fill=INK,
    )
    sheet.text(
        160,
        2075,
        model["site_id"] + " / SEPTEMBER 2026 / NO CONSTRUCTION COMPLETION ASSERTED",
        24,
        fill=MUTED,
    )
    return sheet.save(
        out,
        mid,
        {
            "id": mid,
            "title": "Sacramento / status and capacity",
            "site_id": model["site_id"],
            "kind": "phasing",
            "status": "MODELLED_PROPOSAL",
        },
    )
