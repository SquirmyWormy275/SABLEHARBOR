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
    for base in ("docs/finance/evidence", "docs/legal/evidence"):
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


def populate(root, db):
    db.execute("""CREATE TABLE reader_evidence_package (
        package_id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
        markdown_path TEXT NOT NULL REFERENCES reader_file(path),
        register_path TEXT NOT NULL UNIQUE, register_sha256 TEXT NOT NULL,
        provenance_json TEXT NOT NULL)""")
    rows = records(root)
    db.executemany("INSERT INTO reader_evidence_package VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)
