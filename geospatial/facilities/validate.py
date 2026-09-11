"""Validate facility source, independent plans, provenance and atlas navigation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/facilities"
MANIFEST = ROOT / "geospatial/maps/facilities/MANIFEST.json"
RUNTIME = BASE / "RUNTIME_BRIDGE.json"
COUNTS = (
    "assigned_desks",
    "shared_desks",
    "touchdown_seats",
    "training_seats",
    "meeting_seats",
    "resident_beds",
)
STATUSES = {
    "PROPOSED_MODELLED_PROGRAM_FROM_APPROVED_R01",
    "MODELLED_R02_FROM_APPROVED_R01_NOT_AS_BUILT",
    "MODELLED_R02_DESIGN_NOT_EXISTING",
    "PROPOSED_MODELLED_PROGRAM",
    "MODELLED_NOT_AS_BUILT",
    "MODELLED_FITOUT_NOT_EXISTING",
    "FUTURE_SHELL",
    "SYNTHETIC_OPERATING",
    "SYNTHETIC_IN_SERVICE_2026_07_07",
    "PRELIMINARY_ENGINEERING_PROPOSAL",
    "ILLUSTRATIVE_FITOUT_EXISTING_FUNCTION_NOT_AS_BUILT",
    "ILLUSTRATIVE_NOT_SURVEYED",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_models():
    sources = sorted((BASE / "source").glob("*.json"))
    models = []
    for path in sources:
        data = json.loads(path.read_text())
        if "sites" in data:
            models.extend(data["sites"])
        elif "site_id" in data:
            models.append(data)
        else:
            raise ValueError(f"{path}: unexplained source schema; expected site_id or sites")
    return models, sources


def numeric(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def overlap(a, b):
    return (
        min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > 1e-6
        and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > 1e-6
    )


R01_REFERENCE_DIR = ROOT / "docs/facilities/references/sacramento-hq/r01-approved"
R01_HASHES = {
    "01_Sacramento_Campus_Master_Draft.png": "23729f7e2b427e58820361363e4a47fbc6bbd3ce9774ef67932ecab7a50bfa47",
    "02_Corporate_L02_Product_Draft.png": "09a3339ece443d6e7e8cd148cd8f207b56cd938a03efde4f4c5f8e9367dd6179",
    "03_J2_L01_Contact_JAG_Draft.png": "17bf92029276f7794721129e58830344a9a3ee4341c858f2c928d53ad8b0fefb",
    "04_Education_L01_Teaching_Draft.png": "d37ff987cf1036d32cf0fe07ca3b9a0578d7f359bd820fde2551cb268ed88361",
}
R01_CORE_RECTS_FT = {
    "A": [
        [0, 42, 18, 24],
        [198, 42, 18, 24],
        [0, 0, 18, 42],
        [198, 0, 18, 42],
        [90, 0, 12, 24],
        [90, 24, 12, 24],
        [114, 34, 12, 14],
        [114, 24, 12, 10],
        [114, 0, 12, 24],
    ],
    "B": [
        [0, 40, 18, 24],
        [198, 40, 18, 24],
        [0, 0, 18, 40],
        [198, 0, 18, 40],
        [90, 22, 12, 24],
        [114, 32, 12, 14],
        [114, 22, 12, 10],
    ],
    "C": [
        [0, 66, 16, 24],
        [0, 50, 16, 16],
        [160, 50, 8, 40],
        [0, 16, 16, 24],
        [152, 16, 16, 24],
        [0, 0, 16, 16],
        [152, 0, 16, 16],
    ],
}


def reference_bytes_errors(filename, content, record):
    errors = []
    expected = R01_HASHES[filename]
    if hashlib.sha256(content).hexdigest() != expected or record.get("sha256") != expected:
        errors.append("immutable R01 reference hash mismatch " + filename)
    dimensions = (
        list(__import__("struct").unpack(">II", content[16:24]))
        if content[:8] == b"\x89PNG\r\n\x1a\n" and len(content) >= 24
        else None
    )
    if dimensions != [3240, 2304] or record.get("dimensions_px") != [3240, 2304]:
        errors.append("R01 reference dimensions mismatch " + filename)
    if record.get("status") != "APPROVED_VISUAL_REFERENCE":
        errors.append("R01 reference status mismatch " + filename)
    return errors


def validate_r01_references():
    manifest_path = R01_REFERENCE_DIR / "MANIFEST.json"
    if not manifest_path.is_file():
        return ["missing approved R01 reference manifest"]
    manifest = json.loads(manifest_path.read_text())
    records = {r["filename"]: r for r in manifest["files"]}
    errors = []
    if (
        manifest.get("status") != "APPROVED_VISUAL_REFERENCE"
        or manifest.get("immutable") is not True
    ):
        errors.append("R01 reference manifest must preserve approved immutable status")
    for filename in R01_HASHES:
        p = R01_REFERENCE_DIR / filename
        if not p.is_file() or filename not in records:
            errors.append("missing approved R01 reference " + filename)
        else:
            errors.extend(reference_bytes_errors(filename, p.read_bytes(), records[filename]))
    archive = R01_REFERENCE_DIR / "SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip"
    if (
        not archive.is_file()
        or sha(archive) != "eb10588f6cc6e214d8541b96b1bd044f52f0df85e384fc53a316b55b5d026fe0"
    ):
        errors.append("immutable R01 recovered ZIP mismatch")
    return errors


def validate_r01(site):
    """Check the recovered approval, not the superseded six-building implementation."""
    errors = []

    def check(ok, message):
        if not ok:
            errors.append("R01 " + message)

    def close(a, b):
        return numeric(a) and math.isclose(a, b, abs_tol=0.01)

    def seats(floor, key):
        return sum(r.get(key, 0) for r in floor.get("rooms", []))

    def workplaces(floor):
        return sum(seats(floor, k) for k in ["assigned_desks", "shared_desks", "touchdown_seats"])

    by_letter = {
        b.get("r01_letter", b.get("letter", b["id"].rsplit("-", 1)[-1])): b
        for b in site.get("buildings", [])
    }
    check(
        len(site.get("buildings", [])) == 4 and set(by_letter) == set("ABCD"),
        "requires four distinct buildings A/B/C/D",
    )
    if set(by_letter) != set("ABCD"):
        return errors
    centers = {
        letter: (b["rect_m"][0] + b["rect_m"][2] / 2, b["rect_m"][1] + b["rect_m"][3] / 2)
        for letter, b in by_letter.items()
    }
    check(
        centers["A"][0] < centers["C"][0]
        and centers["B"][0] < centers["D"][0]
        and centers["A"][1] < centers["B"][1]
        and centers["C"][1] < centers["D"][1],
        "approved southwest/northwest/southeast/northeast composition changed",
    )
    check(
        all(close(a, b * 0.3048) for a, b in zip(site.get("envelope_m", []), [840, 600])),
        "840 ×600 ft study envelope changed",
    )
    approved = {
        "A": (3, 216, 108, 200),
        "B": (2, 216, 104, 130),
        "C": (2, 168, 90, 32),
        "D": (3, None, None, 0),
    }
    all_floors = []
    for letter, b in by_letter.items():
        n, w, d, target = approved[letter]
        floors = b.get("floors", [])
        all_floors.extend(floors)
        check(
            b.get("layout_style") == "r01",
            letter + " must use explicit R01 geometry, not automatic cores",
        )
        check(
            len(floors) == n and {f["level"] for f in floors} == set(range(1, n + 1)),
            letter + " required floor stack incomplete",
        )
        if w:
            check(
                close(b["rect_m"][2], w * 0.3048) and close(b["rect_m"][3], d * 0.3048),
                letter + " approved floorplate changed",
            )
        else:
            check(
                close(b["rect_m"][2] * b["rect_m"][3], 10080 * 0.09290304),
                "D floorplate must be10080 ft²",
            )
        check(
            sum(workplaces(f) for f in floors) == target,
            letter + " approved workplace total changed",
        )
        cores = b.get("core_zones", [])
        check(bool(cores), letter + " missing explicit core stack")
        core_ft = sorted(tuple(z.get("rect_ft", [])) for z in cores)
        if letter in R01_CORE_RECTS_FT:
            check(
                core_ft == sorted(tuple(r) for r in R01_CORE_RECTS_FT[letter]),
                letter + " approved core coordinates changed",
            )
        for f in floors:
            if "core_zones" in f:
                check(f["core_zones"] == cores, f["id"] + " core stack differs from building")
            circulation = f.get("circulation_zones", [])
            check(bool(circulation), f["id"] + " missing explicit circulation")
            zones = f.get("rooms", []) + cores + circulation
            area = 0
            for z in zones:
                rect = z.get("rect_m", [])
                if len(rect) != 4 or not all(numeric(v) for v in rect):
                    check(False, f["id"] + " invalid explicit zone")
                    continue
                x, y, zw, zh = rect
                area += zw * zh
                check(
                    zw > 0
                    and zh > 0
                    and x + zw <= b["rect_m"][2] + 1e-6
                    and y + zh <= b["rect_m"][3] + 1e-6,
                    f["id"] + " zone outside footprint",
                )
                if "rect_ft" in z:
                    check(
                        len(z["rect_ft"]) == 4
                        and all(close(v, ft * 0.3048) for v, ft in zip(rect, z["rect_ft"])),
                        f["id"] + " feet/metres disagree",
                    )
            check(
                close(area, f.get("gross_area_m2", -1)),
                f["id"] + " explicit room/core/circulation partition incomplete",
            )
            for i, z in enumerate(zones):
                for other in zones[i + 1 :]:
                    if len(z.get("rect_m", [])) == 4 and len(other.get("rect_m", [])) == 4:
                        check(
                            not overlap(z["rect_m"], other["rect_m"]),
                            f["id"] + " overlapping explicit room/core/circulation zones",
                        )
            for r in f.get("rooms", []):
                check(numeric(r.get("dining_seats")), r["id"] + " missing distinct dining category")
        levels = {f["level"]: f for f in floors}
        if letter == "A" and 2 in levels:
            check(workplaces(levels[2]) == 112, "A-Level02 must have112 workplaces")
            for name, total in [("foundry", 80), ("atlas", 32)]:
                check(
                    sum(
                        sum(
                            r.get(k, 0)
                            for k in ["assigned_desks", "shared_desks", "touchdown_seats"]
                        )
                        for r in levels[2]["rooms"]
                        if name in r["name"].lower()
                    )
                    == total,
                    "A-Level02 " + name + " allocation changed",
                )
        if letter == "B":
            for level, total in [(1, 62), (2, 68)]:
                if level in levels:
                    check(
                        workplaces(levels[level]) == total,
                        "B-Level" + str(level) + " workplace allocation changed",
                    )
        if letter == "C":
            for level, total in [(1, 4), (2, 28)]:
                if level in levels:
                    check(
                        workplaces(levels[level]) == total,
                        "C-Level" + str(level) + " workplace allocation changed",
                    )
            if 1 in levels:
                check(
                    seats(levels[1], "training_seats") == 168,
                    "C teaching configurations must retain120hall +2×24classrooms",
                )
                check(
                    seats(levels[1], "dining_seats") == 80, "C-Level01 must retain80 dining seats"
                )
        if letter == "D":
            bedrooms = [r for f in floors for r in f["rooms"] if r.get("resident_beds", 0)]
            check(
                len(bedrooms) == 60 and all(r["resident_beds"] == 1 for r in bedrooms),
                "D must have60 individual single-occupancy rooms",
            )
    check(len(all_floors) == 10, "must retain ten floors")
    check(
        close(sum(f["gross_area_m2"] for f in all_floors), 175392 * 0.09290304),
        "175392 ft² campus area changed",
    )
    check(sum(workplaces(f) for f in all_floors) == 362, "362 fitted staff workplaces changed")
    check(
        sum(seats(f, "dining_seats") for f in all_floors) == 160,
        "shared campus dining must remain160 seats",
    )
    return errors


def validate_models(models, coverage_ids=None):
    errors = []
    ids = []

    def check(ok, message):
        if not ok:
            errors.append(message)

    def rectangle(rect, envelope, ident):
        if not isinstance(rect, list) or len(rect) != 4 or not all(numeric(n) for n in rect):
            errors.append(f"{ident}: invalid rectangle")
            return False
        x, y, w, h = rect
        check(
            w > 0 and h > 0 and x + w <= envelope[0] + 1e-6 and y + h <= envelope[1] + 1e-6,
            f"{ident}: rectangle exceeds envelope",
        )
        return True

    for site in models:
        sid = site.get("site_id")
        ids.append(sid)
        check(bool(sid), "missing site ID")
        if coverage_ids is not None:
            check(sid in coverage_ids, f"{sid}: no coverage disposition for containing site")
        for field in [
            "status",
            "geometry_status",
            "fictionality",
            "tenure",
            "geometry_basis",
            "sources",
        ]:
            check(bool(site.get(field)), f"{sid}: missing {field}")
        check(site.get("status") in STATUSES, f"{sid}: invalid status")
        for field in ["occupancy_start", "construction_start", "construction_completion"]:
            check(field in site, f"{sid}: missing temporal field {field}")
        for source in site.get("sources", []):
            check((ROOT / source.split("#")[0]).is_file(), f"{sid}: missing source {source}")
        env = site.get("envelope_m")
        if not isinstance(env, list) or len(env) != 2 or not all(numeric(n) and n > 0 for n in env):
            errors.append(f"{sid}: invalid site envelope")
            continue
        if sid == "SH-SITE-0001":
            errors.extend(validate_r01(site))
        buildings = site.get("buildings", [])
        if not buildings:
            check(
                bool(site.get("floor_exemption")),
                f"{sid}: no buildings and no justified floor exemption",
            )
        floors = {}
        for b in buildings:
            bid = b.get("id")
            ids.append(bid)
            check(bool(bid), f"{sid}: missing building ID")
            check(b.get("status") in STATUSES, f"{bid}: invalid status")
            check(
                bool(b.get("structure")) and bool(b.get("core_basis")),
                f"{bid}: missing structure/core concept",
            )
            if not rectangle(b.get("rect_m"), env, bid):
                continue
            w, d = b["rect_m"][2:]
            check(bool(b.get("floors")), f"{bid}: missing required floors")
            if "modelled_floor_count" in b:
                check(
                    b["modelled_floor_count"] == len(b["floors"]),
                    f"{bid}: modelled floor count mismatch",
                )
            levels = []
            for f in b.get("floors", []):
                fid = f.get("id")
                ids.append(fid)
                floors[fid] = f
                levels.append(f.get("level"))
                check(bool(fid), f"{bid}: missing floor ID")
                check(f.get("status") in STATUSES, f"{fid}: invalid status")
                check(numeric(f.get("planned_peak")), f"{fid}: invalid planned population")
                for k in ["gross_area_m2", "net_assignable_area_m2", "core_circulation_service_m2"]:
                    check(numeric(f.get(k)), f"{fid}: invalid {k}")
                if all(
                    numeric(f.get(k))
                    for k in [
                        "gross_area_m2",
                        "net_assignable_area_m2",
                        "core_circulation_service_m2",
                    ]
                ):
                    check(
                        math.isclose(f["gross_area_m2"], w * d, abs_tol=0.01),
                        f"{fid}: gross area / footprint mismatch",
                    )
                    check(
                        math.isclose(
                            f["gross_area_m2"],
                            f["net_assignable_area_m2"] + f["core_circulation_service_m2"],
                            abs_tol=0.01,
                        ),
                        f"{fid}: area rollup mismatch",
                    )
                rooms = f.get("rooms", [])
                net = 0
                check(
                    bool(rooms) or f.get("status") == "FUTURE_SHELL", f"{fid}: missing room program"
                )
                for r in rooms:
                    rid = r.get("id")
                    ids.append(rid)
                    check(bool(rid), f"{fid}: missing room ID")
                    if rectangle(r.get("rect_m"), [w, d], rid):
                        net += r["rect_m"][2] * r["rect_m"][3]
                    check(
                        bool(r.get("access")) and bool(r.get("basis")),
                        f"{rid}: access/basis missing",
                    )
                    for k in COUNTS:
                        check(numeric(r.get(k)), f"{rid}: missing or invalid capacity category {k}")
                    for k in ["special_use_capacity", "special_use_concurrent_capacity"]:
                        if k in r:
                            check(numeric(r[k]), f"{rid}: invalid {k}")
                    if sid == "SH-SITE-0001":
                        check(
                            not re.search(
                                r"(primary|production|enterprise).*data\s*cent(er|re)",
                                r.get("name", ""),
                                re.I,
                            ),
                            f"{rid}: prohibited primary production data center",
                        )
                check(
                    math.isclose(net, f.get("net_assignable_area_m2", -1), abs_tol=0.01),
                    f"{fid}: room area / assignable mismatch",
                )
                for i, r in enumerate(rooms):
                    for other in rooms[i + 1 :]:
                        check(
                            not overlap(r["rect_m"], other["rect_m"]),
                            f"{fid}: overlapping rooms {r['id']}/{other['id']}",
                        )
                if f.get("status") == "FUTURE_SHELL":
                    check(
                        f.get("planned_peak") == 0, f"{fid}: future shell claims occupied capacity"
                    )
            check(len(levels) == len(set(levels)), f"{bid}: duplicate floor levels")
        for i, b in enumerate(buildings):
            for other in buildings[i + 1 :]:
                check(
                    not overlap(b["rect_m"], other["rect_m"]),
                    f"{sid}: overlapping building footprints",
                )
        for scenario in site.get("attendance_scenarios", []):
            ident = scenario["id"]
            check(bool(scenario.get("basis")), f"{ident}: no population basis")
            pop = scenario.get("people")
            allocations = scenario.get("floor_populations")
            if allocations is not None:
                check(
                    set(allocations) == set(floors),
                    f"{ident}: missing/orphan floor population allocation",
                )
                if allocations:
                    check(
                        numeric(pop) and math.isclose(sum(allocations.values()), pop),
                        f"{ident}: population rollup mismatch",
                    )
                else:
                    check(pop in [None, 0], f"{ident}: population without indoor allocation")
                for fid, n in allocations.items():
                    check(numeric(n), f"{ident}: invalid allocation {fid}")
                    if fid in floors and numeric(n):
                        check(
                            n <= floors[fid]["planned_peak"],
                            f"{ident}: exceeds floor planned peak {fid}",
                        )
            categories = ["workers", "trainees", "other_visitors"]
            if any(k in scenario for k in categories):
                check(
                    all(numeric(scenario.get(k)) for k in categories),
                    f"{ident}: incomplete attendance categories",
                )
                if all(numeric(scenario.get(k)) for k in categories):
                    check(
                        sum(scenario[k] for k in categories) == pop,
                        f"{ident}: attendance category rollup mismatch",
                    )
            for sub, total in [
                ("resident_trainees_subset", "trainees"),
                ("temporary_resident_visitors_subset", "other_visitors"),
            ]:
                if sub in scenario:
                    check(
                        numeric(scenario[sub]) and scenario[sub] <= scenario.get(total, 0),
                        f"{ident}: invalid resident subset",
                    )
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    check(not duplicates, "duplicate IDs: " + str(duplicates))
    return errors


def r02_dependency_errors(locks):
    required = [
        BASE / "render.py",
        BASE / "r01_drawing.py",
        ROOT / "geospatial/registers/MAP_ID_REGISTER.json",
        R01_REFERENCE_DIR / "MANIFEST.json",
        *[R01_REFERENCE_DIR / name for name in R01_HASHES],
        *sorted((BASE / "fonts").glob("*")),
    ]
    return [
        "missing R02 dependency lock " + str(p.relative_to(ROOT))
        for p in required
        if p.is_file() and str(p.relative_to(ROOT)) not in locks
    ]


def pdf_page_errors(page, r02=False):
    """Validate physical page geometry and actual embedded PDF text resources."""
    import fitz

    errors = []
    if r02:
        if not math.isclose(page.rect.width / page.rect.height, 3240 / 2304, abs_tol=1e-6):
            errors.append("R02 PDF page proportions differ from approved reference")
        fonts = page.get_fonts()
        if not fonts or any("DejaVuSans" not in f[3].replace(" ", "") for f in fonts):
            errors.append("R02 PDF uses missing/fallback font")
        for font in fonts:
            if not page.parent.extract_font(font[0])[3]:
                errors.append("R02 PDF font is not embedded")
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if not (page.rect + (-1, -1, 1, 1)).contains(fitz.Rect(span["bbox"])):
                    errors.append("text overflows page")
    return errors


def validate_artifacts(models, sources, manifest, render=True):
    errors = []
    maps = manifest.get("maps", [])
    mids = [m["id"] for m in maps]
    if len(mids) != len(set(mids)):
        errors.append("duplicate map IDs")
    locks = manifest.get("input_sha256", manifest.get("source_sha256", {}))
    if isinstance(locks, str):
        locks = {"geospatial/facilities/source/campus.json": locks}
    if manifest.get("design_revision") != "R02":
        errors.append("missing/current R02 design revision")
    errors.extend(r02_dependency_errors(locks))
    for p in sources:
        rel = str(p.relative_to(ROOT))
        if locks.get(rel) != sha(p):
            errors.append("stale/missing source digest " + rel)
    for rel, digest in locks.items():
        if not (ROOT / rel).is_file() or sha(ROOT / rel) != digest:
            errors.append("stale manifest input " + rel)
    if manifest.get("generator_sha256") != sha(BASE / "render.py"):
        errors.append("stale generator digest")
    expected = {}
    for s in models:
        for b in s["buildings"]:
            for f in b["floors"]:
                expected[f["id"]] = (s["site_id"], b["id"], f["status"])
    found = Counter(m.get("floor_id") for m in maps if m.get("kind") == "floor")
    if set(found) != set(expected):
        errors.append("missing/orphan floor artifacts " + str(set(expected) ^ set(found)))
    for fid, n in found.items():
        if n != 1:
            errors.append("duplicate floor map " + str(fid))
    for m in maps:
        if m.get("revision") != "R02":
            errors.append(m["id"] + ": missing/current R02 map revision")
        if not m.get("status"):
            errors.append(m["id"] + ": missing status")
        if m.get("kind") == "floor" and m.get("floor_id") in expected:
            if (m.get("site_id"), m.get("building_id"), m.get("status")) != expected[m["floor_id"]]:
                errors.append(m["id"] + ": floor parent/status mismatch")
        arts = m.get("artifacts", {})
        if set(arts) != {"svg", "png", "pdf"}:
            errors.append(m["id"] + ": missing SVG/PNG/PDF")
        for ext, a in arts.items():
            p = ROOT / a["path"]
            if not p.is_file():
                errors.append("missing artifact " + str(p))
                continue
            if sha(p) != a.get("sha256"):
                errors.append("stale artifact digest " + str(p))
            if not render:
                continue
            try:
                if ext == "svg":
                    svg = ET.parse(p).getroot()
                    if m.get("revision") == "R02" and svg.get("viewBox") != "0 0 3240 2304":
                        errors.append(str(p) + ": R02 SVG page dimensions differ")
                elif ext == "png":
                    from PIL import Image

                    with Image.open(p) as im:
                        if m.get("revision") == "R02" and im.size != (3240, 2304):
                            errors.append(str(p) + ": R02 PNG page dimensions differ")
                        im.verify()
                elif ext == "pdf":
                    import fitz

                    with fitz.open(p) as doc:
                        if not len(doc):
                            raise ValueError("empty PDF")
                        for page in doc:
                            page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
                            errors.extend(
                                str(p) + ": " + e
                                for e in pdf_page_errors(page, m.get("revision") == "R02")
                            )
            except Exception as exc:
                errors.append(str(p) + ": render/parse failure " + str(exc))
    return errors


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ["href", "src"]:
            if k in a:
                self.links.append(a[k])


def runtime_models():
    return json.loads(RUNTIME.read_text())["sites"] if RUNTIME.is_file() else []


def validate_runtime(data, coverage_ids, artifacts=True):
    """Accepted runtime drawings retain their own dimensions and provider boundaries."""
    errors = []
    sites = data.get("sites", [])
    ids = [s["site_id"] for s in sites]
    if set(ids) != {"SH-SITE-0028", "SH-SITE-0029", "SH-SITE-0030"} or len(ids) != 3:
        errors.append("runtime site census mismatch")
    maps = data.get("maps", [])
    mids = [m["id"] for m in maps]
    if len(mids) != 12 or len(set(mids)) != len(mids):
        errors.append("runtime map census mismatch")
    expected_floors = set()
    for site in sites:
        sid = site["site_id"]
        if sid not in coverage_ids:
            errors.append("runtime site lacks coverage disposition " + sid)
        for field in ["status", "geometry_status", "tenure"]:
            if not site.get(field):
                errors.append("runtime site missing " + field + " " + sid)
        if sid in {"SH-SITE-0028", "SH-SITE-0029"}:
            if site.get("buildings") or not site.get("floor_exemption"):
                errors.append("provider context must retain explicit floor exemption " + sid)
        for building in site.get("buildings", []):
            if not building.get("floors"):
                errors.append("runtime building lacks required floor " + building["id"])
            expected_floors.update(f["id"] for f in building.get("floors", []))
    floor_maps = Counter(m.get("floor_id") for m in maps if m.get("kind") == "floor")
    if set(floor_maps) != expected_floors or any(n != 1 for n in floor_maps.values()):
        errors.append("runtime missing/duplicate floor artifact")
    for m in maps:
        if not m.get("status") or m.get("site_id") not in ids:
            errors.append("runtime map lacks status/site " + m["id"])
        arts = m.get("artifacts", {})
        if set(arts) != {"svg", "png", "pdf"}:
            errors.append("runtime artifact formats incomplete " + m["id"])
        for ext, artifact in arts.items():
            path = ROOT / artifact["path"]
            if not path.is_file() or sha(path) != artifact.get("sha256"):
                errors.append("runtime artifact stale/missing " + artifact["path"])
            elif artifacts:
                try:
                    if ext == "svg":
                        ET.parse(path)
                    elif ext == "png":
                        from PIL import Image

                        with Image.open(path) as image:
                            image.verify()
                    elif ext == "pdf":
                        import fitz

                        with fitz.open(path) as doc:
                            if not len(doc):
                                raise ValueError("empty PDF")
                            for page in doc:
                                errors.extend(str(path) + ": " + e for e in pdf_page_errors(page))
                except Exception as exc:
                    errors.append("runtime artifact parse failure " + str(exc))
    locks = data.get("source_sha256", {})
    if not locks:
        errors.append("runtime missing accepted source provenance")
    for path, digest in locks.items():
        if not (ROOT / path).is_file() or sha(ROOT / path) != digest:
            errors.append("stale runtime source " + path)
    return errors


def validate_graph(data, models, coverage_records):
    """The hierarchy must be complete and reachable, not merely free of bad edges."""
    errors = []
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    edges = {(e["source"], e["target"]) for e in data.get("edges", [])}
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, set()).add(b)
    seen = set()
    pending = ["atlas"]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency.get(current, ()))
    expected = {"atlas"}
    for site in models:
        expected.add(site["site_id"])
        for building in site["buildings"]:
            expected.add(building["id"])
            if (site["site_id"], building["id"]) not in edges:
                errors.append("missing site/building atlas edge " + building["id"])
            for floor in building["floors"]:
                expected.add(floor["id"])
                if (building["id"], floor["id"]) not in edges:
                    errors.append("missing building/floor atlas edge " + floor["id"])
                maps = [
                    node
                    for node in adjacency.get(floor["id"], ())
                    if nodes.get(node, {}).get("kind") == "map"
                ]
                if not maps:
                    errors.append("floor lacks saved-map atlas edge " + floor["id"])
                for mid in maps:
                    formats = {
                        Path(nodes.get(a, {}).get("path", "")).suffix
                        for a in adjacency.get(mid, ())
                    }
                    if not {".svg", ".png", ".pdf"} <= formats:
                        errors.append("floor atlas lacks independent formats " + floor["id"])
    expected.update("coverage:" + r["id"] for r in coverage_records)
    if expected - nodes.keys():
        errors.append("missing expected atlas nodes " + str(sorted(expected - nodes.keys())))
    if expected - seen:
        errors.append("unreachable atlas nodes " + str(sorted(expected - seen)))
    listed = [r["coverage_id"] for r in data.get("coverage", [])]
    if len(listed) != len(set(listed)) or set(listed) != {r["id"] for r in coverage_records}:
        errors.append("atlas coverage census mismatch")
    locks = data.get("source_sha256", {})
    required = {
        "geospatial/facilities/coverage/COVERAGE_MATRIX.json",
        "geospatial/maps/facilities/MANIFEST.json",
        "geospatial/facilities/atlas.py",
    }
    required.update(str(p.relative_to(ROOT)) for p in (BASE / "source").glob("*.json"))
    if RUNTIME.is_file():
        required.add(str(RUNTIME.relative_to(ROOT)))
        required.update(json.loads(RUNTIME.read_text())["source_sha256"])
    if not required <= locks.keys():
        errors.append("atlas missing required source hashes")
    for path, digest in locks.items():
        if not (ROOT / path).is_file() or sha(ROOT / path) != digest:
            errors.append("stale atlas source " + path)
    return errors


def validate_atlas(required=False):
    errors = []
    index = ROOT / "geospatial/maps/index.html"
    graph = ROOT / "geospatial/maps/facilities/ATLAS_LINKS.json"
    for p in [index, graph]:
        if required and not p.is_file():
            errors.append("missing atlas deliverable " + str(p))
    if not index.exists():
        return errors
    queue = [index]
    seen = set()
    while queue:
        p = queue.pop()
        if p in seen:
            continue
        seen.add(p)
        parser = Links()
        parser.feed(p.read_text())
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (p.parent / unquote(parsed.path)).resolve() if parsed.path else p
            if not target.is_file():
                errors.append(f"{p}: broken link {link}")
                continue
            if target.suffix == ".html":
                other = Links()
                other.feed(target.read_text())
                queue.append(target)
                if parsed.fragment and unquote(parsed.fragment) not in other.ids:
                    errors.append(f"{p}: missing fragment {link}")
    if graph.exists():
        data = json.loads(graph.read_text())
        nodes = data.get("nodes", [])
        if isinstance(nodes, dict):
            node_ids = set(nodes)
        else:
            node_ids = {n["id"] for n in nodes}
        if len(node_ids) != len(nodes):
            errors.append("duplicate atlas node IDs")
        for edge in data.get("edges", []):
            if (
                edge.get("source", edge.get("from")) not in node_ids
                or edge.get("target", edge.get("to")) not in node_ids
            ):
                errors.append("orphan atlas edge " + str(edge))
        for path in data.get("paths", []):
            if not (ROOT / path.split("#")[0]).is_file():
                errors.append("missing atlas graph path " + path)
        if not nodes:
            errors.append("atlas graph has no nodes")
        models, _ = load_models()
        coverage = json.loads((BASE / "coverage/COVERAGE_MATRIX.json").read_text())
        errors.extend(validate_graph(data, models + runtime_models(), coverage["records"]))
        if data.get("pdf") and (ROOT / data["pdf"]).is_file():
            import fitz

            with fitz.open(ROOT / data["pdf"]) as doc:
                if len(doc) != data.get("pdf_pages"):
                    errors.append("portable atlas page-count mismatch")
                for page in doc:
                    for link in page.get_links():
                        if link.get("kind") == fitz.LINK_GOTO and not 0 <= link.get(
                            "page", -1
                        ) < len(doc):
                            errors.append("broken internal portable-PDF destination")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-atlas", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only validation; source hashes identify the build, not mutable HEAD",
    )
    args = parser.parse_args()
    models, sources = load_models()
    coverage = json.loads((BASE / "coverage/COVERAGE_MATRIX.json").read_text())
    errors = validate_models(models, {r["id"] for r in coverage["records"]})
    errors.extend(validate_r01_references())
    if RUNTIME.is_file():
        errors.extend(
            validate_runtime(
                json.loads(RUNTIME.read_text()),
                {r["id"] for r in coverage["records"]},
                not args.source_only,
            )
        )
    for script, extra in [
        ("coverage/validate_coverage.py", []),
        ("population/build.py", ["--check"]),
        ("program.py", ["--check"]),
    ]:
        result = subprocess.run(
            [sys.executable, str(BASE / script), *extra], capture_output=True, text=True
        )
        if result.returncode:
            errors.append(script + ": " + result.stdout + result.stderr)
    if not args.source_only:
        if not MANIFEST.is_file():
            errors.append("missing facility manifest")
        else:
            errors.extend(validate_artifacts(models, sources, json.loads(MANIFEST.read_text())))
        errors.extend(validate_atlas(args.require_atlas))
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"PASS facilities: {len(models)} sites, {sum(len(s['buildings']) for s in models)} buildings, {sum(len(b['floors']) for s in models for b in s['buildings'])} floors; source, coverage, population"
        + ("" if args.source_only else ", independent artifacts and atlas")
    )


if __name__ == "__main__":
    main()
