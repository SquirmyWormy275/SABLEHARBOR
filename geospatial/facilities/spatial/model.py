"""Normalize accepted floor geometry once for coordinated architectural derivatives."""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "geospatial/facilities/spatial"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_file(path):
    return json.loads(path.read_text())


def build_model(root=ROOT):
    root = Path(root)
    assumptions = json_file(root / "geospatial/facilities/spatial/ARCHITECTURAL_ASSUMPTIONS.json")
    sources = {}
    sites = []
    for path in sorted((root / "geospatial/facilities/source").glob("*.json")):
        sources[str(path.relative_to(root))] = sha(path)
        data = json_file(path)
        for site in data.get("sites", [data]):
            if "buildings" in site:
                sites.append((site, str(path.relative_to(root)), False))
    runtime = root / "geospatial/facilities/RUNTIME_BRIDGE.json"
    sources[str(runtime.relative_to(root))] = sha(runtime)
    for site in json_file(runtime)["sites"]:
        sites.append((site, str(runtime.relative_to(root)), True))
    allocation = json_file(root / "geospatial/registers/MAP_ID_REGISTER.json")
    ids = {r["logical_id"]: r["map_id"] for r in allocation["records"]}
    sources["geospatial/registers/MAP_ID_REGISTER.json"] = sha(
        root / "geospatial/registers/MAP_ID_REGISTER.json"
    )
    source_maps = (
        json_file(root / "geospatial/maps/facilities/MANIFEST.json")["maps"]
        + json_file(runtime)["maps"]
    )
    floors_to_maps = {
        m["floor_id"]: m for m in source_maps if m.get("floor_id") and m.get("kind") == "floor"
    }
    output = []
    schedule = []

    def links(scope, types):
        return {
            kind: "spatial/" + ids[scope + "::" + kind] + ".svg"
            for kind in types
            if scope + "::" + kind in ids
        }

    for raw, path, is_runtime in sites:
        s = {
            "id": raw["site_id"],
            "name": raw["name"],
            "status": raw["status"],
            "source": path,
            "geometry_status": raw.get("geometry_status"),
            "geometry_basis": raw.get("geometry_basis"),
            "fictionality": raw.get("fictionality"),
            "georeferenced": False,
            "geographic_transform": None,
            "envelope_m": raw.get("envelope_m"),
            "access": copy.deepcopy(raw.get("access", {})),
            "site_zones": copy.deepcopy(raw.get("site_zones", [])),
            "buildings": [],
        }
        if not raw["buildings"]:
            s["exemption"] = raw.get(
                "floor_exemption",
                "No occupied/modelled building established by source; context only.",
            )
            s["envelope_m"] = s["envelope_m"] or [100, 100]
        for b in raw["buildings"]:
            rect = b.get("rect_m")
            if rect is None:
                w, d = b["footprint_ft"]
                rect = [0, 0, w * 0.3048, d * 0.3048]
                s["envelope_m"] = [rect[2], rect[3]]
                s["geometry_basis"] = (
                    "Owned-building footprint frame only; position on the synthetic parcel is not inferred."
                )
            height = b.get("floor_height_m", assumptions["runtime_owned_floor_height_m"])
            explicit_height = "floor_height_m" in b
            material = assumptions["materials"][
                "institutional" if b.get("layout_style") == "r01" else "industrial"
            ]
            building = {
                "id": b["id"],
                "name": b["name"],
                "status": b["status"],
                "rect_m": rect,
                "floor_height_m": height,
                "height_m": len(b["floors"]) * height,
                "height_basis": "Source floor_height_m; still a modelled concept."
                if explicit_height
                else assumptions["runtime_owned_height_basis"],
                "parapet_m": assumptions["parapet_height_m"],
                "material": material,
                "geometry_role": "architectural_concept"
                if b.get("layout_style") == "r01"
                else "program_envelope",
                "links": links(b["id"], ["sections", "elevations", "roof"]),
                "floors": [],
            }
            for index, f in enumerate(b["floors"]):
                floor = {
                    "id": f["id"],
                    "name": f["name"],
                    "level": f.get("level", index + 1),
                    "z_m": index * height,
                    "height_m": height,
                    "status": f["status"],
                    "gross_area_m2": f["gross_area_m2"],
                    "planned_peak": f.get("planned_peak"),
                    "cores": copy.deepcopy(f.get("core_zones", b.get("core_zones", []))),
                    "circulation": copy.deepcopy(f.get("circulation_zones", [])),
                    "rooms": [],
                    "links": links(f["id"], ["schedule"]),
                }
                for key in ("doors", "exterior_doors", "core_doors"):
                    if key in f:
                        floor[key] = copy.deepcopy(f[key])
                for room in f["rooms"]:
                    r = copy.deepcopy(room)
                    if "rect_m" not in r:
                        r["rect_m"] = [r[k] * 0.3048 for k in ("x", "y", "width", "height")]
                    r["geometry_role"] = (
                        "partitioned_room" if b.get("layout_style") == "r01" else "program_zone"
                    )
                    r["access"] = r.get("access", "UNESTABLISHED")
                    r["kind"] = r.get("kind", "program zone")
                    r["area_m2"] = r["rect_m"][2] * r["rect_m"][3]
                    r["site_id"] = s["id"]
                    r["building_id"] = b["id"]
                    r["floor_id"] = f["id"]
                    floor["rooms"].append(r)
                    schedule.append(
                        {
                            "site_id": s["id"],
                            "building_id": b["id"],
                            "floor_id": f["id"],
                            "room_id": r["id"],
                            "name": r["name"],
                            "area_m2": r["area_m2"],
                            "access": r["access"],
                            "geometry_role": r["geometry_role"],
                            **{
                                k: r.get(k)
                                for k in (
                                    "assigned_desks",
                                    "shared_desks",
                                    "touchdown_seats",
                                    "training_seats",
                                    "meeting_seats",
                                    "dining_seats",
                                    "resident_beds",
                                    "special_use_capacity",
                                )
                            },
                            "source": path,
                        }
                    )
                m = floors_to_maps.get(f["id"])
                if m:
                    for ext, a in m["artifacts"].items():
                        from os.path import relpath

                        floor["links"][ext] = relpath(root / a["path"], root / "geospatial/maps")
                floor["links"]["atlas"] = "index.html#" + f["id"]
                building["floors"].append(floor)
            s["buildings"].append(building)
        output.append(s)
    sources["geospatial/facilities/spatial/ARCHITECTURAL_ASSUMPTIONS.json"] = sha(
        root / "geospatial/facilities/spatial/ARCHITECTURAL_ASSUMPTIONS.json"
    )
    data = {
        "revision": "1.0.0",
        "status": "COORDINATED_MODELLED_STUDY_NOT_AS_BUILT",
        "as_of": "2026-09-11",
        "source_sha256": sources,
        "assumptions": assumptions,
        "sites": output,
        "room_schedule": schedule,
    }
    validate(data)
    return data


def validate(model):
    import math

    ids = []
    for s in model["sites"]:
        ids.append(s["id"])
        for b in s["buildings"]:
            ids.append(b["id"])
            x, y, w, d = b["rect_m"]
            if w <= 0 or d <= 0 or b["height_m"] <= 0:
                raise ValueError("Invalid envelope")
            if not math.isclose(b["height_m"], sum(f["height_m"] for f in b["floors"])):
                raise ValueError("Stack mismatch")
            z = 0
            for f in b["floors"]:
                ids.append(f["id"])
                if not math.isclose(f["z_m"], z):
                    raise ValueError("Noncontiguous floor stack")
                if not math.isclose(w * d, f["gross_area_m2"], abs_tol=0.02):
                    raise ValueError("Floorplate area mismatch")
                z += f["height_m"]
                for r in f["rooms"]:
                    ids.append(r["id"])
                    rx, ry, rw, rd = r["rect_m"]
                    if (
                        min(rx, ry) < -1e-5
                        or min(rw, rd) <= 0
                        or rx + rw > w + 1e-5
                        or ry + rd > d + 1e-5
                    ):
                        raise ValueError("Room outside envelope: " + r["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate spatial ID")
    return True


if __name__ == "__main__":
    (BASE / "MODEL.json").write_text(json.dumps(build_model(), indent=2) + "\n")
