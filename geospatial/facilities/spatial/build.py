"""Build/check coordinated spatial derivatives and the offline drill-down viewer."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "geospatial/facilities/spatial"
sys.path.insert(0, str(BASE))
from model import build_model, validate  # noqa: E402
from access import build_access  # noqa: E402
from context import build_context  # noqa: E402


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def encoded(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build(check=False, render=False):
    model = build_model(ROOT)
    access = build_access(ROOT)
    context = build_context(ROOT)
    from compare import build_comparison

    comparison = build_comparison(ROOT)
    sources = {**model["source_sha256"], **access["source_sha256"], **context["source_sha256"]}
    for p in sorted(BASE.rglob("*")):
        if (
            p.is_file()
            and (p.suffix in (".py", ".js", ".html") or p.name == "ACCESS_POLICY.json")
            and not p.name.startswith("test_")
        ):
            sources[str(p.relative_to(ROOT))] = sha(p)
    for p in (ROOT / "geospatial/facilities/fonts").glob("*"):
        if p.is_file():
            sources[str(p.relative_to(ROOT))] = sha(p)
    sources["geospatial/facilities/r01_drawing.py"] = sha(
        ROOT / "geospatial/facilities/r01_drawing.py"
    )
    path = ROOT / "geospatial/maps/spatial/MANIFEST.json"
    if render:
        import render as renderer

        manifest = renderer.build(ROOT)
        from context_sheet import render_context

        reg = json.loads((ROOT / "geospatial/registers/MAP_ID_REGISTER.json").read_text())
        mid = next(
            r["map_id"]
            for r in reg["records"]
            if r["logical_id"] == "SH-SITE-0001::enhanced-context"
        )
        manifest["maps"].append(render_context(ROOT, context, mid))
    else:
        manifest = json.loads(path.read_text()) if path.exists() else {"maps": []}
    manifest["sheet_count"] = len(manifest["maps"])
    if render:
        from publication import compile_pdf

        pdf = compile_pdf(ROOT, manifest["maps"])
        manifest["portable_pdf"] = {"path": str(pdf.relative_to(ROOT)), "sha256": sha(pdf)}
    manifest.update(
        revision="1.0.0",
        source_sha256=sources,
        status="MODELLED_SPATIAL_ADDENDUM_WITH_SEPARATE_REAL_CONTEXT",
    )
    data = {
        **model,
        "source_sha256": sources,
        "context": context,
        "access": access,
        "comparisons": comparison["comparisons"],
        "maps": manifest["maps"],
    }
    html = (
        (BASE / "viewer.html")
        .read_text()
        .replace("__SPATIAL_DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__SPATIAL_APP__", (BASE / "viewer.js").read_text())
    )
    ids = []
    for site in model["sites"]:
        ids.append(site["id"])
        for building in site["buildings"]:
            ids.append(building["id"])
            ids.extend(f["id"] for f in building["floors"])
    html = html.replace(
        "</body>",
        '<div hidden aria-hidden="true">'
        + "".join(f'<span id="{identifier}"></span>' for identifier in ids)
        + "</div></body>",
    )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(model["room_schedule"][0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(model["room_schedule"])
    outputs = {
        BASE / "MODEL.json": encoded(model),
        BASE / "ACCESS.json": encoded(access),
        BASE / "CONTEXT.json": encoded(context),
        BASE / "COMPARISON.json": encoded(comparison),
        BASE / "ROOM_SCHEDULE.csv": buf.getvalue(),
        ROOT / "geospatial/maps/spatial.html": html,
        path: encoded(manifest),
    }
    index = [
        "# Spatial architectural addendum",
        "",
        "[Portable bookmarked PDF](../SABLE_HARBOR_Spatial_Addendum_v1.0.0.pdf) · [Offline 3D review](../spatial.html) · [Enterprise atlas](../index.html) · [Room schedule](../../facilities/spatial/ROOM_SCHEDULE.csv)",
        "",
        "Concept studies use accepted floor geometry. Sections, elevations and roof arrangements are design assumptions, not construction records. Real regional context does not place the campus.",
        "",
    ]
    for m in manifest["maps"]:
        index += [
            "## " + m["title"],
            "",
            m.get("floor_id") or m.get("building_id") or m["site_id"],
            "",
            " · ".join(
                f"[{ext.upper()}]({Path(a['path']).name})" for ext, a in m["artifacts"].items()
            ),
            "",
        ]
    outputs[path.parent / "README.md"] = "\n".join(index) + "\n"
    stale = []
    for p, value in outputs.items():
        if check:
            if not p.exists() or p.read_text() != value:
                stale.append(str(p.relative_to(ROOT)))
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value)
    if stale:
        raise ValueError("Stale spatial outputs: " + ", ".join(stale))
    if manifest["maps"]:
        validate_package(data, manifest)
    elif check:
        raise ValueError("Missing spatial sheets")
    print(
        f"PASS spatial {'freshness' if check else 'build'}: {len(model['sites'])} sites, {len(model['room_schedule'])} room records, {len(manifest['maps'])} sheets"
    )
    return data


def validate_package(data, manifest):
    validate(data)
    seen = set()
    keys = {m["logical_id"] for m in manifest["maps"]}
    for s in data["sites"]:
        for b in s["buildings"]:
            for k in ["sections", "elevations", "roof"]:
                if b["id"] + "::" + k not in keys:
                    raise ValueError("Missing building " + k)
            for f in b["floors"]:
                if f["id"] + "::schedule" not in keys:
                    raise ValueError("Missing room schedule")
                for target in f["links"].values():
                    if not (ROOT / "geospatial/maps" / unquote(urlsplit(target).path)).is_file():
                        raise ValueError("Broken floor link " + target)
    for m in manifest["maps"]:
        mid = m.get("map_id", m.get("id"))
        if mid in seen:
            raise ValueError("Duplicate map ID")
        seen.add(mid)
        if set(m["artifacts"]) != {"svg", "png", "pdf"}:
            raise ValueError("Missing format")
        for a in m["artifacts"].values():
            p = ROOT / a["path"]
            if not p.exists() or sha(p) != a["sha256"]:
                raise ValueError("Missing/stale artifact " + str(p))
    if manifest.get("portable_pdf"):
        a = manifest["portable_pdf"]
        if sha(ROOT / a["path"]) != a["sha256"]:
            raise ValueError("Stale portable spatial PDF")
    for r in data["access"]["routes"]:
        if r["floor_id"] + "::access" not in keys:
            raise ValueError("Missing access overlay")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    if args.check and args.render:
        parser.error("--check and --render are mutually exclusive")
    build(args.check, args.render)
