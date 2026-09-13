"""Validate source-bound accounting/legal reading packages for discovery.

Registers describe evidence and review state; database inclusion never accepts a design.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def records(root: Path) -> list[tuple]:
    output = []
    seen = set()
    for base in ("docs/finance/evidence", "docs/legal/evidence", "docs/reader/transactions"):
        for path in sorted((root / base).rglob("evidence-register.json")):
            data = json.loads(path.read_text())
            identity = data["package_id"]
            if not identity or identity in seen:
                raise ValueError(f"Duplicate/empty evidence package ID: {identity}")
            seen.add(identity)

            def target(relative):
                candidate = (root / relative).resolve()
                if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
                    raise ValueError(f"Missing/unsafe evidence path: {relative}")
                return candidate

            markdown = target(data["markdown"])
            if markdown.suffix != ".md" or not data["status"] or not data["sources"]:
                raise ValueError(f"Incomplete evidence package: {identity}")
            for source in data["sources"]:
                payload = target(source["path"]).read_bytes()
                if hashlib.sha256(payload).hexdigest() != source["sha256"]:
                    raise ValueError(f"Stale evidence source: {source['path']}")
            if data.get("reconciliation"):
                target(data["reconciliation"])
            if data.get("visual_manifest"):
                target(data["visual_manifest"])
            output.append((identity, data["title"], data["status"], data["markdown"],
                           str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest(),
                           json.dumps(data, sort_keys=True)))
    return sorted(output)


def artifact_records(root: Path) -> list[tuple]:
    """Bind review files through explicit domain manifests, never filename similarity."""
    output = []
    for package in records(root):
        directory = (root / package[4]).parent
        for manifest in (directory / "draft/manifest.json", directory / "visual-manifest.json"):
            if not manifest.exists():
                continue
            data = json.loads(manifest.read_text())
            if data["status"] != "DRAFT_FOR_EXACT_FILE_REVIEW" or data.get("approved", False):
                raise ValueError("Unrecognized review acceptance state: " + str(manifest))

            def verify(relative, digest):
                target = (root / relative).resolve()
                if not target.is_relative_to(root.resolve()) or not target.is_file():
                    raise ValueError("Missing/unsafe review artifact: " + relative)
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise ValueError("Stale review artifact: " + relative)

            def append(relative, digest, source):
                verify(relative, digest)
                output.append((package[0], relative, Path(relative).suffix.lstrip("."),
                               data["status"], source, digest, str(manifest.relative_to(root))))

            if isinstance(data["artifacts"], dict):
                if data["source_register_sha256"] != package[5]:
                    raise ValueError("Review source register changed: " + package[4])
                if "renderer_sha256" in data:
                    verify("docs/finance/evidence/coverage/render.py", data["renderer_sha256"])
                for relative, digest in data.get("source_dependencies", {}).items():
                    verify(relative, digest)
                for relative, digest in data["artifacts"].items():
                    append(relative, digest, package[4])
            else:
                verify(data["logo"]["path"], data["logo"]["sha256"])
                for artifact in data["artifacts"]:
                    verify(artifact["markdown"], artifact["source_sha256"])
                    for key in ("pdf", "html"):
                        append(artifact[key], artifact[key + "_sha256"], artifact["markdown"])
    paths = [row[1] for row in output]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate review artifact identity")
    return sorted(output)


def populate(root, db):
    db.execute("""CREATE TABLE reader_evidence_package (
        package_id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
        markdown_path TEXT NOT NULL REFERENCES reader_file(path),
        register_path TEXT NOT NULL UNIQUE, register_sha256 TEXT NOT NULL,
        provenance_json TEXT NOT NULL)""")
    rows = records(root)
    db.executemany("INSERT INTO reader_evidence_package VALUES (?,?,?,?,?,?,?)", rows)
    db.execute("""CREATE TABLE reader_evidence_artifact (
        package_id TEXT NOT NULL REFERENCES reader_evidence_package(package_id),
        artifact_path TEXT PRIMARY KEY, format TEXT NOT NULL, status TEXT NOT NULL,
        source_reference TEXT NOT NULL, sha256 TEXT NOT NULL, manifest_path TEXT NOT NULL)""")
    db.executemany("INSERT INTO reader_evidence_artifact VALUES (?,?,?,?,?,?,?)",
                   artifact_records(root))
    return len(rows)
