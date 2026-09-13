"""Apply only the owner-approved Klein/Fort transition, retaining historical source rows."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PATH = "geospatial/sources/klein_fort_occupancy.json"
DECISION = "GEO-KLEIN-FORT-20260913"


def load(root=ROOT):
    value = json.loads((root / PATH).read_text())
    raw = (root / value["canon_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != value["canon_sha256"]:
        raise ValueError("Occupancy decision source hash differs")
    if (
        value["decision_id"] != DECISION
        or value["status"] != "OWNER_APPROVED"
        or value["relation"] != "SEPARATE_PREMISES_STAGED_RELOCATION"
        or value["relocation_year"] != "2024"
    ):
        raise ValueError("Unapproved continuity decision")
    old, new = value["states"]
    for row in [old, new]:
        if row["decision_id"] != DECISION or row["source_id"] != value["source_id"]:
            raise ValueError("Unbound occupancy state")
        if any(
            row.get(k)
            for k in [
                "valid_from",
                "valid_to",
                "opened_on",
                "closed_on",
                "owner_entity",
                "lessor_entity",
            ]
        ):
            raise ValueError("Exact day or property right is not authorized")
    if (
        old["asset_id"] != "SH-SITE-0002"
        or old["earliest_start"] is not None
        or old["latest_start"] != "2022-01-01"
        or old["earliest_end"] != "2024-01-01"
        or old["latest_end"] != "2025-01-01"
        or new["asset_id"] != "SH-SITE-0003"
        or new["earliest_start"] != "2024-01-01"
        or new["latest_start"] != "2025-01-01"
        or new["earliest_end"] is not None
        or new["latest_end"] is not None
    ):
        raise ValueError("Occupancy bounds exceed the approved history")
    return value


def evidence(root=ROOT):
    record = load(root)
    return dict(
        path=record["canon_path"],
        revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        locator="Approved history / Temporal representation",
        sha256=record["canon_sha256"],
        evidence=(root / record["canon_path"]).read_text(),
        decision_id=DECISION,
        approved_state=record,
    )


def sync(root=ROOT):
    record = load(root)
    path = root / "geospatial/sources/catalog.json"
    c = json.loads(path.read_text())
    sid = record["source_id"]
    stamp = record["states"][0]["recorded_at"]
    c["sources"] = [s for s in c["sources"] if s["source_id"] != sid]
    c["sources"].append(
        dict(
            source_id=sid,
            title="Approved Klein/Fort occupancy continuity",
            publisher_or_author="Sable Harbor owner",
            source_type="OWNER_APPROVED_CANON",
            publication_date=record["decision_date"],
            accessed_date=record["decision_date"],
            url_or_repo_path=record["canon_path"],
            repository_commit=None,
            file_sha256=record["canon_sha256"],
            license="Owner-authorized synthetic project material",
            citation=record["canon_path"],
            coverage="Separate premises; staged 2024 relocation; year-bounded occupancy",
            source_quality="OWNER_APPROVED",
            notes="Exact days, parcels, real title and access remain unresolved.",
        )
    )
    c["decisions"] = [d for d in c["decisions"] if d["decision_id"] != DECISION]
    c["decisions"].append(
        dict(
            decision_id=DECISION,
            decision_date=record["decision_date"],
            decision_title="Klein shop to separate Fort premises in 2024",
            decision_type="OWNER_APPROVED_CONTINUITY",
            affected_object_ids=["SH-SITE-0002", "SH-SITE-0003"],
            decision_status="OWNER_APPROVED",
            deciding_authority="Owner: Approve the proposed history",
            source_conversation="Repository work session; explicit acceptance of the staged-2024 relocation proposal",
            source_document=record["canon_path"],
            rationale="Resolve physical continuity separately from the 2022 institutional recharter.",
            alternatives_considered="The previously unresolved same-site or separate-site alternatives are superseded by explicit owner acceptance.",
            supersedes_decision_id="GEO-D002",
            notes="Supersedes historical-linkage uncertainty only; Hazelwood study geography and unlocated exact parcels remain.",
        )
    )
    conflict = next(r for r in c["conflicts"] if r["conflict_id"] == "GEO-C002")
    conflict.update(
        status="RESOLVED_OWNER_APPROVED_2024_RELOCATION",
        recommendation="Retain distinct site IDs; use the approved year-bounded relocation and occupancy states.",
        question="Resolved: Willow continued at the original shop after recharter, moved to separate Fort premises during 2024 and vacated the old shop that year.",
        implications="No same-parcel continuity, exact move day, individual component commissioning date or real property right is inferred.",
    )
    conflict["source_ids"] = list(dict.fromkeys(conflict["source_ids"] + [sid]))
    c["asset_states"] = [r for r in c["asset_states"] if r.get("decision_id") != DECISION]
    for r in c["asset_states"]:
        if r["asset_id"] in ("SH-SITE-0002", "SH-SITE-0003") and not r.get("superseded_at"):
            r["superseded_at"] = stamp
    c["asset_states"].extend(record["states"])
    for obj in c["objects"]:
        if obj["object_id"] in ("SH-SITE-0002", "SH-SITE-0003"):
            old = obj["object_id"] == "SH-SITE-0002"
            obj.update(
                relevant_date="2021–2024" if old else "2024–2026",
                date_precision="YEAR_RANGE",
                decision_id=DECISION,
                notes="Original leased shop; use continued after the 2022 recharter, with staged relocation and vacancy during 2024. Exact parcel and lease days remain unknown."
                if old
                else "Separate Fort premises; principal research operation transferred during 2024. Existing shed functions preserved; exact parcel, entry day and component commissioning dates remain unknown.",
                next_action="Historical linkage resolved; retain explicit parcel/access precision limits and year-bounded occupancy.",
            )
    c["claims"] = [r for r in c["claims"] if not r["claim_id"].startswith("CLM-KF-20260913-")]
    for oid in ["SH-SITE-0002", "SH-SITE-0003"]:
        c["claims"].append(
            dict(
                claim_id="CLM-KF-20260913-" + oid,
                object_id=oid,
                source_id=sid,
                source_locator="Approved history / Temporal representation",
                exact_source_wording=(root / record["canon_path"]).read_text(),
                claim_status="CANON_LOCKED",
                notes="Owner-approved new fictional history, not recovered independent evidence.",
            )
        )
    path.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sync()


def occupancy_at(day, known_at=None, root=ROOT):
    """Query approved occupancy with an optional transaction-time cutoff."""
    from datetime import date, datetime
    from geospatial.scripts.model import temporal_membership

    date.fromisoformat(day)
    record = load(root)
    cutoff = datetime.fromisoformat(known_at) if known_at else None
    return {
        r["asset_id"]: (
            "UNKNOWN"
            if cutoff and cutoff < datetime.fromisoformat(r["recorded_at"])
            else temporal_membership(r, day)
        )
        for r in record["states"]
    }
