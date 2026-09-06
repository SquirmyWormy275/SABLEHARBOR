"""Acceptance checks for Red Wash controlled-publication catalog integration."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORDS = {
    "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05.md": {
        "id": "SH-PS-RW-TOR-001",
        "publication": "docs/governance/publications/SH-PS-RW-TOR-001_v1.0.0.pdf",
        "brand": "pale_sun",
        "category": "Red Wash transaction and operating record",
        "owner": "Pale Sun operating authority",
    },
    "red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md": {
        "id": "SH-PS-RW-LOG-001",
        "publication": "docs/governance/publications/SH-PS-RW-LOG-001_v1.0.0.pdf",
        "brand": "red_wash",
        "category": "Red Wash logistics dependency record",
        "owner": "Pale Sun / Red Wash",
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_red_wash_publications_reconcile_to_sources_and_catalog() -> None:
    manifest = json.loads((ROOT / "docs/governance/publication_manifest.json").read_text())
    catalog = json.loads((ROOT / "docs/internal/institutional_catalog.json").read_text())
    artifacts = {artifact["source"]: artifact for artifact in manifest["artifacts"]}
    objects = {obj["source"]: obj for obj in catalog["objects"]}

    assert manifest["generated_for_version"] >= "2026-09-05"
    assert manifest["reproducibility"]["mutable_pdf_metadata"] == "removed"
    assert catalog["effective_date"] == manifest["generated_for_version"]

    with sqlite3.connect(ROOT / "docs/internal/institutional_catalog.sqlite3") as db:
        for source, expected in RECORDS.items():
            artifact = artifacts[source]
            obj = objects[source]
            source_path = ROOT / source
            publication_path = ROOT / expected["publication"]

            assert artifact["publication"] == expected["publication"]
            assert artifact["brand"] == expected["brand"]
            assert digest(source_path) == artifact["source_sha256"] == obj["source_sha256"]
            assert digest(publication_path) == artifact["sha256"] == obj["publication_sha256"]
            assert publication_path.read_bytes().startswith(b"%PDF-")
            for field in ("id", "publication", "category", "owner"):
                assert obj[field] == expected[field]

            db_row = db.execute(
                """
                SELECT category, owner, publication_path
                FROM institutional_object
                WHERE id = ?
                """,
                (expected["id"],),
            ).fetchone()
            assert db_row == (
                expected["category"],
                expected["owner"],
                expected["publication"],
            )
