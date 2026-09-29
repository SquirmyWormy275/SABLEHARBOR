#!/usr/bin/env python3
"""Dated fictional appointments and bounded vector-master successor migration.

The accepted 1.1.0 PDF/source are preserved verbatim. This migration adds office
occupants under delegated authoring authority; it does not assert Board signatures
or owner acceptance of the successor artwork. Existing financial bytes are unused.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import fitz

from tools.organization.adopt_j2_leadership_20260910 import insert, spans

ROOT = Path(__file__).resolve().parents[2]
DECISION = "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md"
ROSTER = "docs/structured/enterprise_leadership_2026-09-13.json"
# Exact accepted baseline; retaining the literal here makes reruns fail closed.
BASE_PDF_SHA = "352dfa4f1247f6089d340b19940f75758a666dce14f239fb38b1c2a300aaa38b"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def apply():
    source_path = ROOT / "docs/organization/source/chartbook.json"
    before_source = source_path.read_bytes()
    source = json.loads(before_source)
    if source["publication_revision"] == "1.2.0":
        assert sha((ROOT / source["visual_master"]).read_bytes()) == source["visual_master_sha256"]
        print("Enterprise migration already applied; no files changed.")
        return
    master = ROOT / source["visual_master"]
    before_pdf = master.read_bytes()
    if source["publication_revision"] != "1.1.0" or sha(before_pdf) != BASE_PDF_SHA:
        raise ValueError("Unexpected accepted visual baseline")
    proposal = json.loads(
        (
            ROOT
            / "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json"
        ).read_text()
    )
    roster = {
        **proposal,
        "record_id": "SH-ENTERPRISE-PPL-20260913",
        "version": "1.0.0",
        "canonical_source": DECISION,
        "repository_acceptance_status": "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE",
        "authority": "Owner-authorized audit-suite handover sections 3.1, 3.3 and 22; ordinary fictional role completion",
        "state_on_accepted_merge": "LOCKED_CURRENT_APPOINTMENTS_ONLY",
        "actual_employment_census": None,
        "incremental_forecast_positions": 0,
        "incremental_forecast_payroll_usd": 0,
        "occupied_workplaces_assigned": 0,
        "employment_start_dates": "NOT_ESTABLISHED",
        "people": [],
    }
    groups = Counter()
    old_roles = {r["id"]: r for r in source["register_only"]}
    for p in proposal["people"]:
        groups[p["forecast_group"]] += 1
        evidence = [
            {
                "path": DECISION,
                "section": "Dated appointments",
                "evidence": f"{p['person_id']}: {p['name']}, {p['title']}, effective 2026-09-13",
            }
        ]
        person = {
            **p,
            "joined_year": None,
            "employment_start": None,
            "appointment_date": "2026-09-13",
            "status": "current_employee",
            "source_acceptance": roster["repository_acceptance_status"],
            "forecast_position_id": f"SYN-{p['forecast_group'].upper()}-{groups[p['forecast_group']]:03}",
            "workplace_assignment": None,
            "workplace_status": "UNASSIGNED_NOT_OCCUPIED",
            "sources": evidence,
        }
        roster["people"].append(person)
        source["nodes"].append(
            {
                "id": p["person_id"],
                "person_id": p["person_id"],
                "type": "person",
                "name": p["name"],
                "title": p["title"],
                "joined_year": None,
                "source_record_id": p["person_id"],
                "role_id": p["org_role_id"],
                "sources": evidence,
                "status": "current_employee",
                "title_state": "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE",
                "year_basis": "Company joining year not established; appointment date is not a joining year",
                "notes": [
                    "Dated fictional source addition; branch acceptance remains pending. No incremental position or occupied workplace."
                ],
            }
        )
    resolved = {p["org_role_id"] for p in proposal["people"]}
    roster["resolved_role_records"] = [old_roles[r] for r in sorted(resolved & old_roles.keys())]
    source["register_only"] = [r for r in source["register_only"] if r["id"] not in resolved]
    archive = ROOT / "docs/organization/history/v1.1.0"
    if archive.exists():
        raise ValueError("Historical successor archive already exists; inspect before migration")
    archive.mkdir(parents=True)
    (archive / master.name).write_bytes(before_pdf)
    (archive / "chartbook.json").write_bytes(before_source)
    write(
        archive / "manifest.json",
        {
            "publication_revision": "1.1.0",
            "base_commit": "325fdc8a25ab8ba8d74bf4b62d6853e703cfecd8",
            "status": "PRESERVED_ACCEPTED_PUBLICATION",
            "artifacts": [
                {
                    "original_path": source["visual_master"],
                    "preserved_path": str((archive / master.name).relative_to(ROOT)),
                    "sha256": sha(before_pdf),
                },
                {
                    "original_path": str(source_path.relative_to(ROOT)),
                    "preserved_path": str((archive / "chartbook.json").relative_to(ROOT)),
                    "sha256": sha(before_source),
                },
            ],
        },
    )
    original = fitz.open(stream=before_pdf, filetype="pdf")
    doc = fitz.open(stream=before_pdf, filetype="pdf")
    assert len(doc) == 57
    chart = next(c for c in source["charts"] if c["slug"] == "people-enterprise")
    template = chart["pages"][0]
    for offset in range(0, 15, 6):
        people = roster["people"][offset : offset + 6]
        doc.insert_pdf(original, from_page=40, to_page=40)
        page = doc[-1]
        for card in template["cards"]:
            page.add_redact_annot(fitz.Rect(card["bounds"]) + (-2, -2, 2, 2), fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=2)
        cards = []
        regular = next(f for f in page.get_fonts(full=True) if f[3].endswith("Roboto-Regular"))
        font = fitz.Font(fontbuffer=doc.extract_font(regular[0])[3])
        for person, card in zip(people, template["cards"]):
            r = fitz.Rect(card["bounds"])
            page.draw_rect(r, color=(211 / 255, 217 / 255, 221 / 255), fill=(1, 1, 1), width=0.8)
            insert(page, person["name"], (r.x0 + 24, r.y0 + 49), 18, True)
            words = person["title"].split()
            lines = [""]
            for word in words:
                candidate = (lines[-1] + " " + word).strip()
                if font.text_length(candidate, fontsize=14.5) > r.width - 48:
                    lines.append(word)
                else:
                    lines[-1] = candidate
            if len(lines) > 2:
                raise ValueError("Title exceeds preserved two-line card geometry")
            for number, line in enumerate(lines):
                insert(page, line, (r.x0 + 24, r.y0 + 73.5 + 17 * number), 14.5)
            insert(
                page,
                "Year not recorded",
                (r.x0 + 24, r.y0 + 115 if len(lines) == 2 else r.y0 + 103),
                13,
                color=5661034,
            )
            cards.append({"node_id": person["person_id"], "bounds": list(r)})
            chart["node_ids"].append(person["person_id"])
        chart["pages"].append({"page": len(doc), "cards": cards})
    chart["sources"].append(DECISION)
    chart["notes"] += [
        "September 13 delegated appointments fill existing support offices; employment start years and occupied workplaces remain unestablished.",
        "Internal Audit retains Board Audit & Compliance oversight; J2 remains outside ESS. Membership is not an operating approval delegation.",
    ]
    for number in range(len(doc)):
        page = doc[number]
        date = next(s for s in spans(page) if s["text"] == "2026-09-10 / v1.1.0")
        pagination = next(s for s in spans(page) if re.fullmatch(r"\d+ / 57", s["text"]))
        for item in (date, pagination):
            page.add_redact_annot(fitz.Rect(item["bbox"]) + (-1, -1, 1, 1), fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        insert(page, "2026-09-13 / v1.2.0", date["origin"], 10.5, color=5661034)
        insert(page, f"{number + 1} / 60", pagination["origin"], 10.5, color=5661034)
    after = doc.tobytes(garbage=4, deflate=True, no_new_id=True)
    master.write_bytes(after)
    source.update(
        publication_revision="1.2.0",
        as_of="2026-09-13",
        visual_master_sha256=sha(after),
        visual_master_git_blob=hashlib.sha1(f"blob {len(after)}\0".encode() + after).hexdigest(),
        publication_status="delegated-source-successor-engineering-review-pending-owner-acceptance",
    )
    write(source_path, source)
    write(ROOT / ROSTER, roster)
    print("Authored fifteen dated occupants and preserved vector successor, 60 pages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()
    apply()
