"""Independent architectural study sheets in the preserved R01 graphic system."""

from __future__ import annotations
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = _module("spatial_r01_drawing", BASE.parent / "r01_drawing.py")
M = _module("spatial_normalized_model", BASE / "model.py")
A = _module("spatial_access", BASE / "access.py")


def _label(sheet, x, y, text, width, size=26):
    for line in D.fit_lines(str(text), width, size):
        sheet.text(x, y, line, size)
        y += size * 1.35
    return y


def _sheet(site, building, kind, mid, floor=None):
    title = {
        "sections": "BUILDING SECTIONS",
        "elevations": "FOUR EXTERIOR ELEVATIONS",
        "roof": "ROOF PLAN / SERVICE RESERVATIONS",
        "schedule": "ROOM / CAPACITY SCHEDULE",
        "access": "COORDINATED ROOM ACCESS",
    }[kind]
    subtitle = building["name"] + ((" / " + floor["name"]) if floor else "")
    sheet = D.Sheet(
        title, subtitle[:110], mid, kind, location=site["name"].split("—")[0][:37], revision="SP01"
    )
    sheet.line(2480, 410, 2480, 2050, D.MUTED, 1)
    y = 450
    for head, body in [
        ("SOURCE STATUS", building["status"].replace("_", " ")),
        ("GEOMETRY", building["geometry_role"].replace("_", " ")),
        ("HEIGHT BASIS", building["height_basis"].replace("floor_height_m", "floor height")),
        (
            "DESIGN BOUNDARY",
            "Modelled study. Not surveyed, as-built, engineered or code-certified.",
        ),
    ]:
        sheet.text(2550, y, head, 25, weight="bold")
        y = _label(sheet, 2550, y + 44, body, 555, 25) + 54
    sheet.text(2550, y, "DIMENSIONS / METRES", 25, weight="bold")
    y += 45
    sheet.text(2550, y, f"{building['rect_m'][2]:.2f} × {building['rect_m'][3]:.2f} m", 28)
    y += 50
    sheet.text(
        2550, y, f"Height {building['height_m']:.2f} m + parapet {building['parapet_m']:.2f} m", 24
    )
    return sheet


def _section(sheet, building, axis, top, assumptions):
    width, depth = building["rect_m"][2:]
    span = width if axis == "X" else depth
    scale = min(2050 / span, 470 / (building["height_m"] + building["parapet_m"]))
    x0 = 250
    y0 = top + 550
    sheet.text(
        150,
        top,
        f"{axis}–{axis} / {'EAST–WEST' if axis == 'X' else 'SOUTH–NORTH'} CUT",
        32,
        weight="bold",
    )
    sheet.line(x0 - 35, y0, x0 + span * scale + 35, y0, D.INK, 4)
    for f in building["floors"]:
        bottom = y0 - f["z_m"] * scale
        h = f["height_m"] * scale
        sheet.rect(x0, bottom - h, span * scale, h, D.FILLS["white"], D.INK, 2)
        sheet.rect(
            x0,
            bottom - assumptions["slab_thickness_m"] * scale,
            span * scale,
            assumptions["slab_thickness_m"] * scale,
            D.FILLS["neutral"],
            D.INK,
            1,
        )
        sheet.text(145, bottom - 12, f"L{f['level']} {f['z_m']:.1f}", 21)
        for r in f["rooms"]:
            x, y, w, d = r["rect_m"]
            lo, cross, length, other = (x, y, w, d) if axis == "X" else (y, x, d, w)
            cut = depth * 0.75 if axis == "X" else width * 0.30
            if cross - 1e-6 <= cut <= cross + other + 1e-6:
                architectural = r["geometry_role"] == "partitioned_room"
                sheet.rect(
                    x0 + lo * scale,
                    bottom - h + 4,
                    length * scale,
                    h - 8,
                    D.FILLS.get(r.get("color_group"), D.FILLS["blue"]),
                    D.INK if architectural else D.MUTED,
                    2,
                    "9 7" if not architectural else None,
                )
                if length * scale > 55:
                    sheet.text(
                        x0 + (lo + length / 2) * scale,
                        bottom - h / 2,
                        r["id"].split("-")[-1],
                        20,
                        anchor="middle",
                    )
    sheet.rect(
        x0,
        y0 - building["height_m"] * scale - building["parapet_m"] * scale,
        span * scale,
        building["parapet_m"] * scale,
        D.FILLS["neutral"],
        D.INK,
        2,
    )
    sheet.text(
        x0, y0 + 42, f"Span {span:.2f} m • top of modelled stack {building['height_m']:.2f} m", 24
    )
    sheet.text(
        x0,
        y0 + 82,
        f"Cut offset {depth * 0.75 if axis == 'X' else width * 0.30:.2f} m from {'south' if axis == 'X' else 'west'} edge. Tags: floor schedules; dashed: program zones.",
        22,
        fill=D.MUTED,
    )


def _elevations(sheet, b, assumptions):
    for n, (face, span, edge) in enumerate(
        [
            ("SOUTH", b["rect_m"][2], 0),
            ("NORTH", b["rect_m"][2], 1),
            ("WEST", b["rect_m"][3], 2),
            ("EAST", b["rect_m"][3], 3),
        ]
    ):
        x0 = 200 + (n % 2) * 1120
        top = 470 + (n // 2) * 735
        scale = min(980 / span, 450 / (b["height_m"] + b["parapet_m"]))
        y0 = top + 520
        sheet.text(x0, top, face + " / ASSUMED FACADE", 30, weight="bold")
        sheet.rect(
            x0,
            y0 - (b["height_m"] + b["parapet_m"]) * scale,
            span * scale,
            (b["height_m"] + b["parapet_m"]) * scale,
            b["material"]["wall"],
            D.INK,
            3,
        )
        count = max(1, round(span / assumptions["facade_target_bay_m"]))
        bay = span / count
        for f in b["floors"]:
            bottom = y0 - f["z_m"] * scale
            sheet.line(x0, bottom, x0 + span * scale, bottom, D.INK, 2)
            for j in range(count):
                start = (j + 0.16) * bay
                end = (j + 0.84) * bay
                blocked = False
                for core in f["cores"]:
                    x, y, w, d = core["rect_m"]
                    touch = [
                        abs(y) < 1e-5,
                        abs(y + d - b["rect_m"][3]) < 1e-5,
                        abs(x) < 1e-5,
                        abs(x + w - b["rect_m"][2]) < 1e-5,
                    ][edge]
                    a, z = (x, x + w) if edge < 2 else (y, y + d)
                    if touch and max(start, a) < min(end, z):
                        blocked = True
                if not blocked:
                    sill = assumptions["facade_glazing_sill_m"]
                    head = f["height_m"] - assumptions["facade_glazing_head_clearance_m"]
                    sheet.rect(
                        x0 + start * scale,
                        bottom - head * scale,
                        (end - start) * scale,
                        max(0, head - sill) * scale,
                        b["material"]["glass"],
                        D.INK,
                        1,
                    )
        sheet.text(x0, y0 + 48, f"{span:.2f} m frontage / repeated study bays", 23)
    sheet.text(
        180,
        2010,
        "Openings are proposed rhythm only; explicit perimeter cores are left solid. Materials and facade design remain unselected.",
        23,
        fill=D.MUTED,
    )


def _roof(sheet, b, assumptions):
    w, d = b["rect_m"][2:]
    scale = min(2050 / w, 1300 / d)
    x0 = 240
    y0 = 1880
    sheet.rect(x0, y0 - d * scale, w * scale, d * scale, D.FILLS["neutral"], D.INK, 4)
    sheet.rect(
        x0 + 8, y0 - d * scale + 8, w * scale - 16, d * scale - 16, "none", D.MUTED, 2, "10 7"
    )
    sheet.text(150, 440, "REFERENCE NORTH ↑ / LOCAL BUILDING FRAME", 28, weight="bold")
    for core in b["floors"][-1]["cores"]:
        x, y, cw, cd = core["rect_m"]
        sheet.rect(
            x0 + x * scale, y0 - (y + cd) * scale, cw * scale, cd * scale, "none", D.MUTED, 2, "8 6"
        )
    _label(
        sheet,
        x0 + 45,
        y0 - d * scale + 90,
        "UNALLOCATED ROOF / NO INSTALLED PLANT ASSERTED",
        w * scale - 90,
        32,
    )
    sheet.text(x0, y0 + 60, f"Roof projection {w * d:.1f} m² / {w:.2f} × {d:.2f} m", 28)
    _label(
        sheet,
        180,
        2020,
        "Dashed core projections reserve coordination only; no roof penetration, plant, drainage outlet or safe-access design is asserted.",
        2170,
        24,
    )


def _schedule(sheet, f):
    headers = [
        ("ROOM / FUNCTION", 150),
        ("m²", 1170),
        ("ACCESS", 1310),
        ("DESKS A/S/T", 1680),
        ("LEARN", 1930),
        ("MEET", 2070),
        ("DINE", 2190),
        ("BEDS", 2310),
        ("USE", 2410),
    ]
    for text, x in headers:
        sheet.text(x, 445, text, 23, weight="bold")
    sheet.line(150, 467, 2410, 467, D.INK, 2)
    row = min(76, 1400 / max(1, len(f["rooms"])))
    y = 490
    for r in f["rooms"]:
        short = r["id"].split("-")[-1]
        lines = D.fit_lines(short + " / " + r["name"], 950, 23)
        if len(lines) * 29 > row - 7:
            raise ValueError("Schedule row requires larger page: " + r["id"])
        for n, line in enumerate(lines):
            sheet.text(150, y + 27 + n * 29, line, 23)
        sheet.text(1170, y + 27, f"{r['area_m2']:.1f}", 23)
        sheet.text(1310, y + 27, r["access"][:24], 22)

        def val(k):
            return "?" if r.get(k) is None else str(r[k])

        sheet.text(
            1680,
            y + 27,
            "/".join(val(k) for k in ["assigned_desks", "shared_desks", "touchdown_seats"]),
            23,
        )
        for x, k in [
            (1930, "training_seats"),
            (2070, "meeting_seats"),
            (2190, "dining_seats"),
            (2310, "resident_beds"),
            (2410, "special_use_capacity"),
        ]:
            sheet.text(x, y + 27, val(k), 23)
        sheet.line(150, y + row - 3, 2410, y + row - 3, "#d7ddda", 1)
        y += row
    sheet.text(
        150,
        1970,
        f"Gross {f['gross_area_m2']:.1f} m² • room/program area {sum(r['area_m2'] for r in f['rooms']):.1f} m² • planned peak {f['planned_peak'] if f['planned_peak'] is not None else 'unknown'}",
        27,
    )
    _label(
        sheet,
        150,
        2020,
        "A/S/T = assigned/shared/touchdown desks; USE = special-use capacity. ? = not supplied; 0 = explicit zero. Capacity categories are not employee headcount.",
        2250,
        24,
    )


def _access(sheet, b, f, routes):
    w, d = b["rect_m"][2:]
    scale = min(2100 / w, 1320 / d)
    x0 = 220
    y0 = 1890
    for z in f["circulation"]:
        x, y, cw, cd = z["rect_m"]
        sheet.rect(
            x0 + x * scale,
            y0 - (y + cd) * scale,
            cw * scale,
            cd * scale,
            D.FILLS["sand"],
            D.MUTED,
            1,
        )
    for r in f["rooms"]:
        x, y, rw, rd = r["rect_m"]
        sheet.rect(
            x0 + x * scale,
            y0 - (y + rd) * scale,
            rw * scale,
            rd * scale,
            D.FILLS["white"],
            D.MUTED,
            2,
        )
        sheet.text(
            x0 + (x + rw / 2) * scale,
            y0 - (y + rd) * scale + 30,
            r["id"].split("-")[-1],
            24,
            anchor="middle",
        )
    colors = {"staff": D.BLUE, "J2": "#a45e4c", "service": D.GOLD}
    for n, r in enumerate(routes):
        color = colors[r["classification"]]
        points = r["waypoints_m"]
        for a, z in zip(points, points[1:]):
            sheet.line(
                x0 + a[0] * scale, y0 - a[1] * scale, x0 + z[0] * scale, y0 - z[1] * scale, color, 6
            )
        for p in points[1:-1]:
            sheet.circle(x0 + p[0] * scale, y0 - p[1] * scale, 8, color)
        sheet.circle(x0 + points[0][0] * scale, y0 - points[0][1] * scale, 18, color)
        sheet.text(
            x0 + points[0][0] * scale,
            y0 - points[0][1] * scale + 8,
            str(n + 1),
            21,
            fill="white",
            anchor="middle",
        )
    sheet.text(150, 440, "VERIFIED DOOR–ROOM–CIRCULATION LINKS / NORTH ↑", 30, weight="bold")
    sheet.text(
        150, 1960, "Blue: suite-authorized staff • red: J2-authorized • gold: service staff", 24
    )
    _label(
        sheet,
        150,
        2010,
        "Room tags reference the full schedule. Routes preserve operational access restrictions; furniture clearance, door hardware and egress remain unassessed.",
        2250,
        24,
    )


def build(root: Path = BASE.parents[2]) -> dict:
    root = Path(root).resolve()
    model = M.build_model(root)
    access = A.build_access(root)
    if access["summary"]["failures"]:
        raise ValueError("Access source review failed")
    ids = {
        r["logical_id"]: r["map_id"]
        for r in json.loads((root / "geospatial/registers/MAP_ID_REGISTER.json").read_text())[
            "records"
        ]
    }
    out = root / "geospatial/maps/spatial"
    records = []

    def save(site, b, kind, f=None):
        scope = f["id"] if f else b["id"]
        logical = scope + "::" + kind
        mid = ids[logical]
        sheet = _sheet(site, b, kind, mid, f)
        if kind == "sections":
            _section(sheet, b, "X", 440, model["assumptions"])
            _section(sheet, b, "Y", 1210, model["assumptions"])
            sheet.text(
                180,
                2020,
                f"Slab {model['assumptions']['slab_thickness_m']:.2f} m and parapet {b['parapet_m']:.2f} m are study assumptions; structural design is unassessed.",
                24,
                fill=D.MUTED,
            )
        elif kind == "elevations":
            _elevations(sheet, b, model["assumptions"])
        elif kind == "roof":
            _roof(sheet, b, model["assumptions"])
        elif kind == "schedule":
            _schedule(sheet, f)
        else:
            _access(sheet, b, f, [r for r in access["routes"] if r["floor_id"] == f["id"]])
        meta = {
            "map_id": mid,
            "id": mid,
            "logical_id": logical,
            "kind": kind,
            "site_id": site["id"],
            "building_id": b["id"],
            "floor_id": f["id"] if f else None,
            "title": b["name"] + " / " + (f["name"] + " / " if f else "") + kind,
            "status": "MODELLED_ARCHITECTURAL_STUDY_NOT_ENGINEERED",
        }
        meta = sheet.save(out, mid, meta)
        meta["revision"] = "SP01"
        for ext, a in meta["artifacts"].items():
            a["path"] = str((out / (mid + "." + ext)).relative_to(root))
        records.append(meta)

    for site in model["sites"]:
        for b in site["buildings"]:
            for kind in ["sections", "elevations", "roof"]:
                save(site, b, kind)
            for f in b["floors"]:
                save(site, b, "schedule", f)
                if any(r["floor_id"] == f["id"] for r in access["routes"]):
                    save(site, b, "access", f)
    manifest = {
        "revision": "1.0.0",
        "source_sha256": {**model["source_sha256"], **access["source_sha256"]},
        "maps": records,
        "sheet_count": len(records),
    }
    for p in [
        Path(__file__),
        BASE / "model.py",
        BASE.parent / "r01_drawing.py",
        BASE / "access.py",
        *sorted((BASE.parent / "fonts").glob("*")),
    ]:
        manifest["source_sha256"][str(p.relative_to(root))] = M.sha(p)
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps({"sheets": build(BASE.parents[2])["sheet_count"]}))
