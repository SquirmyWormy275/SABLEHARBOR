"""Reproduce the complete pinned format-queue reconciliation, without editing its source."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = "8898d2d0310a60bdf0e4753036790c6eda1388cd"
QUEUE = "docs/wiki/library/format-review.md"


def blob(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def link(path):
    return os.path.relpath(ROOT / path, OUT)


def main(check=False):
    revision = subprocess.check_output(["git", "rev-parse", BASE], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT, text=True
    ).splitlines()
    queue = blob(QUEUE)
    rows = []
    # Inspect every tracked domain manifest/register and release index for exact source-path
    # references. A co-occurrence is search evidence, never a publication pairing.
    search_paths = [
        p
        for p in paths
        if p.endswith(".json") and ("manifest" in p.lower() or "register" in p.lower())
    ]
    search_paths += [p for p in paths if p.startswith("docs/releases/") and p.endswith(".md")]
    texts = {p: blob(p).decode("utf-8") for p in sorted(search_paths)}
    search_manifest = [{"path": p, "sha256": sha(t.encode())} for p, t in texts.items()]
    pubpath = "docs/governance/publication_manifest.json"
    pubs = json.loads(texts[pubpath])["artifacts"]
    chartpath = "docs/organization/ORGANIZATION_MAP_REGISTER.json"
    charts = json.loads(texts[chartpath])
    chart_by_page = {c["page"]: c for c in charts["charts"]}
    packet_dir = "docs/finance/evidence/SH-FIN-HUMAN-001/"
    packet = json.loads(blob(packet_dir + "catalog.json"))
    packet_manifest = json.loads(blob(packet_dir + "manifest.json"))
    maintenance_roots = (
        "docs/internal/development/",
        "docs/internal/validation/",
        "docs/handoffs/",
        "docs/releases/",
        "docs/commercialization/",
        "geospatial/facilities/qa/",
        "geospatial/reports/",
        "blackridge/reports/",
    )
    maintenance_names = {
        "CONTRIBUTING.md",
        "LICENSE.md",
        "SECURITY.md",
        "PULL_REQUEST_TEMPLATE.md",
        "FONT_PROVENANCE.md",
        "MANIFEST_SCOPE.md",
        "VALIDATION.md",
        "CONTROLLED_DOCUMENT_INDEX.md",
        "BACKLOG.md",
        "ARCHITECTURE.md",
        "DATABASE_AND_ACCOUNTING_ARCHITECTURE.md",
        "DATA_MODEL.md",
        "EXECUTION_PLAN.md",
        "GENERATION_METHOD.md",
        "GENERATION_RUN_ARCHITECTURE.md",
        "HANDOFF.md",
        "OVERNIGHT_RUN_STATE.md",
        "QUERY_COOKBOOK.md",
        "READER_EXERCISES.md",
        "UNIT_PACKAGE_CONTRACT.md",
        "VALIDATION_AND_RECONCILIATION.md",
        "WORKLOG.md",
        "OPERATING_DEPTH_EXPORT_SPECIFICATION.md",
        "SOURCE_LOCK_EXCEPTIONS.md",
        "CHART_GOVERNANCE.md",
        "CHART_MIGRATION.md",
        "CANON_TRACEABILITY_MATRIX.md",
        "DISPLAY_INVENTORY.md",
        "UNRESOLVED_AND_EXCLUDED.md",
        "NEXT_CHAT_HANDOFF.md",
        "DEFINITION_OF_DONE.md",
        "PROVENANCE_AND_REPRODUCIBILITY.md",
        "ARTIFACT_INDEX.md",
        "QA.md",
    }
    for title, target in re.findall(r"^- \[([^]]+)\]\(([^)]+)\) — ", queue.decode(), re.M):
        path = os.path.normpath(str(Path(QUEUE).parent / target))
        source = blob(path)
        text = source.decode()
        evidence = []
        matches = [p for p, t in texts.items() if path in t]
        dispositions = (
            "UNRESOLVED_DOCUMENT_COUNTERPART",
            "No exact source-to-PDF/XLSX relation was established in the scanned "
            "manifests. Related releases and documents do not establish equivalence.",
            "Find an explicit publication source/member mapping or prepare a scoped "
            "derivative after its design review.",
        )
        if path in chart_by_page:
            c = chart_by_page[path]
            evidence = [
                {
                    "manifest": chartpath,
                    "relationship": "REGISTERED_CHART_PAGE",
                    "chart_id": c["id"],
                    "publication_pages": c["publicationPages"],
                    "artifacts": c["assets"]
                    + [{"path": charts["visualMaster"], "sha256": charts["visualMasterSha256"]}],
                }
            ]
            dispositions = (
                "VERIFIED_CHART_PUBLICATION",
                "The chart register explicitly links this Markdown navigation page to the "
                "chart assets and PDF pages; this is a chart representation, not a letterhead"
                " rendering of all Markdown prose.",
                "Reuse the existing registered chart and PDF pages.",
            )
        elif path == packet_dir + "PACKET.md":
            evidence = [
                {
                    "manifest": packet_dir + "manifest.json",
                    "relationship": "MANIFESTED_EVIDENCE_PACKET",
                    "artifacts": [
                        {"path": packet_dir + p, "sha256": h}
                        for p, h in packet["artifacts"].items()
                        if p.endswith((".pdf", ".xlsx"))
                    ],
                    "acceptance": "docs/canon/FINANCE_HUMAN_EVIDENCE_001_ACCEPTANCE_2026-09-11.md",
                    "native_database": packet["native_database"],
                }
            ]
            assert packet_manifest["files"]["PACKET.md"] == sha(source)
            dispositions = (
                "VERIFIED_ACCEPTED_EVIDENCE_PACKET",
                "The packet manifest binds this Markdown, PDF and workbook; the later "
                "acceptance record governs over retained draft labels in the immutable "
                "artifacts.",
                "Reuse exact accepted packet; no expansion of invoice/legal or design scope.",
            )
        else:
            # Exact source-byte identity may establish a snapshot derivative; filename/title
            # similarity never does. Record both source identities, not a current-canon claim.
            for pub in pubs:
                if pub.get("source_sha256") == sha(source):
                    evidence.append(
                        {
                            "manifest": pubpath,
                            "relationship": "EXACT_SOURCE_HASH_PUBLICATION",
                            "manifest_source": pub["source"],
                            "artifacts": [{"path": pub["publication"], "sha256": pub["sha256"]}],
                        }
                    )
            if evidence:
                dispositions = (
                    "VERIFIED_IDENTICAL_SOURCE_PUBLICATION",
                    "This source is byte-identical to the source hash explicitly bound to a "
                    "controlled PDF. Snapshot/history status remains unchanged.",
                    "Reuse the hash-matched publication with the snapshot date and source "
                    "identity explicit.",
                )
            elif "/history/" in path or "/canon_snapshot/" in path:
                dispositions = (
                    "HISTORICAL_COUNTERPART_UNRESOLVED",
                    "Preserved historical/snapshot source; no exact historical publication "
                    "pairing established. A current successor PDF cannot silently stand in for "
                    "this version.",
                    "Preserve source; verify the original versioned release member before "
                    "assigning a counterpart.",
                )
            elif text.startswith("# Superseded filename"):
                dispositions = (
                    "NAVIGATION_ALIAS_NO_PUBLICATION",
                    "This file is a superseded-filename pointer to its successor, not an "
                    "independent corporate instrument.",
                    "Follow its existing successor link; retain the alias for old URLs.",
                )
            elif path.startswith(maintenance_roots) or Path(path).name in maintenance_names:
                dispositions = (
                    "READER_MAINTENANCE_NO_LETTERHEAD",
                    "Repository procedure, build/review record or navigation surface; its "
                    "Markdown is the intended reader/maintainer form under Sources and Formats. "
                    "This disposition is not an exemption for any linked in-universe record.",
                    "Retain Markdown and discovery entry; assess linked corporate records "
                    "separately.",
                )
        for e in evidence:
            for a in e["artifacts"]:
                assert sha(blob(a["path"])) == a["sha256"], a["path"]
        direct = []
        for ref in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in ref or not ref.split("#")[0].endswith((".pdf", ".xlsx")):
                continue
            candidate = os.path.normpath(str(Path(path).parent / ref.split("#")[0]))
            direct.append(
                {
                    "path": candidate,
                    "exists_at_base": candidate in paths,
                    "relationship": "SOURCE_LINK_ONLY_NOT_EQUIVALENCE",
                }
            )
        rows.append(
            {
                "id": "READ-FMT-" + sha(path.encode())[:12].upper(),
                "source": path,
                "title": title,
                "source_sha256": sha(source),
                "disposition": dispositions[0],
                "rationale": dispositions[1],
                "next_action": dispositions[2],
                "manifest_path_matches": matches,
                "direct_publication_links": direct,
                "verified_evidence": evidence,
                "source_state_excerpt": "\n".join(text.splitlines()[:12])[:1200],
                "database_scope": (
                    "Reader discovery metadata only; native financial linkage is "
                    "asserted only where explicitly listed in evidence."
                ),
            }
        )
    assert len(rows) == 448 and len({r["source"] for r in rows}) == 448
    counts = dict(sorted(Counter(r["disposition"] for r in rows).items()))
    data = {
        "record_id": "SH-READER-FORMAT-RECONCILIATION-001",
        "base_revision": revision,
        "queue_path": QUEUE,
        "queue_sha256": sha(queue),
        "scope": (
            "All 448 counterpart-review rows in the pinned queue; its 131 already verified "
            "and 99 existing maintenance records are not reclassified here."
        ),
        "search_scope": (
            "Every tracked JSON manifest/register and docs/releases Markdown index at base; "
            "exact path search and explicit supported adapters. External release bytes were not "
            "downloaded by this audit. An unresolved result is not proof that no counterpart exists."
        ),
        "search_inventory": search_manifest,
        "counts": counts,
        "records": rows,
    }
    outputs = {OUT / "records.json": json.dumps(data, indent=2) + "\n"}
    summary = [
        "# Document counterpart reconciliation",
        "",
        f"**Record:** SH-READER-FORMAT-RECONCILIATION-001 · **Source revision:** `{revision}`.",
        "",
        "All **448** rows from the pinned [format-review "
        "queue](../../wiki/library/format-review.md) have a stable disposition in "
        "[records.json](records.json). This is a completed reconciliation of that "
        "population, not a claim that all missing documents were produced. It does "
        "not rewrite the live generated queue.",
        "",
        "| Disposition | Rows |",
        "|---|---:|",
    ]
    summary += [f"| {k} | {v} |" for k, v in counts.items()]
    summary += [
        "",
        "## What was checked",
        "",
        f"The audit searched {len(texts)} tracked manifest/register JSON files and "
        "release-index Markdown files, retaining every searched file hash. Explicit "
        "organization-register relations, source hashes in the controlled-publication "
        "manifest, and the accepted finance packet manifest establish the verified "
        "counterparts. Every artifact cited as verified was read and hash-checked at "
        "the same source revision.",
        "",
        "A manifest mentioning a Markdown file, a linked PDF, an analogous workbook, "
        "or a similarly named release is only a candidate. The audit records these "
        "links without promoting them to equivalent publications. External release "
        "member bytes were not retrieved in this audit; unresolved rows retain that "
        "exact limitation. A separately recorded [release follow-up](RELEASE_FOLLOW_UP.md) "
        "does not alter these pinned dispositions. Historical source versions are never matched to a "
        "successor solely by title.",
        "",
        "Technical navigation and maintainer records are not in-universe letterhead "
        "documents under [Sources and Formats](../SOURCES_AND_FORMATS.md). Their "
        "disposition applies only to that file. Unpaired policies, contracts, "
        "accounting records and other narrative records remain unresolved unless an "
        "explicit relation is established. No new PDF, workbook or art was generated.",
        "",
        "## Row-by-row review",
        "",
    ]
    groups = {}
    for r in rows:
        key = r["source"].split("/")[0]
        groups.setdefault(key, []).append(r)
    for group, members in sorted(groups.items()):
        file = f"{group.replace('.', '')}-records.md"
        summary.append(f"- [{group}: {len(members)} records]({file})")
        lines = [
            f"# {group} counterpart dispositions",
            "",
            "[Reconciliation scope and methods](README.md)",
            "",
            "| Source | Disposition | Counterpart or next action |",
            "|---|---|---|",
        ]
        for r in members:
            parts = []
            for e in r["verified_evidence"]:
                parts += [
                    f"[{Path(a['path']).name}]({link(a['path'])})"
                    for a in e["artifacts"]
                    if a["path"].endswith((".pdf", ".xlsx"))
                ]
            detail = ", ".join(parts) if parts else r["next_action"]
            lines.append(
                f"| [{r['title'].replace('|', '/')} ]({link(r['source'])})"
                f"<br>`{r['id']}` | {r['disposition']} | {detail} |"
            )
        outputs[OUT / file] = "\n".join(lines) + "\n"
    summary += [
        "",
        "## Reproduce and check",
        "",
        "```bash",
        "python docs/reader/reconciliation/build.py",
        "python docs/reader/reconciliation/build.py --check",
        "```",
        "",
        "The pinned source commit is deliberately fixed. A successor audit must "
        "record a new queue revision and reconcile additions/removals explicitly; "
        "regenerating the shared catalog does not retroactively change this "
        "inventory. Shared catalog integration remains the main integrator’s "
        "responsibility.",
    ]
    outputs[OUT / "README.md"] = "\n".join(summary) + "\n"
    for path, content in outputs.items():
        if check:
            assert path.read_text() == content, f"Stale reconciliation: {path}"
        else:
            path.write_text(content)
    print(
        f"PASS: {len(rows)} unique queue records; {counts}; "
        f"{len(texts)} search inputs; artifact hashes verified."
    )


if __name__ == "__main__":
    import sys

    main("--check" in sys.argv)
