"""Stable-ID source-model differences and review overlays; no canonical writes."""

from __future__ import annotations

import argparse
import copy
import hashlib
from html import escape
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

BASELINE = "ff5cd67ff980790413f7bfbf0829b47d20d266a3"
SEATS = {
    "assigned_desks",
    "shared_desks",
    "touchdown_seats",
    "training_seats",
    "meeting_seats",
    "dining_seats",
    "resident_beds",
    "planned_peak",
}
IGNORED = {
    "id",
    "site_id",
    "building_id",
    "floor_id",
    "links",
    "source",
    "buildings",
    "floors",
    "rooms",
}


def flatten(model: dict) -> dict:
    records = {}

    def add(row, scope, site_id, building_id=None, floor_id=None, inherited=None):
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"missing stable {scope} ID")
        if identifier in records:
            raise ValueError(f"duplicate stable ID: {identifier}")
        links = {**(inherited or {}), **row.get("links", {})}
        records[identifier] = {
            "scope": scope,
            "row": row,
            "site_id": site_id,
            "building_id": building_id,
            "floor_id": floor_id,
            "links": links,
        }
        return links

    for site in model["sites"]:
        sid = site.get("id")
        sl = add(site, "site", sid)
        for building in site.get("buildings", []):
            bid = building.get("id")
            bl = add(building, "building", sid, bid, inherited=sl)
            for floor in building.get("floors", []):
                fid = floor.get("id")
                fl = add(floor, "floor", sid, bid, fid, inherited=bl)
                for room in floor.get("rooms", []):
                    add(room, "room", sid, bid, fid, fl)
    return records


def category(field: str) -> str:
    if field in SEATS:
        return "capacity"
    if field in {"height_m", "floor_height_m", "z_m", "parapet_m", "height_basis"}:
        return "height"
    if field in {
        "access",
        "doors",
        "exterior_doors",
        "core_doors",
        "circulation",
        "cores",
        "site_zones",
    }:
        return "access"
    if field in {
        "rect_m",
        "geometry",
        "envelope_m",
        "gross_area_m2",
        "area_m2",
        "geometry_role",
        "geographic_transform",
        "georeferenced",
        "geometry_status",
        "geometry_basis",
    }:
        return "geometry"
    if field in {"name", "status"}:
        return field
    return "attribute"


def compare_models(before: dict, after: dict) -> dict:
    old, new = flatten(before), flatten(after)
    site_ids = sorted({r["site_id"] for r in list(old.values()) + list(new.values())})
    comparisons = []
    for sid in site_ids:
        site = (new.get(sid) or old[sid])["row"]
        changes = []
        affected_floors = set()
        for identifier in sorted(set(old) | set(new)):
            a, b = old.get(identifier), new.get(identifier)
            if sid not in {r["site_id"] for r in (a, b) if r}:
                continue
            representative = b or a
            links = sorted(
                set((a or {}).get("links", {}).values()) | set((b or {}).get("links", {}).values())
            )
            if representative["scope"] in {"site", "building"}:
                for child in list(old.values()) + list(new.values()):
                    if child["site_id"] == sid and (
                        representative["scope"] == "site"
                        or child["building_id"] == representative["building_id"]
                    ):
                        links.extend(child["links"].values())
                links = sorted(set(links))
            differences = []
            if a is None or b is None:
                differences = [
                    (
                        "__added__" if a is None else "__removed__",
                        None if a is None else a["row"],
                        None if b is None else b["row"],
                    )
                ]
            else:
                for field in sorted((set(a["row"]) | set(b["row"])) - IGNORED):
                    if a["row"].get(field) != b["row"].get(field):
                        differences.append((field, a["row"].get(field), b["row"].get(field)))
                for field in ("site_id", "building_id", "floor_id"):
                    if a[field] != b[field]:
                        differences.append((field, a[field], b[field]))
            for field, previous, current in differences:
                changes.append(
                    {
                        "scope": representative["scope"],
                        "id": identifier,
                        "field": field,
                        "category": "add_remove" if field.startswith("__") else category(field),
                        "before": copy.deepcopy(previous),
                        "after": copy.deepcopy(current),
                        "affected_maps": links,
                    }
                )
                for r in (a, b):
                    if not r:
                        continue
                    if r["floor_id"]:
                        affected_floors.add(r["floor_id"])
                    elif r["scope"] in {"site", "building"}:
                        affected_floors.update(
                            x["floor_id"]
                            for x in list(old.values()) + list(new.values())
                            if x["floor_id"]
                            and x["site_id"] == sid
                            and (r["scope"] == "site" or x["building_id"] == r["building_id"])
                        )
        overlays = []
        for fid in sorted(affected_floors):
            a, b = old.get(fid), new.get(fid)
            overlays.append(
                {
                    "floor_id": fid,
                    "before_rooms": copy.deepcopy(a["row"].get("rooms", []) if a else []),
                    "after_rooms": copy.deepcopy(b["row"].get("rooms", []) if b else []),
                    "before_floor": copy.deepcopy(a["row"] if a else None),
                    "after_floor": copy.deepcopy(b["row"] if b else None),
                    "links": {
                        "before": (a or {}).get("links", {}),
                        "after": (b or {}).get("links", {}),
                    },
                }
            )
        comparisons.append(
            {
                "site_id": sid,
                "title": site.get("name", sid),
                "before_revision": before.get("revision", "UNSPECIFIED"),
                "after_revision": after.get("revision", "UNSPECIFIED"),
                "changes": changes,
                "overlays": overlays,
            }
        )
    return {
        "schema_version": "1.0.0",
        "state": "COMPARISON_NOT_CANON",
        "comparisons": comparisons,
        "summary": {
            "sites": len(comparisons),
            "changed_sites": sum(bool(c["changes"]) for c in comparisons),
            "changes": sum(len(c["changes"]) for c in comparisons),
            "affected_floors": sum(len(c["overlays"]) for c in comparisons),
        },
        "source_sha256": {
            "before": before.get("source_sha256", {}),
            "after": after.get("source_sha256", {}),
        },
    }


def build_comparison(root: Path) -> dict:
    root = Path(root).resolve()
    spec = importlib.util.spec_from_file_location(
        "comparison_spatial_model", root / "geospatial/facilities/spatial/model.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = module.build_model(root)
    paths = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            BASELINE,
            "geospatial/facilities/source",
            "geospatial/facilities/RUNTIME_BRIDGE.json",
            "geospatial/registers/MAP_ID_REGISTER.json",
            "geospatial/maps/facilities/MANIFEST.json",
        ],
        text=True,
    ).splitlines()
    if not paths or "geospatial/facilities/source/campus.json" not in paths:
        raise ValueError("accepted comparison baseline unavailable")
    baseline_hashes = {}
    equal_source_paths = []
    with tempfile.TemporaryDirectory(prefix="sable-comparison-") as temp:
        historical = Path(temp)
        for path in paths:
            raw = subprocess.check_output(["git", "-C", str(root), "show", f"{BASELINE}:{path}"])
            target = historical / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            baseline_hashes[path] = hashlib.sha256(raw).hexdigest()
            if (root / path).exists() and (root / path).read_bytes() == raw:
                equal_source_paths.append(path)
        assumption_path = "geospatial/facilities/spatial/ARCHITECTURAL_ASSUMPTIONS.json"
        target = historical / assumption_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / assumption_path).read_bytes())
        previous = module.build_model(historical)
    previous["revision"] = BASELINE
    current["revision"] = current.get("revision", "current")
    result = compare_models(previous, current)
    result["baseline_evidence"] = {
        "accepted_commit": BASELINE,
        "git_blob_sha256": baseline_hashes,
        "byte_identical_paths": equal_source_paths,
        "normalization": "Baseline source files actually read with git show into an isolated temporary tree. Current normalization assumptions applied to both models for comparable geometry; these are not historical approvals.",
        "baseline_floor_geometry_equal": not any(
            change["category"] in {"geometry", "add_remove"}
            for c in result["comparisons"]
            for change in c["changes"]
        ),
    }
    result["informational"] = [
        {
            "kind": "NEW_ARCHITECTURAL_ASSUMPTIONS",
            "source": assumption_path,
            "sha256": hashlib.sha256((root / assumption_path).read_bytes()).hexdigest(),
            "meaning": "Vertical/material/roof assumptions are new spatial study inputs, not accepted ff5cd67 floor geometry or evidence of construction. Identical assumptions normalize both comparison sides; no historical height approval is claimed.",
        }
    ]
    return result


def overlay_svg(overlay: dict) -> str:
    rooms = overlay["before_rooms"] + overlay["after_rooms"]
    width = max((r["rect_m"][0] + r["rect_m"][2] for r in rooms), default=1)
    depth = max((r["rect_m"][1] + r["rect_m"][3] for r in rooms), default=1)
    scale = min(1080 / max(width, 1), 680 / max(depth, 1))
    parts = []
    for key, color, dash in [("before_rooms", "#b34e48", "7 4"), ("after_rooms", "#245c87", "")]:
        for room in overlay[key]:
            x, y, w, d = room["rect_m"]
            parts.append(
                f'<rect x="{50 + x * scale:.3f}" y="{100 + (depth - y - d) * scale:.3f}" width="{w * scale:.3f}" height="{d * scale:.3f}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>'
            )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900"><rect width="1200" height="900" fill="#f6f5f0"/><g font-family="sans-serif" fill="#213740"><text x="50" y="42" font-size="24">'
        + escape(overlay["floor_id"])
        + ' / REVISION OVERLAY</text><text x="50" y="72" font-size="16">Red dashed: before · Blue solid: after · Local model metres · Not survey or construction approval</text>'
        + "".join(parts)
        + '<text x="50" y="855" font-size="16">Read the companion change register for name, access, status, height and capacity changes.</text></g></svg>\n'
    )


def export_overlays(comparison: dict, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for site in comparison["comparisons"]:
        for overlay in site["overlays"]:
            fid = overlay["floor_id"]
            if not re.fullmatch("[A-Za-z0-9_-]+", fid):
                raise ValueError("unsafe floor ID for filename")
            path = output_dir / (fid + "-revision-overlay.svg")
            with path.open("x") as handle:
                handle.write(overlay_svg(overlay))
            files.append(str(path))
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if bool(args.before) != bool(args.after):
        parser.error("--before and --after must be supplied together")
    data = (
        compare_models(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
        if args.before
        else build_comparison(args.root)
    )
    # Exports are review derivatives only; prevent CLI writes into the source repository.
    for destination in [args.output, args.output_dir]:
        if destination and destination.resolve().is_relative_to(args.root.resolve()):
            parser.error("export destination must be outside repository")
    if args.output_dir:
        data["exported_overlays"] = export_overlays(data, args.output_dir)
    text = json.dumps(data, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x") as handle:
            handle.write(text)
    else:
        print(text, end="")
