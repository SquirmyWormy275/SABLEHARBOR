"""Exact accepted-source review of PR #185 for the finite geographic edition."""

from __future__ import annotations

import gzip
import io
import json
from collections import Counter
from pathlib import Path

from tools.evidence.inventory import fingerprints, tree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROM = "e4ed29b2b6410e4c736b90dddef37a735487dada"
THROUGH = "bcdf3ade1d83d04774da9a914deb269442ee52f6"

# Every changed path is reviewed at the authority appropriate to its role.
# Derived files and tests are not separate corroboration of their source.
FINDINGS = {
    "geospatial/engineering_review/interface_successor_20260929/README.md": (
        "EXPLANATORY_READER",
        "Explains the 12-site/31-track/26-structure synthetic interface and the real-right/design limits; the generated register and pinned source control the quantitative claims.",
    ),
    "geospatial/engineering_review/interface_successor_20260929/build.py": (
        "DERIVATION_AND_VALIDATION",
        "Recomputes eight proposed turnout centerline/parent/yard joins, profile stations and accepted old/new structure mileposts; code is not field certification.",
    ),
    "geospatial/engineering_review/interface_successor_20260929/register.json": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "The exact 12 facilities, 31 tracks, 26 structures and eight out-of-service curves crosswalk the accepted route; zero real trackage-rights geometries, unknown external parcels and failed certification gates remain explicit.",
    ),
    "geospatial/engineering_review/interface_successor_20260929/source.json": (
        "TARGETED_GEOGRAPHIC_SOURCE_REVIEW",
        "Pins the accepted 40-mile geometry, industrial source/selector, site/track/rights layers and no-mine-spur/custody constraints; it does not add a new operating asset or right.",
    ),
    "geospatial/successor_20260929/README.md": (
        "EXPLANATORY_READER",
        "Documents the prior 83-path accepted-source interval through e4ed29b2; that interval already reviewed one changed controlling canon source in full.",
    ),
    "geospatial/successor_20260929/SOURCE_DELTA.json.gz": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "Compressed exact-blob source review for the prior interval; not independent corroboration of the underlying 83 paths.",
    ),
    "geospatial/successor_20260929/SUMMARY.json": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "Prior interval summary counts 83 changed paths, one controlling canon geographic review and eleven targeted geographic sources.",
    ),
    "geospatial/successor_20260929/source_delta.py": (
        "DERIVATION_AND_VALIDATION",
        "Revised the historical interval to e4ed29b2 and rejects unreviewed controlling canon changes; no current site or property fact is authored by the script.",
    ),
    "geospatial/successors/RAIL_GEO_107_108_DISPOSITION_2026-09-29.md": (
        "SCOPED_GEOGRAPHIC_CRITERION_REVIEW",
        "Itemizes #107/#108 remaining criteria and explicitly does not close them; it retains real ROW, client footprint, hardware/hydraulic and field-survey gaps.",
    ),
    "geospatial/successors/rail_history_2026_09_29/README.md": (
        "EXPLANATORY_READER",
        "Separates the new fictional 1954 alternative from recovered historical evidence and current operating linework.",
    ),
    "geospatial/successors/rail_history_2026_09_29/build.py": (
        "DERIVATION_AND_VALIDATION",
        "Validates source pins, 1954 length range, accepted unknown dates/geometry and zero current property/economic effect before rendering the case.",
    ),
    "geospatial/successors/rail_history_2026_09_29/case.geojson": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "Contains only two scenario features for a fictional 1954 snapshot; these are not recovered surveys or current railway assets.",
    ),
    "geospatial/successors/rail_history_2026_09_29/case.svg": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "The map visibly labels the provisional/evidence boundary; illustration adds no source authority.",
    ),
    "geospatial/successors/rail_history_2026_09_29/report.json": (
        "REGENERATED_GEOGRAPHIC_DERIVATIVE",
        "Reports the 15.084858-mile survivor and 7.047398-mile abandoned alternative as fictional, with recovered 1898/1954 linework and real ROW null.",
    ),
    "geospatial/successors/rail_history_2026_09_29/source.json": (
        "TARGETED_GEOGRAPHIC_SOURCE_REVIEW",
        "Selects a separate provisional case map only, not the accepted historical evidence layer; 1898 extent, recovered 1954 geometry, exact dates and real rights stay unknown.",
    ),
    "geospatial/tests/test_rail_history_case_successor.py": (
        "IMPLEMENTATION_TEST",
        "Rejects source mutation, unearned recovered-history/rights claims and stale case outputs; tests are not source evidence.",
    ),
    "geospatial/tests/test_rail_site_interface_successor.py": (
        "IMPLEMENTATION_TEST",
        "Checks complete site/track/structure/turnout populations and rejects unearned service/right claims; tests are not field inspections.",
    ),
    "geospatial/tests/test_source_delta_20260929.py": (
        "IMPLEMENTATION_TEST",
        "Verifies exact historical Git blob bytes and 83-path population against the pinned accepted commits, not the moving worktree.",
    ),
}


def build() -> dict:
    before, after = tree(ROOT, FROM), tree(ROOT, THROUGH)
    paths = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if len(paths) != 18 or set(paths) != set(FINDINGS):
        raise ValueError("Post-#185 changed-path population needs fresh substantive review")
    if any(p.startswith("docs/canon/") for p in paths):
        raise ValueError("Unexpected controlling canon change in PR #185 interval")
    oids = sorted({oid for path in paths for oid in (before.get(path), after.get(path)) if oid})
    hashes = {}
    for index in range(0, len(oids), 64):
        hashes.update(fingerprints(ROOT, oids[index : index + 64]))
    rows = []
    for path in paths:
        old, new = before.get(path), after.get(path)
        level, finding = FINDINGS[path]
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
    levels = Counter(row["review_level"] for row in rows)
    return {
        "record_id": "SH-GEO-SOURCE-DELTA-20260929-POST185-001",
        "from_accepted_main": FROM,
        "through_accepted_main": THROUGH,
        "review_date_utc": "2026-09-29",
        "scope": "All eighteen accepted PR #185 changed paths and exact Git blob/SHA-256 identities, with a path-specific geographic-authority disposition. No controlling canon changed in this interval.",
        "rows": rows,
        "summary": {
            "changed_paths": len(rows),
            "changed_controlling_canon": 0,
            "levels": dict(sorted(levels.items())),
        },
        "limits": [
            "All 78,145 original carrier dispositions in the accepted 1.4 baseline remain intact.",
            "The provisional early line is fictional scenario geometry, not recovered history or real ROW.",
            "The proposed terminal/warehouse leads and ladders remain out of service and have no modeled journal/cash/tax effect.",
            "This interval ends at the actual accepted PR #185 merge. The scope decision and this review are newly authored in a later successor; their own final accepted tree belongs in the later acceptance receipt, not in a self-referential source delta.",
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
