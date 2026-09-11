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
COUNTS = (
    "assigned_desks",
    "shared_desks",
    "touchdown_seats",
    "training_seats",
    "meeting_seats",
    "resident_beds",
)
STATUSES = {
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


def validate_artifacts(models, sources, manifest, render=True):
    errors = []
    maps = manifest.get("maps", [])
    mids = [m["id"] for m in maps]
    if len(mids) != len(set(mids)):
        errors.append("duplicate map IDs")
    locks = manifest.get("input_sha256", manifest.get("source_sha256", {}))
    if isinstance(locks, str):
        locks = {"geospatial/facilities/source/campus.json": locks}
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
                    ET.parse(p)
                elif ext == "png":
                    from PIL import Image

                    with Image.open(p) as im:
                        im.verify()
                elif ext == "pdf":
                    import fitz

                    with fitz.open(p) as doc:
                        if not len(doc):
                            raise ValueError("empty PDF")
                        for page in doc:
                            page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
                            for block in page.get_text("dict")["blocks"]:
                                for line in block.get("lines", []):
                                    for span in line["spans"]:
                                        if not (page.rect + (-1, -1, 1, 1)).contains(
                                            fitz.Rect(span["bbox"])
                                        ):
                                            errors.append(str(p) + ": text overflows page")
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
        errors.extend(validate_graph(data, models, coverage["records"]))
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
    for script, extra in [
        ("coverage/validate_coverage.py", []),
        ("population/build.py", ["--check"]),
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
