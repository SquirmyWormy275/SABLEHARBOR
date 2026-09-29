"""Pinned geographic-authority review of sources added since evidence 1.4.0.

This is a source disposition, not a new property survey or a domain audit.
Run ``python -m geospatial.successor_20260928.source_delta`` from a checkout
containing both pinned Git revisions.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

from tools.evidence.inventory import fingerprints, tree

ROOT = Path(__file__).resolve().parents[2]
FROM = "dff38f04131b8f10cd62b543becb71aec5a7080a"
THROUGH = "3dd5e15f58d39b28291782bde5bf4dbf3744a03e"
OUTPUT = Path(__file__).parent

# Each accepted canon delta in this interval was read as a complete document.
# These findings describe only its geographic authority and preserve other domains.
CANON_FINDINGS = {
    "ADVISORY_LEGAL_IMPLEMENTATION_2026-09-22.md": "Advisory remains an SHI business line; customer engagements and trademark research create no Sable Harbor premise or new site. The sponsor plan has no geographic property effect.",
    "ARU_ADMINISTRATIVE_COMPLETION_2026-09-22.md": "Taylor terminal and warehouse fixture attachments reuse existing accepted polygons. Rawlins equipment location, synthetic title references and modeled filings do not convey land, create a new parcel or prove real priority.",
    "ARU_SECURED_FINANCING_SUCCESSOR_2026-09-22.md": "The ARU collateral schedule identifies goods and six track fixtures; seven aggregate facility records are context, not seven newly owned parcels. The security grant excludes underlying land and buildings.",
    "CAPITAL_DESIGNATION_RIGHTS_2026-09-22.md": "Investor designation and unit rights have no site, occupancy or land-right effect.",
    "COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md": "Corporate tax and capital directions preserve the existing Delaware LLC and Sacramento headquarters; they do not create another premise. Voice/decision dates are not property-entry dates.",
    "CRADLE_HOST_TERMS_2026-09-22.md": "Demotte and Kelly Gang remain separate external hosts. Prospective work orders and exit terms neither convey their sites to Cradle nor change Bedford's accepted footprint.",
    "GEOGRAPHIC_COMPLETION_2026-09-13.md": "The accepted 34-site/component disposition and three fictional selected footprints control at their stated precision. The 1898, 1954 and abandoned rail alignments stay unlocated; no actual parcel or survey right is established. Its former exterior-image sentence is superseded by the later withdrawal.",
    "HEADQUARTERS_VISUAL_WITHDRAWAL_2026-09-22.md": "The owner withdrew the exterior image and its recovery requirement. Sacramento site identity and geometry remain; neither the old image nor a replacement is a current required geographic source.",
    "J2_PERSONNEL_COMPLETION_2026-09-22.md": "Fictional biographies and company joining years do not establish Sable Harbor tenure at earlier third-party places or new J2 premises.",
}

# These changed records contain material location or site-adjacent facts. Their
# exact files were inspected separately from the accepted canon documents.
DOMAIN_FINDINGS = {
    "enterprise/operations/source/current_company_2026_08.json": "August Cradle host, Bedford processing and customer chronology are operating/custody facts; external host remains external and no additional site is created.",
    "enterprise/operations/source/completed_period_2026_08.json": "Authored Pittsburgh/Fairmont employee residence facts support local payroll analysis, not a precise Fort or Bedford parcel or new employer facility.",
    "enterprise/operations/source/debt_host_2026_08.json": "Kelly Gang and Demotte performance/settlement records retain external operator ownership; no host facility transfers to Cradle.",
    "enterprise/closeout/source/escrow_register.json": "Escrow and property-related holdbacks remain conditional; recorded sums do not convey title, release a bond or change site occupancy.",
    "enterprise/closeout/source/debt_administration_2026_09_22.json": "ARU collateral administration references existing Taylor/Rawlins assets; synthetic case filing and location records do not establish real title or additional land.",
    "enterprise/closeout/source/state_apportionment.json": "Tax jurisdiction/activity factors do not establish a street address, tenure or a new site.",
    "enterprise/closeout/source/california_qualifications.json": "California entity qualification and filing state are legal/tax records, not evidence of an additional occupied California premise.",
    "enterprise/closeout/source/software_sales_tax.json": "Fictional Sacramento correspondence strings are explicitly not property/geocoding evidence; city-level user tax situs is a separate commercial assertion.",
    "enterprise/ccf/company_closeout/synthetic_permit_instruments_august.json": "Fictional Red Wash authority records attach conditions to existing activities; they do not locate a new mine or supply real government permits.",
    "enterprise/ccf/company_closeout/september_shipment_qualification.json": "Shipment qualification preserves custody and recipient gates; a shipment route is not a new owned rail segment or licensed site.",
    "enterprise/ccf/company_closeout/activity_applicability.json": "Fort, Bedford, external hosts and selected/planned runtime sites retain distinct duty states. Applicability names no new property title or commissioned provider.",
    "enterprise/ccf/company_closeout/industrial_transaction_tax.json": "Synthetic seller and buyer correspondence addresses are tax documents, not new operating sites or geocodable premises.",
}


def disposition(path: str) -> tuple[str, str]:
    if path.startswith("docs/canon/"):
        return "FULL_TEXT_CANON_GEOGRAPHIC_REVIEW", CANON_FINDINGS[Path(path).name]
    if path in DOMAIN_FINDINGS:
        return "TARGETED_DOMAIN_GEOGRAPHIC_REVIEW", DOMAIN_FINDINGS[path]
    if path.startswith(("geospatial/", "geography/")):
        return (
            "GEOGRAPHIC_SOURCE_OR_DERIVATIVE",
            "Retain its own source/release status. This path inventory does not accept new geometry or replace native geographic validation.",
        )
    if path.startswith(("enterprise/", "industrial/", "red_wash/", "docs/legal/", "docs/finance/")):
        return (
            "DOMAIN_SOURCE_BOUNDARY",
            "Owning-domain source or derivative; no independent property, site or rail-network authority is inferred from this path classification.",
        )
    if path.startswith(("docs/", "wiki/", "reader/")):
        return (
            "DOCUMENT_OR_PUBLICATION_BOUNDARY",
            "Read under accepted canon and its own publication status; a copied claim or illustration is not independent geographic evidence.",
        )
    return (
        "IMPLEMENTATION_OR_CONTEXT_BOUNDARY",
        "Exact changed path and bytes retained; classification alone neither establishes geographic truth nor certifies another domain.",
    )


def build() -> dict:
    before, after = tree(ROOT, FROM), tree(ROOT, THROUGH)
    paths = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    canon = {Path(p).name for p in paths if p.startswith("docs/canon/")}
    if canon != set(CANON_FINDINGS):
        raise ValueError(f"Canon delta population changed: {sorted(canon ^ set(CANON_FINDINGS))}")
    if not set(DOMAIN_FINDINGS) <= set(paths):
        raise ValueError("A reviewed domain source is absent from the pinned delta")
    oids = sorted({oid for p in paths for oid in (before.get(p), after.get(p)) if oid})
    hashes = {}
    for index in range(0, len(oids), 64):
        hashes.update(fingerprints(ROOT, oids[index : index + 64]))
    rows = []
    for path in paths:
        state, finding = disposition(path)
        old, new = before.get(path), after.get(path)
        rows.append(
            {
                "source_path": path,
                "change": "ADDED" if old is None else "REMOVED" if new is None else "MODIFIED",
                "from_blob": old,
                "through_blob": new,
                "from_sha256": hashes[old][1] if old else None,
                "through_sha256": hashes[new][1] if new else None,
                "review_level": state,
                "geographic_finding": finding,
            }
        )
    levels = Counter(r["review_level"] for r in rows)
    return {
        "prior_geographic_review_through": FROM,
        "successor_review_through": THROUGH,
        "review_date": "2026-09-28",
        "scope": "Complete changed-path/fingerprint inventory; full-text review of every changed controlling canon document and targeted review of twelve site-adjacent company sources. Other files receive an explicit authority-boundary classification, not a substantive audit.",
        "rows": rows,
        "summary": {
            "changed_paths": len(rows),
            "canon_full_text": levels["FULL_TEXT_CANON_GEOGRAPHIC_REVIEW"],
            "targeted_domain": levels["TARGETED_DOMAIN_GEOGRAPHIC_REVIEW"],
            "review_levels": dict(sorted(levels.items())),
        },
        "remaining": "Detailed rail/site engineering under issue 107 remains. This ledger, its tests and navigation are derivatives of the pinned review, not new geographic source facts. Later independently accepted substantive geographic sources require review; this ledger alone does not close issue 108.",
    }


def write() -> dict:
    result = build()
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    (OUTPUT / "SOURCE_DELTA.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    (OUTPUT / "SUMMARY.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(write()["summary"], indent=2, sort_keys=True))
