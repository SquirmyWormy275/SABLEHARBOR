"""Generate governed R02 facility sheets in the approved R01 drawing language."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from r01_drawing import floor, master, phasing, stacking

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/facilities"
OUT = ROOT / "geospatial/maps/facilities"
REF = ROOT / "docs/facilities/references/sacramento-hq/r01-approved"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_models():
    models = []
    for path in sorted((BASE / "source").glob("*.json")):
        data = json.loads(path.read_text())
        for model in data.get("sites", [data]):
            if "buildings" in model:
                model["source_path"] = str(path.relative_to(ROOT))
                models.append(model)
    return models


def build(only=None, output=None):
    models = load_models()
    out = output or OUT
    records = []
    register_path = ROOT / "geospatial/registers/MAP_ID_REGISTER.json"
    allocation = {
        r["logical_id"]: r["map_id"] for r in json.loads(register_path.read_text())["records"]
    }

    def render(key, model, fn, *args):
        mid = allocation[key]
        if only and only not in [key, mid, model["site_id"]]:
            return
        records.append(fn(model, *args, mid, out))

    for model in models:
        render(model["site_id"] + "::site", model, master)
        for building in model["buildings"]:
            render(building["id"] + "::building", model, stacking, building)
            for level in building["floors"]:
                render(level["id"], model, floor, building, level)
        if model.get("phases"):
            render(model["site_id"] + "::phasing", model, phasing)
    if only:
        print(f"{len(records)} review sheets saved to {out}; current manifest not replaced")
        return
    dependencies = [
        *sorted((BASE / "source").glob("*.json")),
        Path(__file__),
        BASE / "r01_drawing.py",
        register_path,
        *sorted((BASE / "fonts").glob("*")),
        REF / "MANIFEST.json",
        *sorted(REF.glob("*.png")),
    ]
    manifest = {
        "revision": "0.2.0",
        "design_revision": "R02",
        "approved_visual_reference": "SH-FAC-REF-SAC-R01",
        "base_commit": models[0]["authoritative_base"],
        "current_main_compatibility": "b83e4be2182a5e4143808a3dab5f8d929a133caf",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in dependencies if p.is_file()},
        "generator_sha256": sha(Path(__file__)),
        "maps": records,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"{len(models)} sites; {sum(len(m['buildings']) for m in models)} buildings; {sum(len(b['floors']) for m in models for b in m['buildings'])} floors; {len(records)} sheets / {len(records) * 3} individual files"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only", help="Stable map/logical/site ID for review; does not replace current manifest"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.only, args.output)
