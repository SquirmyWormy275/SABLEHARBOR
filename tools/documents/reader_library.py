"""Derived file discovery beside the controlled institutional catalog.

Never infer approval or a source/publication relationship from a filename.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

GROUPS = {
    "business": "Businesses and professional practice",
    "people": "People, governance and departments",
    "finance": "Finance, transactions and operating cases",
    "controls": "Controls, services and runtime",
    "places": "Geography and facilities",
    "identity": "Identity and collateral",
    "history": "Canon, history and decisions",
    "reader": "Reader guides and subject pages",
    "technical": "Implementation, source guides and delivery evidence",
}


def group(path: str) -> str:
    if path.startswith(("docs/wiki/", "docs/reader/")):
        return "reader"
    if path.startswith(("docs/canon/", "docs/history/")):
        return "history"
    if path.startswith(("docs/business-lines/", "docs/advisory/")):
        return "business"
    if path.startswith(
        ("docs/controls/", "enterprise/ccf/", "enterprise/services/", "enterprise/runtime/")
    ):
        return "controls"
    if path.startswith(
        (
            "docs/finance/",
            "docs/legal/",
            "docs/audit/",
            "industrial/",
            "red_wash/",
            "blackridge/",
            "enterprise/business/",
            "enterprise/operations/",
        )
    ):
        return "finance"
    if path.startswith(("geospatial/", "docs/facilities/", "assets/headquarters/")):
        return "places"
    if path.startswith("assets/brand/"):
        return "identity"
    if path.startswith(("docs/governance/", "docs/organization/", "docs/j2/")):
        return "people"
    return "technical"


def inputs(root: Path) -> list[str]:
    raw = (
        subprocess.check_output(["git", "ls-files", "-z", "--cached"], cwd=root)
        .decode()
        .split("\0")
    )
    return sorted(
        {
            p
            for p in raw
            if p
            and (root / p).is_file()
            and Path(p).suffix.lower() in {".md", ".pdf", ".xlsx"}
            and not p.startswith("docs/wiki/library/")
            and p != "docs/wiki/Library.md"
        }
    )


def link(target: str, page: str) -> str:
    return quote(os.path.relpath(target, str(Path(page).parent)), safe="/-_.")


def title(path: Path) -> str:
    if path.suffix.lower() == ".md":
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip().replace("|", " / ")
    return path.stem.replace("_", " ").replace("|", " / ")


def evidence_acceptance(root: Path, directory: Path, draft_status: str) -> str:
    """Acceptance is a separate dated record; never rewrite reviewed draft bytes."""
    path = directory / "ACCEPTANCE.json"
    if not path.exists():
        return draft_status
    accepted = json.loads(path.read_text())
    if accepted["status"] != "OWNER_ACCEPTED_EXACT_PACKET":
        raise ValueError("Unknown evidence acceptance state")
    if not (root / accepted["controlling_record"]).is_file():
        raise ValueError("Missing evidence acceptance canon")
    for relative, digest in accepted["artifacts"].items():
        target = (root / relative).resolve()
        if not target.is_relative_to(directory.resolve()) or not target.is_file():
            raise ValueError("Accepted evidence path missing or unsafe")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Accepted evidence bytes changed: " + relative)
    return accepted["status"]


def evidence_records(root: Path) -> list[tuple]:
    """Validate declared draft evidence without promoting it to a controlled publication."""
    records = []
    base = root / "docs/finance/evidence"
    for path in sorted(base.glob("*/catalog.json")):
        catalog = json.loads(path.read_text())
        source = json.loads((path.parent / "source.json").read_text())
        manifest = json.loads((path.parent / "manifest.json").read_text())
        if catalog["document_id"] != source["packet_id"] or catalog["status"] != "DRAFT_FOR_USER_REVIEW":
            raise ValueError("Evidence identity or draft status mismatch")
        if manifest["status"] != "DRAFT_NOT_APPROVED":
            raise ValueError("Evidence manifest is not an unapproved draft")
        if manifest["release_sha256"] != source["release_sha256"]:
            raise ValueError("Evidence release mismatch")
        for name, digest in catalog["artifacts"].items():
            target = (path.parent / name).resolve()
            if not target.is_relative_to(path.parent.resolve()) or not target.is_file():
                raise ValueError("Evidence artifact missing or unsafe")
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError("Evidence artifact hash mismatch: " + name)
        if manifest["files"].get("catalog.json") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Evidence catalog hash mismatch")
        invoice = source["rows"]["invoices"]
        if len(invoice) != 1 or any(invoice[0][key] != catalog[key] for key in ("invoice_id", "scenario", "unit")):
            raise ValueError("Evidence invoice or scope mismatch")
        if catalog["source_revision"] != source["release_source_revision"]:
            raise ValueError("Evidence revision mismatch")
        native = source["release"] + "/" + source["members"]["native_database"]["member"]
        if catalog["native_database"] != native:
            raise ValueError("Evidence native database link mismatch")
        for rows in source["rows"].values():
            if any(row.get("scenario", catalog["scenario"]) != catalog["scenario"] or row["unit"] != catalog["unit"] for row in rows):
                raise ValueError("Evidence source population scope mismatch")
        if catalog["native_source_ids"] != [row["event_id"] for row in source["rows"]["events"]]:
            raise ValueError("Evidence accounting event links mismatch")
        relatives = [str((path.parent / name).relative_to(root)) for name in ("PACKET.md", "packet.pdf", "reconciliation.xlsx")]
        hashes = [catalog["artifacts"][name] for name in ("PACKET.md", "packet.pdf", "reconciliation.xlsx")]
        records.append((catalog["document_id"], evidence_acceptance(root, path.parent, catalog["status"]), catalog["invoice_id"], catalog["scenario"], catalog["unit"], source["release"], source["release_source_revision"], source["release_sha256"], catalog["native_database"], json.dumps(source["members"], sort_keys=True), json.dumps(catalog["native_source_ids"]), *relatives, *hashes, str(path.relative_to(root))))
    return records


def counterpart_records(root: Path) -> dict:
    """Apply a dated audit only to unchanged sources and verified artifact bytes."""
    path = root / "docs/reader/reconciliation/records.json"
    if not path.is_file():
        return {}
    result = {}
    for record in json.loads(path.read_text())["records"]:
        source = record["source"]
        target = (root / source).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError("Missing/unsafe counterpart source: " + source)
        if source in result:
            raise ValueError("Duplicate counterpart source: " + source)
        if hashlib.sha256(target.read_bytes()).hexdigest() != record["source_sha256"]:
            continue  # Current edits require a new review, not the historical disposition.
        for evidence in record["verified_evidence"]:
            for artifact in evidence["artifacts"]:
                target = (root / artifact["path"]).resolve()
                if not target.is_relative_to(root.resolve()) or not target.is_file():
                    raise ValueError("Missing/unsafe counterpart artifact: " + artifact["path"])
                if hashlib.sha256(target.read_bytes()).hexdigest() != artifact["sha256"]:
                    raise ValueError("Stale counterpart artifact: " + artifact["path"])
        result[source] = record
    return result


def populate(
    root: Path, db: sqlite3.Connection, artifacts: list[dict],
    *, file_paths: list[str] | None = None,
) -> dict:
    db.executescript("""
      CREATE TABLE reader_file (
        path TEXT PRIMARY KEY, title TEXT NOT NULL, format TEXT NOT NULL,
        collection TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL);
      CREATE TABLE reader_publication_pair (
        source_path TEXT NOT NULL REFERENCES reader_file(path),
        publication_path TEXT NOT NULL REFERENCES reader_file(path),
        provenance TEXT NOT NULL, PRIMARY KEY(source_path, publication_path));
      CREATE TABLE reader_format_review (
        source_path TEXT PRIMARY KEY REFERENCES reader_file(path),
        review_state TEXT NOT NULL, rationale TEXT NOT NULL,
        review_queue TEXT NOT NULL);
      CREATE TABLE reader_counterpart_audit (
        source_path TEXT PRIMARY KEY REFERENCES reader_file(path),
        disposition TEXT NOT NULL, evidence_json TEXT NOT NULL);
      CREATE TABLE reader_evidence_link (
        document_id TEXT PRIMARY KEY, status TEXT NOT NULL, invoice_id TEXT NOT NULL,
        scenario TEXT NOT NULL, reporting_unit TEXT NOT NULL, release_tag TEXT NOT NULL,
        source_revision TEXT NOT NULL, release_sha256 TEXT NOT NULL,
        native_database TEXT NOT NULL, member_provenance_json TEXT NOT NULL,
        source_ids_json TEXT NOT NULL, markdown_path TEXT NOT NULL REFERENCES reader_file(path),
        pdf_path TEXT NOT NULL REFERENCES reader_file(path),
        xlsx_path TEXT NOT NULL REFERENCES reader_file(path),
        markdown_sha256 TEXT NOT NULL, pdf_sha256 TEXT NOT NULL, xlsx_sha256 TEXT NOT NULL,
        catalog_path TEXT NOT NULL);
      CREATE VIRTUAL TABLE reader_search USING fts5(path UNINDEXED, title, body);
    """)
    rows = []
    publication_sources = {a["publication"]: a["source"] for a in artifacts}
    for relative in inputs(root) if file_paths is None else file_paths:
        path = root / relative
        data = path.read_bytes()
        heading = title(path)
        if relative in publication_sources:
            heading = f"{title(root / publication_sources[relative])} — {path.stem}"
        row = (
            relative,
            heading,
            path.suffix.lower()[1:],
            group(relative),
            hashlib.sha256(data).hexdigest(),
            len(data),
        )
        rows.append(row)
        db.execute("INSERT INTO reader_file VALUES (?,?,?,?,?,?)", row)
        body = data.decode(errors="replace") if row[2] == "md" else row[1]
        db.execute("INSERT INTO reader_search VALUES (?,?,?)", (relative, row[1], body))
    paths = {r[0] for r in rows}
    evidence = evidence_records(root)
    for record in evidence:
        if any(path not in paths for path in record[11:14]):
            raise ValueError("Evidence artifact is not in tracked reader inventory")
        db.execute("INSERT INTO reader_evidence_link VALUES (" + ",".join("?" for _ in record) + ")", record)
    paired = {}
    for artifact in artifacts:
        source, publication = artifact["source"], artifact["publication"]
        if source not in paths or publication not in paths:
            raise ValueError(f"reader library missing controlled pair: {source}")
        db.execute(
            "INSERT INTO reader_publication_pair VALUES (?,?,?)",
            (source, publication, "docs/governance/publication_manifest.json"),
        )
        paired[source] = publication
    review_rows = []
    audited = counterpart_records(root)
    for path, record in audited.items():
        db.execute("INSERT INTO reader_counterpart_audit VALUES (?,?,?)",
                   (path, record["disposition"], json.dumps(record, sort_keys=True)))
    for path, heading, extension, collection, _, _ in rows:
        if extension != "md":
            continue
        if path in paired:
            state = "VERIFIED_DOCUMENT_PAIR"
            reason = (
                "Manifested Markdown/PDF pair; native transactional coverage is a separate check."
            )
            queue = "Existing controlled-publication maintenance"
        elif path.startswith(("docs/wiki/", "docs/reader/")) or Path(path).name in {
            "README.md",
            "MAINTAINERS.md",
        }:
            state = "READER_OR_MAINTENANCE_PAGE"
            reason = (
                "Navigation/maintenance text; not presented as an in-universe corporate instrument."
            )
            queue = "Reader navigation maintenance"
        else:
            state = "COUNTERPART_REVIEW_REQUIRED"
            reason = "No pair verified by this manifest; check other manifests/releases before declaring a missing publication."
            queue = (
                "SH-FIN-HUMAN-001"
                if collection == "finance"
                else "Corporate document-format reconciliation"
            )
        if path not in paired and path in audited:
            record = audited[path]
            state, reason, queue = record["disposition"], record["rationale"], record["next_action"]
        db.execute(
            "INSERT INTO reader_format_review VALUES (?,?,?,?)", (path, state, reason, queue)
        )
        review_rows.append((path, heading, state, reason, queue))
    counts = Counter(r[2] for r in rows)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[3]].append(row)
    directory = root / "docs/wiki/library"
    directory.mkdir(parents=True, exist_ok=True)
    for key, label in GROUPS.items():
        page = f"docs/wiki/library/{key}.md"
        lines = [
            f"# {label}",
            "",
            "[Library](../Library.md) · [Company index](../Home.md)",
            "",
            "Generated file inventory. Includes current and historical records; open the source for its status. "
            "A folder or title does not establish approval. PDF companions below are verified through the controlled-publication manifest. "
            "Other files are listed independently; an absent companion link means unmapped, not proven nonexistent.",
            "",
        ]
        folders = defaultdict(list)
        for row in grouped[key]:
            folders[str(Path(row[0]).parent)].append(row)
        for folder, records in sorted(folders.items()):
            lines.extend([f"## `{folder}`", ""])
            for path, heading, extension, _, _, _ in records:
                safe_heading = heading.replace("[", "\\[").replace("]", "\\]")
                entry = f"- [{safe_heading}]({link(path, page)}) — {extension.upper()}"
                if path in paired:
                    entry += f" · [formatted PDF]({link(paired[path], page)})"
                lines.append(entry)
            lines.append("")
        (root / page).write_text("\n".join(lines))
    review_page = "docs/wiki/library/format-review.md"
    review_lines = [
        "# Document-format review queue",
        "",
        "[Library](../Library.md)",
        "",
        "Generated reconciliation queue, not an assertion that every unpaired record lacks a publication. "
        "The repository maintainer owns reconciliation of this queue; these work queues are not in-universe appointments. "
        "Review other domain manifests and release members before proposing new documents. "
        "Historical releases remain immutable. Native accounting record completeness is outside this discovery index.",
        "",
        "| State | Records |",
        "|---|---:|",
    ]
    review_counts = Counter(row[2] for row in review_rows)
    review_lines.extend(f"| {state} | {count} |" for state, count in sorted(review_counts.items()))
    review_lines.extend(
        [
            "",
            "## Records requiring counterpart reconciliation",
            "",
            "Finance records route to [SH-FIN-HUMAN-001](../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md). "
            "Other corporate records require scoped format review before any batch rendering. "
            "Existing approved visuals are retained; this queue does not authorize automatic publication.",
            "",
        ]
    )
    for path, heading, state, _reason, queue in review_rows:
        if state == "COUNTERPART_REVIEW_REQUIRED":
            label = heading.replace("[", "\\[").replace("]", "\\]")
            review_lines.append(f"- [{label}]({link(path, review_page)}) — {queue}")
    review_lines.append("")
    if audited:
        review_lines.extend([
            "## Dated counterpart dispositions", "",
            "The [complete dated audit](../../reader/reconciliation/README.md) records verified "
            "artifacts, maintenance exemptions and unresolved document counterparts. Its dispositions "
            "are applied only while each source hash matches; changed sources return to review. "
            "The database table `reader_counterpart_audit` retains the exact evidence for each applied row.", "",
        ])
    (root / review_page).write_text("\n".join(review_lines))
    lines = [
        "# Document library",
        "",
        "[Company index](Home.md) · [Use cases](../reader/USE_CASES.md) · "
        "[Source and format guide](../reader/SOURCES_AND_FORMATS.md)",
        "",
        "Use the subject pages for a guided introduction. Use this complete file inventory to reach the underlying "
        "Markdown records, PDFs and Excel workbooks without parsing source data. Current and historical files remain "
        "visible; read each document's status and successor references.",
        "",
        "| Collection | Files |",
        "|---|---:|",
    ]
    lines.extend(
        f"| [{label}](library/{key}.md) | {len(grouped[key])} |" for key, label in GROUPS.items()
    )
    lines.extend(
        [
            "",
            "## Format coverage",
            "",
            f"The inventory contains {counts['md']} Markdown files, "
            f"{counts['pdf']} PDFs and {counts['xlsx']} Excel workbooks. "
            f"The existing publication manifest verifies {len(paired)} Markdown/PDF pairs.",
            "",
            "Every inventoried file has a path, title, format, collection, size and SHA-256 in "
            "`reader_file` within the [institutional database](../internal/institutional_catalog.sqlite3). "
            "`reader_publication_pair` records verified source/PDF links; `reader_search` supports text search. "
            "`reader_evidence_link` separately connects validated evidence packets to their native accounting IDs and MD/PDF/XLSX files without declaring publication approval. These are discovery tables. Native accounting and operating databases retain their transaction records.",
            "`reader_evidence_package` preserves accounting/legal package registers and review states; "
            "`reader_counterpart_audit` records applicable dated counterpart evidence.",
            "",
            "The [format-review queue](library/format-review.md) lists every unpaired non-navigation Markdown record for reconciliation. "
            "Unpaired documents have not been certified against the new three-form requirement. "
            "Release-only records are reached through release guides; their archive contents are not silently "
            "counted as files in this checkout. Code, raw data, imagery and packaged binaries are reached through "
            "their domain guides and manifests. Generated library pages are excluded from their own inventory.",
            "",
            "## Rebuild",
            "",
            "Run `python tools/documents/build_institutional_catalog.py` from the repository root. "
            "The generator updates this library and the existing database together. It does not change source records "
            "or issue new publications.",
            "",
        ]
    )
    (root / "docs/wiki/Library.md").write_text("\n".join(lines))
    return {"files": len(rows), "formats": dict(counts), "verified_pairs": len(paired)}
