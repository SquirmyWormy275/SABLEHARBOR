"""Recover three rejected property prospects from their accepted source records."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REVISION = "321354190005c17bd91fa15ce15bb1c57be56f88"
SPECS = [
    (
        "SH-PROP-0001",
        "Cedar Junction processing prospect",
        "industrial/pale_sun/05_FALSE_START_CEDAR_JUNCTION.md",
        "Kentucky, United States",
        "2023-11-06",
        "2024-02-16",
        "Cedar Junction Conversion Services, LLC and its Kentucky brownfield processing property are fictional.",
    ),
    (
        "SH-PROP-0002",
        "Juniper Mesa uranium-property prospect",
        "industrial/pale_sun/06_FALSE_START_JUNIPER_MESA.md",
        "Western New Mexico, United States",
        "2024-03-04",
        "2024-06-14",
        "Juniper Mesa is a fictional western New Mexico uranium-property opportunity sold by fictional Mesa Lantern Minerals, LLC.",
    ),
    (
        "SH-PROP-0003",
        "Salt Rim recovery-restart prospect",
        "industrial/pale_sun/07_FALSE_START_SALT_RIM.md",
        "Western United States; state intentionally unspecified",
        "2024-07-08",
        "2024-10-04",
        "Salt Rim Recovery Venture was a fictional proposal to restart a western uranium recovery operation through a seller/operating-partner arrangement.",
    ),
]


def recover():
    rows = []
    for oid, name, path, place, start, end, needle in SPECS:
        raw = subprocess.check_output(["git", "show", REVISION + ":" + path], cwd=ROOT)
        lines = raw.decode().splitlines()
        hits = [(i, line) for i, line in enumerate(lines) if line.startswith(needle)]
        if len(hits) != 1:
            raise ValueError("Ambiguous prospect source")
        i, quote = hits[0]
        if start not in raw.decode() or end not in raw.decode():
            raise ValueError("Unbound prospect review date")
        rows.append(
            dict(
                object_id=oid,
                canonical_name=name,
                place=place,
                source=dict(
                    path=path,
                    revision=REVISION,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    locator=f"line:{i + 1}",
                    text=quote,
                ),
                review_started=start,
                review_closed=end,
                source_recorded_at="2026-09-05T22:16:52-07:00",
                source_available_as_of=end,
                geometry=None,
                geometry_disposition="INTENTIONALLY_UNLOCATED_WITH_SOURCE_REGION",
                occupancy_start=None,
                occupancy_end=None,
                acquired_on=None,
                owner_entity=None,
                disposition="REJECTED_EXTERNAL_PROSPECT_NOT_SABLE_HARBOR_PROPERTY",
                meaning="Dates describe the inquiry and rejected acquisition, not tenure or operation. Seller forecasts and analyst screening costs are not company expenditures, permits, reserves or production commitments.",
            )
        )
    return rows


def sync(c):
    rows = recover()
    ids = {r["object_id"] for r in rows}
    c["objects"] = [o for o in c["objects"] if o["object_id"] not in ids]
    c["sources"] = [
        s for s in c["sources"] if not s["source_id"].startswith("SRC-GFC-PROP-")
    ]
    c["claims"] = [
        r for r in c["claims"] if not r["claim_id"].startswith("CLM-GFC-PROP-")
    ]
    for i, r in enumerate(rows, 1):
        source = r["source"]
        sid = f"SRC-GFC-PROP-{i:03}"
        c["sources"].append(
            dict(
                source_id=sid,
                title=r["canonical_name"],
                publisher_or_author="Sable Harbor synthetic corporate record",
                source_type="ACCEPTED_RECONSTRUCTED_CASE_RECORD",
                publication_date="2026-09-06",
                accessed_date="2026-09-13",
                url_or_repo_path=source["path"],
                repository_commit=source["revision"],
                file_sha256=source["sha256"],
                license="Repository synthetic project material",
                citation=source["path"],
                coverage=r["place"] + "; rejected prospect chronology",
                source_quality="EXACT_ACCEPTED_SOURCE",
                notes=r["meaning"],
            )
        )
        c["objects"].append(
            dict(
                object_id=r["object_id"],
                canonical_name=r["canonical_name"],
                object_type="REJECTED_EXTERNAL_PROPERTY_PROSPECT",
                entity_id=None,
                place=r["place"],
                granularity="STATE_OR_REGION",
                census_status="CONSTRAINED",
                canon_status="CANON_LOCKED",
                fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
                source_id=sid,
                source_path=source["path"],
                source_commit=source["revision"],
                source_locator=source["locator"],
                exact_source_wording=source["text"],
                relevant_date=r["review_started"] + " / " + r["review_closed"],
                date_precision="DAY",
                conflict_id="",
                next_action="Retain source region and intentional unknown exact parcel; do not invent company ownership, occupancy or executed rights.",
                notes=r["meaning"],
                decision_id="GEO-COMPLETE-20260913",
            )
        )
        c["claims"].append(
            dict(
                claim_id=f"CLM-GFC-PROP-{i:03}",
                object_id=r["object_id"],
                source_id=sid,
                source_locator=source["locator"],
                exact_source_wording=source["text"],
                claim_status="CANON_LOCKED",
                notes="Recovered source claim, not newly authored property acquisition.",
            )
        )
    (ROOT / "geospatial/finalization/REJECTED_PROSPECTS.json").write_text(
        json.dumps(
            dict(
                records=rows,
                scope="Three newly enumerated geographic references from accepted case narratives. These supplement the 34-site/component docket without creating company premises.",
            ),
            indent=2,
        )
        + "\n"
    )
    return c
