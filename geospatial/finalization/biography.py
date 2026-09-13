"""Retain geographic biography references without inventing corporate premises."""

import hashlib
import subprocess

from geospatial.finalization.prospects import ROOT, REVISION

SPECS = [
    (
        "SH-REF-0027",
        "BTC career geography",
        "South Africa",
        "industrial/pale_sun/01_VILANDER_BIOGRAPHY.md",
        "He joined the South African security company known here only as BTC",
        "COUNTRY",
        "FICTIONAL_IN_REAL_GEOGRAPHY",
    ),
    (
        "SH-REF-0028",
        "DeMotte / agricultural Midwest biography",
        "DeMotte, Indiana; agricultural Midwest",
        "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md",
        "Van der Velde is a Dutch immigrant",
        "CITY_OR_REGION",
        "REAL_WORLD_REFERENCE",
    ),
    (
        "SH-REF-0029",
        "Kansas State education reference",
        "Kansas State; precise campus or attendance dates unspecified",
        "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md",
        "Van der Velde is a Dutch immigrant",
        "INSTITUTIONAL_REFERENCE",
        "REAL_WORLD_REFERENCE",
    ),
    (
        "SH-REF-0031",
        "Gid Voss 2018 coal-preparation customer incident",
        "Unnamed coal preparation plant; region unspecified",
        "docs/canon/WILLOW_KLEIN_CLOSEOUT_2026-09-06.md",
        "Gid Voss's defining pre-Klein Sable Harbor incident",
        "INTENTIONALLY_UNLOCATED",
        "FICTIONAL",
    ),
    (
        "SH-REF-0030",
        "Harvard Business School education reference",
        "Harvard Business School; precise premises and attendance dates unspecified",
        "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md",
        "Van der Velde is a Dutch immigrant",
        "INSTITUTIONAL_REFERENCE",
        "REAL_WORLD_REFERENCE",
    ),
]


def sync(catalog):
    ids = {r[0] for r in SPECS}
    catalog["objects"] = [r for r in catalog["objects"] if r["object_id"] not in ids]
    catalog["sources"] = [
        r for r in catalog["sources"] if not r["source_id"].startswith("SRC-GFC-BIO-")
    ]
    for index, (oid, name, place, path, prefix, precision, fictionality) in enumerate(
        SPECS, 1
    ):
        raw = subprocess.check_output(["git", "show", REVISION + ":" + path], cwd=ROOT)
        hits = [
            (i, line)
            for i, line in enumerate(raw.decode().splitlines(), 1)
            if line.startswith(prefix)
        ]
        if len(hits) != 1:
            raise ValueError("Ambiguous biography source: " + path)
        line, text = hits[0]
        sid = f"SRC-GFC-BIO-{index:03}"
        limit = {
            "SH-REF-0027": "Former-employer career geography only. BTC is fictional; its expanded legal name and exact premises are unspecified. No current company ownership, deployment or office is established.",
            "SH-REF-0028": "Biographical regional reference, distinct from Demotte Reclamation Services in West Virginia. Nationality does not establish a birthplace; no corporate occupancy is established.",
            "SH-REF-0029": "Educational reference only; campus and attendance dates are unknown. Corporate occupancy is not applicable.",
            "SH-REF-0030": "Educational opportunity reference only; no campus, attendance period, graduation or company premises are inferred.",
            "SH-REF-0031": "Year-bounded customer incident at an unnamed coal preparation plant. The region, premises and tenure are unknown; this is not Klein, the Fort or Emberline.",
        }[oid]
        catalog["sources"].append(
            dict(
                source_id=sid,
                title=name,
                publisher_or_author="Sable Harbor synthetic corporate record",
                source_type="ACCEPTED_BIOGRAPHICAL_RECORD",
                publication_date=None,
                accessed_date="2026-09-13",
                url_or_repo_path=path,
                repository_commit=REVISION,
                file_sha256=hashlib.sha256(raw).hexdigest(),
                license="Repository synthetic project material",
                citation=path,
                coverage=place,
                source_quality="EXACT_ACCEPTED_SOURCE",
                notes=limit,
            )
        )
        catalog["objects"].append(
            dict(
                object_id=oid,
                canonical_name=name,
                object_type="CAREER_GEOGRAPHIC_REFERENCE",
                entity_id=None,
                place=place,
                granularity=precision,
                census_status="CONSTRAINED",
                canon_status="CANON_CONSTRAINED",
                fictionality=fictionality,
                source_id=sid,
                source_path=path,
                source_commit=REVISION,
                source_locator=f"line:{line}",
                exact_source_wording=text,
                relevant_date="2018" if oid == "SH-REF-0031" else "",
                date_precision="YEAR" if oid == "SH-REF-0031" else "UNKNOWN",
                conflict_id="",
                next_action="Retain named reference; corporate occupancy is not applicable.",
                notes=limit,
                decision_id="GEO-COMPLETE-20260913",
            )
        )
        catalog["claims"].append(
            dict(
                claim_id=f"CLM-GFC-BIO-{index:03}",
                object_id=oid,
                source_id=sid,
                source_locator=f"line:{line}",
                exact_source_wording=text,
                claim_status="CANON_CONSTRAINED",
                notes=limit,
            )
        )
    return catalog
