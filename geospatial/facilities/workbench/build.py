"""Build an offline facility decision workbench from the accepted planning model."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "geospatial/facilities/workbench"
sys.path.insert(0, str(BASE))
from scenario import baseline, evaluate  # noqa: E402
from impact import dependency_graph, impact, stale_sources  # noqa: E402
from readiness import build_readiness  # noqa: E402
from evidence import build_evidence_queue, submission_template  # noqa: E402


def load_data(root=ROOT):
    register = json.loads((root / "geospatial/facilities/SPACE_REGISTER.json").read_text())
    campus = json.loads((root / "geospatial/facilities/source/campus.json").read_text())
    graph = dependency_graph(root)
    sites = {s["id"]: s["name"] for s in register["sites"] + register["linked_runtime_sites"]}
    names = {}
    for p in sorted((root / "geospatial/facilities/source").glob("*.json")):
        source = json.loads(p.read_text())
        for site in source.get("sites", [source]):
            for b in site.get("buildings", []):
                for f in b["floors"]:
                    names[f["id"]] = b["name"] + " / " + f["name"]
    event = campus["attendance_scenarios"][0]
    training_floor_id = "SH-SITE-0001-C-L01"
    floors = []
    for f in register["floors"] + register["linked_runtime_floors"]:
        unknown = f["assigned_desks"] is None
        defaults = {
            "assigned_workers": f["assigned_desks"],
            "shared_workers": f["shared_desks"],
            "attendance_percent": None if unknown else 100,
            "sharing_ratio": None if unknown else 1,
            "touchdown_visitors": f["touchdown_seats"],
            "other_attendees": None
            if unknown
            else max(
                0,
                event["floor_populations"].get(f["id"], 0)
                - sum(f[k] for k in ("assigned_desks", "shared_desks", "touchdown_seats"))
                - (event["trainees"] if f["id"] == training_floor_id else 0),
            ),
        }
        floors.append(
            {
                "id": f["id"],
                "building_id": f["building_id"],
                "site_id": f["site_id"],
                "site_name": sites[f["site_id"]],
                "name": names.get(f["id"], f.get("name", f["id"])),
                "assigned_desks": f["assigned_desks"],
                "shared_desks": f["shared_desks"],
                "touchdown_seats": f["touchdown_seats"],
                "training_seats": f["training_seats"],
                "resident_capacity": f["resident_beds"],
                "planned_peak": f["planned_peak"],
                "defaults": defaults,
            }
        )
    event = campus["attendance_scenarios"][0]
    night = campus["attendance_scenarios"][1]
    data = {
        "revision": "1.0.0",
        "authority": "PLANNING_EXPERIMENTS_ONLY",
        "source_sha256": graph["source_sha256"],
        "floors": floors,
        "campus": {
            "site_id": campus["site_id"],
            "trainee_peak": event["trainees"],
            "resident_capacity": night["people"],
            "training_floor_id": training_floor_id,
            "default_resident_trainees": event["resident_trainees_subset"],
        },
    }
    return data, graph


def build(check=False):
    data, graph = load_data()
    readiness = build_readiness(ROOT)
    evidence = build_evidence_queue(ROOT)
    ui = {
        **data,
        "readiness": readiness,
        "evidence": evidence,
        "evidence_template": submission_template(ROOT),
        "impacts": [
            {
                "source_path": source,
                "sha256": graph["source_sha256"].get(source),
                "artifacts": impact(graph, [source])["affected_artifacts"],
                "commands": impact(graph, [source])["commands"],
                "reason": graph["basis"],
            }
            for source in graph["edges"]
        ],
    }
    payload = (
        json.dumps(ui, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    template = (BASE / "template.html").read_text()
    app = (BASE / "app.js").read_text()
    html = template.replace("__WORKBENCH_DATA__", payload).replace("__WORKBENCH_APP__", app)
    files = {
        BASE / "BASELINE.json": data,
        BASE / "DEPENDENCIES.json": graph,
        BASE / "READINESS.json": readiness,
        BASE / "EVIDENCE_QUEUE.json": evidence,
        BASE / "BASELINE_SCENARIO.json": baseline(data),
        BASE / "BASELINE_RESULT.json": evaluate(data, baseline(data)),
    }
    outputs = {p: json.dumps(d, indent=2, ensure_ascii=False) + "\n" for p, d in files.items()}
    outputs[ROOT / "geospatial/maps/workbench.html"] = html
    manifest = {
        "revision": "1.0.0",
        "source_sha256": data["source_sha256"],
        "outputs": {
            str(p.relative_to(ROOT)): hashlib.sha256(s.encode()).hexdigest()
            for p, s in outputs.items()
        },
    }
    outputs[BASE / "MANIFEST.json"] = json.dumps(manifest, indent=2) + "\n"
    stale = []
    for path, text in outputs.items():
        if check:
            if not path.is_file() or path.read_text() != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(text)
    if stale:
        raise ValueError("Stale workbench outputs: " + ", ".join(stale))
    print(
        f"PASS workbench {'freshness' if check else 'build'}: {len(data['floors'])} floors; {len(outputs)} outputs"
    )


def export_result(path, result):
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError(
            "Experiment outputs must be new files outside the repository; no source overwrite."
        )
    with path.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    b = sub.add_parser("build")
    b.add_argument("--check", action="store_true")
    s = sub.add_parser("scenario")
    s.add_argument("input", type=Path)
    s.add_argument("--output", type=Path, required=True)
    i = sub.add_parser("impact")
    i.add_argument("--changed", action="append", default=[])
    i.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command in (None, "build"):
        build(getattr(args, "check", False))
        return
    data, graph = load_data()
    if args.command == "scenario":
        result = evaluate(data, json.loads(args.input.read_text()))
        export_result(args.output, result)
        if result["status"] == "INVALID":
            raise SystemExit(2)
    else:
        committed = json.loads((BASE / "DEPENDENCIES.json").read_text())
        changed = sorted(set(args.changed + stale_sources(ROOT, committed)))
        result = impact(committed, changed)
        export_result(args.output, result)
    print(
        json.dumps({"status": result.get("status", "IMPACT_REPORTED"), "output": str(args.output)})
    )


if __name__ == "__main__":
    main()
