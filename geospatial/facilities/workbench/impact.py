"""Conservative dependency traversal from committed source and publication manifests."""

import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_graph(root):
    root = Path(root)
    edges = {}
    hashes = {}
    generators = {}

    def connect(source, outputs, command):
        edges.setdefault(source, set()).update(outputs)
        for output in outputs:
            generators.setdefault(output, set()).add(command)
        path = root / source
        if path.is_file():
            hashes[source] = digest(path)

    facilities = "geospatial/facilities/"
    maps = json.loads((root / "geospatial/maps/facilities/MANIFEST.json").read_text())
    runtime = json.loads((root / (facilities + "RUNTIME_BRIDGE.json")).read_text())
    atlas = json.loads((root / "geospatial/maps/facilities/ATLAS_LINKS.json").read_text())
    outputs = [a["path"] for m in maps["maps"] for a in m["artifacts"].values()]
    for source in [*maps["source_sha256"], facilities + "render.py", facilities + "r01_drawing.py"]:
        connect(
            source,
            outputs + ["geospatial/maps/facilities/MANIFEST.json"],
            "python geospatial/facilities/render.py",
        )
    for source in runtime["source_sha256"]:
        connect(
            source,
            [facilities + "RUNTIME_BRIDGE.json"],
            "python geospatial/facilities/runtime_bridge.py",
        )
    coverage = json.loads((root / (facilities + "coverage/COVERAGE_MATRIX.json")).read_text())
    for source in coverage["input_sha256"]:
        connect(
            source,
            [
                facilities + "coverage/COVERAGE_MATRIX.json",
                facilities + "coverage/COVERAGE_MATRIX.md",
            ],
            "python geospatial/facilities/coverage/build_coverage.py",
        )
    policy = json.loads((root / (facilities + "population/policy.json")).read_text())
    for source in [
        *policy["sources"].values(),
        facilities + "population/policy.json",
        facilities + "population/build.py",
    ]:
        connect(
            source,
            [
                facilities + "population/REGISTER.json",
                facilities + "population/BRIDGE.md",
                facilities + "population/DISCREPANCY_REPORT.json",
            ],
            "python geospatial/facilities/population/build.py",
        )
    for source in [
        facilities + "program.py",
        facilities + "population/REGISTER.json",
        facilities + "RUNTIME_BRIDGE.json",
        "enterprise/business/source/policy.json",
        *[p.relative_to(root).as_posix() for p in (root / (facilities + "source")).glob("*.json")],
    ]:
        connect(
            source,
            [facilities + "SPACE_REGISTER.json", facilities + "PROGRAM.md"],
            "python geospatial/facilities/program.py",
        )
    for source in [
        "geospatial/maps/facilities/MANIFEST.json",
        facilities + "RUNTIME_BRIDGE.json",
        facilities + "integrate_manifest.py",
    ]:
        connect(
            source,
            ["geospatial/maps/MAP_MANIFEST.json"],
            "python geospatial/facilities/integrate_manifest.py",
        )
    atlas_outputs = [
        "geospatial/maps/index.html",
        "geospatial/maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf",
        "geospatial/maps/facilities/ATLAS_LINKS.json",
        "geospatial/maps/facilities/ARTIFACT_INDEX.md",
    ]
    for source in [
        *atlas["source_sha256"],
        *outputs,
        facilities + "atlas.py",
        "geospatial/maps/MAP_MANIFEST.json",
    ]:
        if source not in atlas_outputs:
            connect(source, atlas_outputs, "python geospatial/facilities/atlas.py")
    # Runtime originals belong to the accepted runtime renderer, not the facility renderer.
    runtime_outputs = [a["path"] for m in runtime["maps"] for a in m["artifacts"].values()]
    for source in [
        "enterprise/services/source/runtime_sites_2026-09-11.json",
        "enterprise/services/source/runtime_capital_plan_2026-09-11.json",
        "enterprise/runtime/design.py",
        "enterprise/runtime/render.py",
    ]:
        connect(
            source,
            runtime_outputs + ["enterprise/runtime/visuals/manifest.json"],
            "python -m enterprise.runtime.render (review accepted release lineage first)",
        )
    spatial_manifest = root / "geospatial/maps/spatial/MANIFEST.json"
    if spatial_manifest.is_file():
        spatial = json.loads(spatial_manifest.read_text())
        spatial_outputs = [a["path"] for m in spatial["maps"] for a in m["artifacts"].values()]
        spatial_outputs += [
            "geospatial/maps/spatial.html",
            "geospatial/maps/spatial/MANIFEST.json",
            "geospatial/maps/spatial/README.md",
        ]
        for source in spatial["source_sha256"]:
            connect(
                source, spatial_outputs, "python geospatial/facilities/spatial/build.py --render"
            )
        connect(
            "geospatial/maps/spatial/MANIFEST.json",
            ["geospatial/maps/MAP_MANIFEST.json"],
            "python geospatial/facilities/integrate_manifest.py",
        )
    workbench_outputs = [
        facilities + "workbench/BASELINE.json",
        facilities + "workbench/READINESS.json",
        facilities + "workbench/EVIDENCE_QUEUE.json",
        facilities + "workbench/DEPENDENCIES.json",
        facilities + "workbench/BASELINE_SCENARIO.json",
        facilities + "workbench/BASELINE_RESULT.json",
        facilities + "workbench/MANIFEST.json",
        "geospatial/maps/workbench.html",
    ]
    for source in list(hashes) + [
        p.relative_to(root).as_posix()
        for p in (root / (facilities + "workbench")).glob("*")
        if p.suffix in (".py", ".js", ".html") and not p.name.startswith("test_")
    ]:
        connect(source, workbench_outputs, "python geospatial/facilities/workbench/build.py")
    return {
        "source_sha256": dict(sorted(hashes.items())),
        "edges": {k: sorted(v) for k, v in sorted(edges.items())},
        "generators": {k: sorted(v) for k, v in sorted(generators.items())},
        "basis": "Conservative manifest and generator dependency closure; a dependent artifact is a regeneration candidate, not proof its pixels changed.",
    }


def impact(graph, changed):
    affected = set()
    todo = list(changed)
    seen = set(todo)
    while todo:
        for output in graph["edges"].get(todo.pop(), []):
            affected.add(output)
            if output not in seen:
                seen.add(output)
                todo.append(output)
    return {
        "changed": sorted(set(changed)),
        "affected_artifacts": sorted(affected),
        "commands": sorted({c for p in affected for c in graph["generators"].get(p, [])}),
        "unmapped": sorted(set(changed) - set(graph["edges"])),
        "rule": "Unmapped sources require review; commands are a set, not an execution order. No automatic regeneration or canon promotion.",
    }


def stale_sources(root, graph):
    return [
        p
        for p, h in graph["source_sha256"].items()
        if not (Path(root) / p).is_file() or digest(Path(root) / p) != h
    ]
