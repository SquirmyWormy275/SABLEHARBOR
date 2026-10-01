"""Pin the next accepted geographic-authority source interval for issue #108."""

from __future__ import annotations

import gzip
import io
import json
from collections import Counter
from pathlib import Path

from tools.evidence.inventory import fingerprints, tree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROM = "3dd5e15f58d39b28291782bde5bf4dbf3744a03e"
THROUGH = "e4ed29b2b6410e4c736b90dddef37a735487dada"

CANON_FINDINGS = {
    "docs/canon/COMPANY_SYNTHETIC_SCOPE_DISPOSITION_2026-09-29.md": "Full-text review: the new controlling issue #18 scope record distinguishes the synthetic company edition from unestablished real tax/legal execution. It changes no site, occupancy, railway, parcel, right of way, client footprint or rail-design authority. Its future external transaction boundary cannot establish real rail land rights."
}

FINDINGS = {
    "enterprise/operations/source/portal_2027_common_boundary_2026_09_29.json": "SHI local identity/recovery reference scope names Reno, Boise and northern Nevada runtime designs but confirms no 2027 operating host, contract or new occupied site. A design site ID does not create a parcel.",
    "enterprise/operations/source/portal_2027_iam_opening_2026_09_29.json": "Prospective 2027 ESS service identity and payroll case population; no newly located employer premise or operated data center is established.",
    "enterprise/operations/source/portal_2027_payroll_release_q1_2026_09_29.json": "Two SHI ESS payroll-release role accounts are a scenario function, not new Sacramento premises or site occupancy evidence.",
    "enterprise/operations/source/portal_2027_payroll_release_q1_successor_2026_09_29.json": "Selected Q1 ESS identity/JML successor remains a future fictional case. Its human/service joins do not certify a physical site or real host operation.",
    "enterprise/operations/source/portal_2027_reference_controls_case_2026_09_29.json": "Local nonpersonal reference lab expressly has no physical site ID or real deployment; its nine selected due windows do not activate Reno/Boise or create a company-wide facility census.",
    "industrial/successors/rail_2026_09_29/source.json": "Dated synthetic operating-geometry selector retains 40 total route-miles, 11 stable segment IDs, 26 structure IDs and the nine-mile truck-only mine road. Route split changes to 33.155448786/4.136588436/2.707962778 miles; no land right or new in-service lead is supplied.",
    "industrial/successors/rail_2026_09_29/reperform-result.json": "The three-route successor reperforms 180 planning months and 13 financial datasets; complete-route March 2027 downside capacity stays 1,008 cars and modeled journal/cash/tax delta is zero. It is not historical survey or property evidence.",
    "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson": "Fixed-control synthetic candidate holds endpoints, junctions and 26 structure coordinates at 40 route-miles. Proposed local leads/ladders remain out of service; no real title, surveyed boundary or external client parcel is created.",
    "geospatial/engineering_review/historical_alignment_2026_09_29/source.json": "Provisional southwest 1954 survivor/abandoned-line alternative is newly authored fiction. Accepted 1898 extent and recovered 1954/abandoned locations remain unknown; no current asset or real ROW is inferred.",
    "docs/legal/EXTERNAL_EXECUTION_FACT_TEST_2026-09-29.md": "External tax/trademark execution fact test describes absent real taxpayer/filing/clearance evidence; it supplies no property or railway access instrument.",
    "docs/internal/company-closeout/evidence/rail-source-consumer-2026-09-29/crosswalk-result.json": "Independent old/new segment and structure crosswalk supports the synthetic 40-mile route-source transition. It is a derived geometry check, not a real survey or new asset acquisition.",
}


def disposition(path: str) -> tuple[str, str]:
    if path in CANON_FINDINGS:
        return "CONTROLLING_CANON_FULL_TEXT_GEOGRAPHIC_REVIEW", CANON_FINDINGS[path]
    if path in FINDINGS:
        return "TARGETED_GEOGRAPHIC_SOURCE_REVIEW", FINDINGS[path]
    if path.startswith("docs/canon/"):
        raise ValueError(f"Changed controlling canon lacks full geographic review: {path}")
    if path.startswith(("geospatial/", "industrial/successors/rail_2026_09_29/")):
        return (
            "GEOGRAPHIC_ENGINEERING_OR_DERIVATIVE",
            "Retain exact native source/candidate status; this changed-path review does not itself adopt geometry, certify construction or supply land rights.",
        )
    if path.startswith(("enterprise/", "industrial/", "docs/legal/")):
        return (
            "OWNING_DOMAIN_SOURCE_OR_DERIVATIVE",
            "Preserve the source's own effective/availability and domain authority. This path classification alone establishes no new site, occupancy, rail segment or parcel.",
        )
    if path.startswith(("docs/", "wiki/")):
        return (
            "DOCUMENT_OR_PUBLICATION_BOUNDARY",
            "Reader/publication or other-domain record; repetition of a geographic claim is not independent spatial evidence.",
        )
    return (
        "IMPLEMENTATION_OR_TEST_BOUNDARY",
        "Exact path and bytes are inventoried, without promoting code/tests to a source of property or historical geography.",
    )


def build() -> dict:
    before, after = tree(ROOT, FROM), tree(ROOT, THROUGH)
    paths = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if len(paths) != 83 or not set(FINDINGS) <= set(paths):
        raise ValueError("Pinned changed-path or targeted-source population differs")
    if {p for p in paths if p.startswith("docs/canon/")} != set(CANON_FINDINGS):
        raise ValueError("Controlling canon delta lacks full geographic review")
    oids = sorted({oid for p in paths for oid in (before.get(p), after.get(p)) if oid})
    hashes = {}
    for index in range(0, len(oids), 64):
        hashes.update(fingerprints(ROOT, oids[index : index + 64]))
    rows = []
    for path in paths:
        old, new = before.get(path), after.get(path)
        level, finding = disposition(path)
        rows.append(
            {
                "source_path": path,
                "change": "ADDED" if old is None else "REMOVED" if new is None else "MODIFIED",
                "from_blob": old,
                "through_blob": new,
                "from_sha256": hashes[old][1] if old else None,
                "through_sha256": hashes[new][1] if new else None,
                "review_level": level,
                "geographic_finding": finding,
            }
        )
    levels = Counter(r["review_level"] for r in rows)
    return {
        "record_id": "SH-GEO-SOURCE-DELTA-20260929-001",
        "from_accepted_main": FROM,
        "through_accepted_main": THROUGH,
        "review_date_utc": "2026-09-29",
        "scope": "All changed paths and exact blob/SHA-256 identities; targeted geographic-authority review of eleven material sources and full-text geographic review of the one changed controlling canon source. Other-domain rows retain explicit classification limits.",
        "rows": rows,
        "summary": {
            "changed_paths": len(rows),
            "targeted_geographic_sources": levels["TARGETED_GEOGRAPHIC_SOURCE_REVIEW"],
            "changed_controlling_canon": levels["CONTROLLING_CANON_FULL_TEXT_GEOGRAPHIC_REVIEW"],
            "levels": dict(sorted(levels.items())),
        },
        "limits": [
            "The accepted 78,145-carrier baseline is already fully dispositioned; no old backlog is reopened.",
            "Targeted findings are geographic-authority reviews, not full tax, IT, finance or legal audits.",
            "The provisional early alignment is not a recovered survey; detailed construction/site/right criteria remain under #107.",
            "Sources accepted after the pinned through commit need a later source-delta review.",
        ],
    }


def write() -> dict:
    result = build()
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, filename="", mode="wb", mtime=0) as stream:
        stream.write(raw)
    (HERE / "SOURCE_DELTA.json.gz").write_bytes(buffer.getvalue())
    (HERE / "SUMMARY.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(write()["summary"], indent=2, sort_keys=True))
