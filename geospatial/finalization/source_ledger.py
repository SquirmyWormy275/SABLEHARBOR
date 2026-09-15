"""Verify the reviewed source boundary and expose per-file geographic dispositions."""

import csv
import gzip
import json
from pathlib import Path
from collections import Counter
from geospatial.finalization.screen import BASE, ROOT
from tools.evidence.inventory import tree, fingerprints

REVISION = "dff38f04131b8f10cd62b543becb71aec5a7080a"
BASELINE = "d91a22c35c91b213204411421de88815f27d8e16"
CANON_FINDINGS = {
    "ADVISORY_ATLAS_MERIDIAN_CLOSEOUT_2026-09-08.md": "Atlas Meridian is a product organization; Advisory delivery does not establish an additional office or pooled staff estate.",
    "BUSINESS_DEVELOPMENT_DIRECTION_2026-09-09.md": "Opportunity qualification and customer work do not establish title, a campus or an occupied office.",
    "CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md": "Version/SHMS closure update preserves Sacramento headquarters and its accepted campus constraints.",
    "DECISION_REGISTER_ADDENDUM_2026-09-08_ADVISORY.md": "Advisory delivery governance; no additional owned geographic estate.",
    "DECISION_REGISTER_ADDENDUM_2026-09-09_ADVISORY_TIER1.md": "Tier-one consulting gates and operating boundaries; no new physical office.",
    "FINANCE_HUMAN_EVIDENCE_001_ACCEPTANCE_2026-09-11.md": "Acceptance of finance evidence does not execute an external property transaction or establish occupancy.",
    "FOUNDRY_FIELD_BILLING_ADOPTION_2026-09-13.md": "Fictional correspondence addresses explicitly excluded from geocoding, registered-office and occupancy evidence. Conditional 2027 model is not external execution.",
    "J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md": "Leadership effective dates do not establish campus opening or residential occupancy.",
    "KLEIN_FORT_OCCUPANCY_2026-09-13.md": "Accepted 2021 shop continuity after the 2022 recharter; separate Fort move and shop vacancy during 2024, with exact days unknown.",
    "NORTHSTAR_MINERALS_VISUAL_IDENTITY_2026-09-07.md": "External client identity and approved artwork; no transfer of its sites or assets.",
    "ORG_CHART_DESIGN_AND_CLEANUP_2026-09-09.md": "Organizational diagram scope; chart groupings do not indicate co-location or ownership of external entities.",
    "READER_OVERNIGHT_SCOPE_2026-09-11.md": "Reader publication and evidence boundaries; current geographic delegation supplies the later authority for geographic decisions only.",
    "RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md": "Three existing runtime records: selected providers do not imply contracts or commissioned operations; Northern Nevada land is acquired/preconstruction.",
    "RUNTIME_RECONCILIATION_INDEX_2026-09-11.md": "Index of accepted runtime decisions, not independent corroboration or a new location.",
    "SACRAMENTO_VISITOR_MAP_V08_ACCEPTANCE_2026-09-11.md": "Approved V08 artwork is immutable illustration, not surveyed building geometry or a new site selection.",
    "THIRD_PARTY_SERVICES_IMPLEMENTATION_SCOPE_2026-09-09.md": "Provider sourcing and internal readiness are separate from purchases, contracts and externally executed services.",
    "THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md": "Earlier sourcing state yields to the September 11 runtime decisions; no provider selection creates occupancy.",
}


def role(path):
    """Disposition describes geographic authority, never a claim of full domain audit."""
    if path.startswith("docs/canon/"):
        return "CONTROLLING_CANON_DELTA_REVIEWED", CANON_FINDINGS[Path(path).name]
    if path.startswith(
        (
            "docs/legal/",
            "legal/",
            "finance/",
            "docs/finance/",
            "enterprise/ccf/",
            "enterprise/runtime/",
        )
    ):
        return (
            "DOMAIN_RECORD_CANON_BOUNDED",
            "Retain owning-domain evidence. Geographic authority is bounded by the reviewed controlling canon; financial, compliance and publication records do not independently establish physical tenure or external execution.",
        )
    if path.startswith(("geospatial/", "geography/")):
        return (
            "GEOGRAPHIC_IMPLEMENTATION_OR_ARCHIVE",
            "Retain feature/source provenance and dated release scope; generated maps and source copies are not independent corroboration. Current geometry and temporal behavior are checked by the geographic suite.",
        )
    if path.startswith(("docs/org/", "reader/", "wiki/", "docs/reader/")) or Path(
        path
    ).suffix.lower() in {".png", ".jpg", ".pdf", ".svg", ".webp", ".docx"}:
        return (
            "PUBLICATION_OR_VISUAL_REPRESENTATION",
            "Retain source/brand identity and published date. Publication, diagram membership and decoration do not establish location or tenure; current controlling canon governs geographic interpretation.",
        )
    if Path(path).suffix in {
        ".py",
        ".js",
        ".mjs",
        ".ts",
        ".yml",
        ".yaml",
        ".toml",
        ".lock",
    } or path.startswith((".github/", "scripts/", "tools/", "tests/")):
        return (
            "IMPLEMENTATION_OR_VALIDATION",
            "Code/configuration/test or delivery input; not an independent geographic assertion.",
        )
    return (
        "CONTEXT_RECORD_CANON_BOUNDED",
        "Retained contextual record with exact revision and bytes. Earlier proposals and operational examples yield to accepted canon; this disposition is geographic relevance review, not full legal, financial or technical certification.",
    )


def build():
    old, current = tree(ROOT, BASELINE), tree(ROOT, REVISION)
    paths = sorted(p for p in old.keys() | current.keys() if old.get(p) != current.get(p))
    canon = {Path(p).name for p in paths if p.startswith("docs/canon/")}
    if canon != set(CANON_FINDINGS):
        raise ValueError("Reviewed canon delta population changed")
    hashes = {}
    oids = sorted(set(old.values()) | set(current.values()))
    for i in range(0, len(oids), 100):
        hashes.update(fingerprints(ROOT, oids[i : i + 100]))
    baseline = []
    for row in csv.DictReader((ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open()):
        p = row["source_path"]
        if hashes[old[p]] != (int(row["bytes"]), row["file_sha256"]):
            raise ValueError("Baseline source mismatch: " + p)
        baseline.append(
            {
                **row,
                "disposition": "BASELINE_GEOGRAPHIC_REVIEW_RECONCILED",
                "basis": "Six disjoint fixed carrier batches; catalog source claims; 97 baseline image roles and 109 container inventories; final 135-image/290-appearance visual review; recovered non-premises references.",
                "limit": "Census coverage is geographic review, not blanket acceptance of every statement in this source. Empty discovery populations are not proof of absent geographic meaning.",
            }
        )
    if {r["source_path"] for r in baseline} != set(old):
        raise ValueError("Incomplete baseline source population")
    changes = []
    for p in paths:
        disposition, finding = role(p)
        changes.append(
            dict(
                source_path=p,
                change="ADDED" if p not in old else "REMOVED" if p not in current else "MODIFIED",
                baseline_git_blob=old.get(p),
                current_git_blob=current.get(p),
                baseline_sha256=hashes[old[p]][1] if p in old else None,
                current_sha256=hashes[current[p]][1] if p in current else None,
                disposition=disposition,
                geographic_finding=finding,
            )
        )
    return dict(
        baseline_revision=BASELINE,
        reviewed_main_revision=REVISION,
        baseline_sources=baseline,
        subsequent_changes=changes,
        summary=dict(
            baseline_files=len(baseline),
            subsequent_changes=len(changes),
            canon_deltas=len(canon),
            dispositions=dict(Counter(r["disposition"] for r in changes)),
            scope="Complete per-file geographic disposition ledger through the pinned accepted main; only the 17 controlling canon deltas claim full-text delta review. Other rows explicitly retain their domain/derivation boundary. Later commits require a new review; no automatic approval of future sources.",
        ),
    )


def write(output):
    result = build()
    output.mkdir(parents=True, exist_ok=True)
    (output / "SOURCE_LEDGER.json.gz").write_bytes(
        gzip.compress(json.dumps(result, ensure_ascii=False).encode(), mtime=0)
    )
    (output / "SOURCE_LEDGER_SUMMARY.json").write_text(
        json.dumps(result["summary"], indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(write(BASE)["summary"], indent=2))
