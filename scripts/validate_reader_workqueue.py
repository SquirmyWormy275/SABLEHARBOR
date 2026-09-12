#!/usr/bin/env python3
"""Validate the resumable reader queue; never execute jobs or infer approval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/reader/overnight/QUEUE.json"


def validate(root: Path, data: dict) -> None:
    jobs = data["jobs"]
    ids = [job["id"] for job in jobs]
    if not jobs or len(ids) != len(set(ids)):
        raise ValueError("Empty queue or duplicate job IDs")
    by_id = {job["id"]: job for job in jobs}
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            raise ValueError(f"Cyclic dependency: {key}")
        if key in visited:
            return
        if key not in by_id:
            raise ValueError(f"Unknown dependency: {key}")
        visiting.add(key)
        for dependency in by_id[key]["depends_on"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    def relative(path):
        target = (root / path).resolve()
        if Path(path).is_absolute() or not target.is_relative_to(root.resolve()):
            raise ValueError(f"Path outside repository: {path}")
        return target

    for job in jobs:
        visit(job["id"])
        if job["gate"] not in {"existing_authority", "exact_visual_acceptance"}:
            raise ValueError(f"Invalid gate: {job['id']}")
        if not job["acceptance"] or not job["write_scope"]:
            raise ValueError(f"Missing acceptance/scope: {job['id']}")
        for path in job["inputs"]:
            if not relative(path).is_file():
                raise ValueError(f"Missing task input: {path}")
        for path in job["write_scope"]:
            relative(path)
    workers = [job for job in jobs if job["lane"] != "integrator"]
    for index, left in enumerate(workers):
        for right in workers[index + 1:]:
            if left["lane"] == right["lane"]:
                continue
            for a in map(Path, left["write_scope"]):
                for b in map(Path, right["write_scope"]):
                    if a == b or a in b.parents or b in a.parents:
                        raise ValueError(f"Cross-lane write collision: {left['id']} / {right['id']}")
    for record in data["frozen"]:
        path = relative(record["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Frozen asset changed: {record['path']}")


def validate_coverage(root: Path) -> None:
    data = json.loads((root / "docs/reader/WIKI_COVERAGE.json").read_text())
    records = data["pages"] + data["remaining_subject_queue"]
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate wiki coverage ID")
    actual = {record["page"] for record in data["pages"]}
    expected = {
        str(path.relative_to(root))
        for directory in ("businesses", "departments")
        for path in (root / "docs/wiki" / directory).glob("*.md")
        if path.name != "README.md"
    }
    if actual != expected or len(actual) != len(data["pages"]):
        raise ValueError("Wiki page coverage differs from current subject pages")
    counts = data["counts"]
    if counts != {
        "business_pages": sum("/businesses/" in path for path in actual),
        "department_institution_capability_pages": sum("/departments/" in path for path in actual),
        "queued_subjects": len(data["remaining_subject_queue"]),
    }:
        raise ValueError("Wiki coverage counts do not reconcile")
    for record in records:
        paths = record.get("source_entry_points", []) + record.get("existing_visuals_reused", [])
        paths += [record[key] for key in ("page", "source", "current_entry") if key in record]
        for path in paths:
            target = (root / path).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                raise ValueError(f"Missing/invalid wiki coverage target: {path}")


if __name__ == "__main__":
    data = json.loads(QUEUE.read_text())
    validate(ROOT, data)
    validate_coverage(ROOT)
    print(f"PASS: {len(data['jobs'])} jobs, dependency graph, input paths and frozen hashes")
    print(f"Execution state: {data['status']} (this check does not start work)")
