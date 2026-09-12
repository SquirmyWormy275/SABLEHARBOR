#!/usr/bin/env python3
"""Validate reader links, generated discovery coverage, and exact source hashes."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/documents"))


TABLES = (
    "institutional_object",
    "relationship",
    "institutional_search",
    "reader_file",
    "reader_publication_pair",
    "reader_format_review",
    "reader_search",
    "reader_evidence_link",
    "reader_evidence_package",
    "reader_counterpart_audit",
    "reader_text",
    "reader_evidence_artifact",
)


def logical_content(db):
    return {name: sorted(db.execute(f"SELECT * FROM {name}").fetchall()) for name in TABLES}


def main(check_regeneration=False) -> None:
    from reader_library import inputs, evidence_records
    from evidence_packages import records as package_records
    from evidence_packages import artifact_records

    pages = [
        ROOT / "README.md",
        *sorted((ROOT / "docs/wiki").rglob("*.md")),
        *sorted((ROOT / "docs/reader").rglob("*.md")),
        ROOT / "docs/finance/READER_EXERCISES.md",
        ROOT / "docs/handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md",
        *sorted((ROOT / "docs/finance/evidence").rglob("*.md")),
        *sorted((ROOT / "docs/legal/evidence").rglob("*.md")),
    ]
    failures = []
    checked = 0
    for page in pages:
        text = page.read_text()
        # Exclude fenced examples; include image URLs and ordinary inline links.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        targets = re.findall(r"\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text)
        targets += re.findall(r'(?:src|href)="([^"]+)"', text)
        for target in targets:
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            candidate = (page.parent / unquote(parsed.path)).resolve()
            if not candidate.is_relative_to(ROOT) or not candidate.exists():
                failures.append(f"{page.relative_to(ROOT)} -> {target}")
            elif parsed.fragment and candidate.suffix.lower() == ".md":
                anchors = set()
                duplicates = {}
                for heading in re.findall(r"^#{1,6}\s+(.+)$", candidate.read_text(), flags=re.M):
                    slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                    occurrence = duplicates.get(slug, 0)
                    duplicates[slug] = occurrence + 1
                    anchors.add(slug + (f"-{occurrence}" if occurrence else ""))
                anchors.update(re.findall(r'(?:id|name)="([^"]+)"', candidate.read_text()))
                if unquote(parsed.fragment) not in anchors:
                    failures.append(f"Missing anchor: {page.relative_to(ROOT)} -> {target}")
            checked += 1
    db = sqlite3.connect(
        f"file:{ROOT / 'docs/internal/institutional_catalog.sqlite3'}?mode=ro", uri=True
    )
    rows = db.execute("SELECT path,sha256,bytes FROM reader_file").fetchall()
    expected = set(inputs(ROOT))
    actual = {r[0] for r in rows}
    if actual != expected:
        failures.append(
            f"Reader coverage differs: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    for relative, digest, length in rows:
        payload = (ROOT / relative).read_bytes()
        if len(payload) != length or hashlib.sha256(payload).hexdigest() != digest:
            failures.append(f"Stale reader file: {relative}")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        failures.append("Reader or institutional foreign-key failure")
    for relative in ["docs/finance/READER_EXERCISES.md", "docs/wiki/Home.md", "README.md"]:
        if not db.execute("SELECT 1 FROM reader_search WHERE path=?", (relative,)).fetchone():
            failures.append(f"Missing searchable reader entry: {relative}")
    if (
        db.execute("SELECT count(*) FROM reader_publication_pair").fetchone()[0]
        != db.execute("SELECT count(*) FROM institutional_object").fetchone()[0]
    ):
        failures.append("Controlled pair coverage differs from institutional catalog")
    try:
        expected_evidence = sorted(evidence_records(ROOT))
        actual_evidence = sorted(db.execute("SELECT * FROM reader_evidence_link").fetchall())
        if expected_evidence != actual_evidence:
            failures.append("Evidence database links differ from validated packet catalogs")
        if package_records(ROOT) != sorted(db.execute("SELECT * FROM reader_evidence_package").fetchall()):
            failures.append("Evidence package database differs from source registers")
        if artifact_records(ROOT) != sorted(db.execute("SELECT * FROM reader_evidence_artifact").fetchall()):
            failures.append("Review artifact database differs from verified manifests")
    except (ValueError, KeyError) as error:
        failures.append(str(error))
    before = logical_content(db) if check_regeneration else None
    db.close()
    if failures:
        raise SystemExit("\n".join(failures))
    if check_regeneration:
        subprocess.run(
            [sys.executable, str(ROOT / "tools/documents/build_institutional_catalog.py")],
            check=True,
        )
        regenerated = sqlite3.connect(ROOT / "docs/internal/institutional_catalog.sqlite3")
        after = logical_content(regenerated)
        regenerated.close()
        if before != after:
            raise SystemExit("Database logical content differs after regeneration")
        print("All institutional/reader table and search contents reproduce exactly")
    print(
        f"Reader validation passed: {len(pages)} pages, {checked} local links, {len(rows)} indexed files"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-regeneration", action="store_true")
    main(parser.parse_args().check_regeneration)
