#!/usr/bin/env python3
"""Build Alexandria's derived JSON and SQLite institutional catalog."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/governance/publication_manifest.json"
OUT_JSON = ROOT / "docs/internal/institutional_catalog.json"
OUT_DB = ROOT / "docs/internal/institutional_catalog.sqlite3"


def field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"\*\*{re.escape(name)}:\*\*\s*([^\n|]+)", text, re.I)
    return match.group(1).strip().strip("`") if match else default


def category(path: str) -> str:
    if path == "docs/canon/INDUSTRIAL_PLANNING_SUCCESSOR_2026-09-06.md":
        return "industrial planning authority"
    if path.startswith("industrial/planning/"):
        return "industrial conditional planning record"
    if path == "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md":
        return "canon decision addendum"
    if path == "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md":
        return "Red Wash transaction and operating record"
    if path.startswith("red_wash/logistics/"):
        return "Red Wash logistics dependency record"
    if path.startswith("industrial/"):
        return "industrial synthetic company record"
    if "/committees/" in path:
        return "committee charter"
    if path.startswith("docs/governance/"):
        return "governance policy"
    if "/alexandria/" in path:
        return "Alexandria doctrine"
    if path.startswith("docs/j2/"):
        return "J2 doctrine"
    return "institutional assurance"


def inferred_owner(path: str) -> str:
    if path == "docs/canon/INDUSTRIAL_PLANNING_SUCCESSOR_2026-09-06.md":
        return "Repository owner"
    if path.startswith("industrial/"):
        return "Sable Harbor Industrial Holdings"
    name = Path(path).stem
    if path == "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md":
        return "Repository owner"
    if path == "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md":
        return "Pale Sun operating authority"
    if path.startswith("red_wash/logistics/"):
        return "Pale Sun / Red Wash"
    if path.startswith("docs/governance/"):
        return "Corporate Governance"
    if any(x in name for x in ("ORIENTATION", "EIB", "CANON", "SEMAPHORE")):
        return "Orientation"
    if "JUDGMENT" in name:
        return "Judgment"
    if "CONTACT" in name:
        return "Contact"
    if "EDUCATION" in name:
        return "Education"
    if "JUNCTION" in name:
        return "Junction Advisory Group"
    return "J2 Headquarters"


def split_refs(value: str) -> list[str]:
    return [x.strip().strip("`") for x in re.split(r"[;,]", value) if x.strip()]


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    objects = []
    for artifact in manifest["artifacts"]:
        source = artifact["source"]
        source_path = ROOT / source
        publication_path = ROOT / artifact["publication"]
        for path in (source_path, publication_path):
            if not path.is_file():
                raise SystemExit(f"controlled artifact missing: {path.relative_to(ROOT)}")
        source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        publication_sha256 = hashlib.sha256(publication_path.read_bytes()).hexdigest()
        if source_sha256 != artifact["source_sha256"]:
            raise SystemExit(f"controlled source hash drift: {source}")
        if publication_sha256 != artifact["sha256"]:
            raise SystemExit(f"controlled publication hash drift: {artifact['publication']}")

        text = source_path.read_text()
        title_match = re.search(r"^#\s+(.+)$", text, re.M)
        doc_id = field(text, "Document ID")
        if not title_match or not doc_id:
            raise SystemExit(f"controlled source lacks title or document ID: {source}")
        related = split_refs(field(text, "Related"))
        cross_refs = split_refs(field(text, "Cross-reference", field(text, "Cross-references")))
        searchable = " ".join((title_match.group(1), source, text)).lower()
        objects.append({
            "id": doc_id,
            "title": title_match.group(1).strip(),
            "category": category(source),
            "owner": field(text, "Owner", inferred_owner(source)),
            "version": field(text, "Version", "1.0.0"),
            "status": field(text, "State", field(text, "Status", "CONTROLLED")),
            "source": source,
            "publication": artifact["publication"],
            "source_sha256": source_sha256,
            "publication_sha256": publication_sha256,
            "related_doctrines": related,
            "cross_references": cross_refs,
            "search_text": searchable,
        })
    object_ids = [obj["id"] for obj in objects]
    if len(object_ids) != len(set(object_ids)):
        raise SystemExit("controlled catalog contains duplicate document IDs")

    payload = {
        "catalog_id": "SH-ALX-CATALOG-001",
        "version": "1.0.2",
        "effective_date": manifest["generated_for_version"],
        "authority": "Derived from canonical Markdown and the controlled-publication manifest; not a parallel source of truth.",
        "objects": objects,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    if OUT_DB.exists():
        OUT_DB.unlink()
    db = sqlite3.connect(OUT_DB)
    db.executescript("""
    CREATE TABLE institutional_object (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
      owner TEXT NOT NULL, version TEXT NOT NULL, status TEXT NOT NULL,
      source_path TEXT UNIQUE NOT NULL, publication_path TEXT UNIQUE NOT NULL,
      source_sha256 TEXT NOT NULL, publication_sha256 TEXT NOT NULL,
      search_text TEXT NOT NULL);
    CREATE TABLE relationship (
      source_id TEXT NOT NULL REFERENCES institutional_object(id),
      relation_type TEXT NOT NULL, target_reference TEXT NOT NULL,
      PRIMARY KEY(source_id, relation_type, target_reference));
    CREATE VIRTUAL TABLE institutional_search USING fts5(id UNINDEXED, title, owner, category, body);
    """)
    for obj in objects:
        db.execute("INSERT INTO institutional_object VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            obj["id"], obj["title"], obj["category"], obj["owner"], obj["version"],
            obj["status"], obj["source"], obj["publication"], obj["source_sha256"],
            obj["publication_sha256"], obj["search_text"]))
        db.execute("INSERT INTO institutional_search VALUES (?,?,?,?,?)", (
            obj["id"], obj["title"], obj["owner"], obj["category"], obj["search_text"]))
        for relation_type, values in (("related", obj["related_doctrines"]), ("cross_reference", obj["cross_references"])):
            for value in values:
                db.execute("INSERT OR IGNORE INTO relationship VALUES (?,?,?)", (obj["id"], relation_type, value))
    db.execute("CREATE VIEW current_institutional_object AS SELECT * FROM institutional_object WHERE upper(status) NOT LIKE 'SUPERSEDED%'")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
