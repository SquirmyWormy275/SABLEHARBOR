"""Bounded single-system source-version census, never a business-population assertion."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from .company_store import CompanyStoreError, _id, _time
from .store import canonical, digest

VERSION_POLICIES = {"ALL_VISIBLE_VERSIONS", "LATEST_VISIBLE_PER_RECORD"}
UNKNOWN_POLICIES = {"EXCLUDE", "INCLUDE_UNDATED_STRATUM"}
MAX_MEMBERS = 2000
MAX_NATIVE_BYTES = 64 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
QUALIFICATION = (
    "Exact visible source-record versions only; not employee, change or business-event "
    "completeness, actual operation, period coverage, source reliability or effectiveness. "
    "Undated records are a separate stratum and are not established within the event window."
)


def _check(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def instant(value):
    _check(isinstance(value, str), "Explicit offset timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompanyStoreError("Explicit offset timestamp required") from exc
    _check(parsed.tzinfo is not None, "Explicit offset timestamp required")
    try:
        return parsed.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise CompanyStoreError("Timestamp is outside supported UTC range") from exc


def validate_query(query):
    _check(
        isinstance(query, dict)
        and set(query) == {"version_policy", "event_window", "unknown_event_policy"},
        "Exact source census query required",
    )
    _check(
        isinstance(query["version_policy"], str) and query["version_policy"] in VERSION_POLICIES,
        "Unknown source version policy",
    )
    _check(
        isinstance(query["unknown_event_policy"], str)
        and query["unknown_event_policy"] in UNKNOWN_POLICIES,
        "Unknown undated record policy",
    )
    window = query["event_window"]
    _check(
        isinstance(window, dict) and set(window) == {"start", "end"}, "Exact event window required"
    )
    start, end = instant(window["start"]), instant(window["end"])
    _check(start < end, "Event window must have positive duration")
    return {**query, "event_window": {"start": start.isoformat(), "end": end.isoformat()}}


def _grant(store, principal, engagement, company, branch, system):
    rows = store.list_systems(principal, engagement, company, branch)["systems"]
    _check(system in {r["system"] for r in rows}, "Source grant unavailable")


def _native_export(
    store,
    *,
    principal_id,
    engagement_id,
    company_id,
    branch_id,
    system_id,
    as_of,
    query,
    page_size,
    max_pages,
):
    key = store._key(company_id, branch_id, system_id)
    _id(principal_id)
    _id(engagement_id)
    clock = _time(as_of)
    start, end = (instant(query["event_window"][k]) for k in ("start", "end"))
    _check(end <= instant(clock), "Event window has not ended at current clock")
    members, originals, pages = [], [], []
    scanned, native_bytes, metadata_bytes = 0, 0, 0
    excluded = {"outside_event_window": 0, "undated": 0}
    strata = {"IN_EVENT_WINDOW": 0, "UNDATED": 0}
    started = datetime.now(UTC).isoformat()
    with store._db() as db:
        db.execute("BEGIN")
        grant = db.execute(
            "SELECT active FROM grants WHERE principal=? AND engagement=? "
            "AND company=? AND branch=? AND system=?",
            (principal_id, engagement_id, *key),
        ).fetchone()
        _check(grant is not None and grant[0], "Source grant unavailable")
        if query["version_policy"] == "ALL_VISIBLE_VERSIONS":
            sql = (
                "SELECT record,version,event_at,LENGTH(content) size FROM versions "
                "WHERE company=? AND branch=? AND system=? AND available_at<=? "
                "AND (event_at IS NULL OR event_at<=?) ORDER BY record,version"
            )
            args = (*key, clock, clock)
        else:
            # Latest visibility is resolved BEFORE applying event-window/date policy.
            sql = (
                "SELECT v.record,v.version,v.event_at,LENGTH(v.content) size FROM versions v "
                "JOIN (SELECT record,MAX(version) version FROM versions "
                "WHERE company=? AND branch=? AND system=? AND available_at<=? "
                "AND (event_at IS NULL OR event_at<=?) GROUP BY record) latest "
                "ON v.record=latest.record AND v.version=latest.version "
                "WHERE v.company=? AND v.branch=? AND v.system=? ORDER BY v.record,v.version"
            )
            args = (*key, clock, clock, *key)
        cursor = db.execute(sql, args)
        previous = None
        while True:
            batch = cursor.fetchmany(page_size)
            if not batch:
                break
            _check(len(pages) < max_pages, "Incomplete census: page budget exceeded")
            page_members = []
            for row in batch:
                identity = (row["record"], row["version"])
                _check(
                    previous is None or identity > previous,
                    "Duplicate or reordered source identity",
                )
                previous = identity
                scanned += 1
                event = row["event_at"]
                if event is None:
                    if query["unknown_event_policy"] == "EXCLUDE":
                        excluded["undated"] += 1
                        continue
                    stratum = "UNDATED"
                elif not start <= instant(event) < end:
                    excluded["outside_event_window"] += 1
                    continue
                else:
                    stratum = "IN_EVENT_WINDOW"
                _check(len(members) < MAX_MEMBERS, "Census member quota exceeded")
                _check(
                    native_bytes + row["size"] <= MAX_NATIVE_BYTES,
                    "Census native byte quota exceeded",
                )
                stored = store._read(
                    db, principal_id, engagement_id, (*key, row["record"]), row["version"], clock
                )
                content = stored["content"]
                _check(len(content) == row["size"], "Source size changed within snapshot")
                metadata = store._metadata(stored)
                member = {"source": metadata, "date_stratum": stratum, "bytes": len(content)}
                metadata_bytes += len(canonical(member).encode())
                _check(metadata_bytes <= MAX_METADATA_BYTES, "Census metadata quota exceeded")
                members.append(member)
                originals.append(content)
                native_bytes += len(content)
                strata[stratum] += 1
                page_members.append(member)
            pages.append(
                {
                    "index": len(pages),
                    "scanned_versions": len(batch),
                    "matched_versions": len(page_members),
                    "members_sha256": digest(page_members),
                }
            )
    _grant(store, principal_id, engagement_id, *key)
    manifest = {
        "schema": "COMPANY_SOURCE_CENSUS_V1",
        "query": query,
        "principal_id": principal_id,
        "engagement_id": engagement_id,
        "company": company_id,
        "branch": branch_id,
        "system_id": system_id,
        "as_of": clock,
        "started_at": started,
        "completed_at": datetime.now(UTC).isoformat(),
        "snapshot_isolation": "ONE_CONCRETE_SOURCE_DATABASE_TRANSACTION",
        "sampling_unit": "SOURCE_RECORD_VERSION",
        "source_versions": len(members),
        "distinct_source_records": len({m["source"]["record"] for m in members}),
        "scanned_visible_versions": scanned,
        "strata": strata,
        "excluded": excluded,
        "native_bytes": native_bytes,
        "pages": pages,
        "pagination_complete": True,
        "members": members,
        "membership_sha256": digest(members),
        "qualification": QUALIFICATION,
    }
    return {"manifest": manifest, "originals": originals}


def export_census(
    store,
    *,
    principal_id,
    engagement_id,
    company_id,
    branch_id,
    system_id,
    as_of,
    query,
    page_size=100,
    max_pages=100,
):
    """One concrete system snapshot; portfolio aliases are resolved to exactly one component."""
    query = validate_query(query)
    _check(type(page_size) is int and 1 <= page_size <= 1000, "Bounded page size required")
    _check(type(max_pages) is int and 1 <= max_pages <= 1000, "Bounded page budget required")
    kwargs = dict(
        principal_id=principal_id,
        engagement_id=engagement_id,
        company_id=company_id,
        branch_id=branch_id,
        system_id=system_id,
        as_of=as_of,
        query=query,
        page_size=page_size,
        max_pages=max_pages,
    )
    if getattr(store, "is_federated", False):
        source_id, native_system, component, native = store._route(company_id, branch_id, system_id)
        kwargs.update(
            company_id=component["company"], branch_id=component["branch"], system_id=native_system
        )
        result = _native_export(native, **kwargs)
        store._authorized(
            principal_id, engagement_id, source_id, native_system, company_id, branch_id
        )
        manifest = result["manifest"]
        manifest["portfolio_binding"] = dict(store.binding)
        manifest["source_store_id"] = source_id
        manifest["source_system_alias"] = system_id
        # Exact upstream metadata remains under source; wrapper metadata is a separate route pin.
        manifest["portfolio_qualification"] = store._manifest["profile"]["qualification"]
    else:
        result = _native_export(store, **kwargs)
    manifest = result["manifest"]
    # Capture times do not alter the immutable query/member snapshot identity.
    manifest["snapshot_id"] = "CENSUS-" + digest(
        {k: v for k, v in manifest.items() if k not in {"started_at", "completed_at", "pages"}}
    )
    return result


def verify_export(export, *, expected_manifest_sha256):
    _check(
        isinstance(export, dict) and set(export) == {"manifest", "originals"},
        "Census shape invalid",
    )
    manifest, originals = export["manifest"], export["originals"]
    _check(digest(manifest) == expected_manifest_sha256, "Census manifest changed")
    members, pages = manifest["members"], manifest["pages"]
    _check(
        manifest["pagination_complete"]
        and len(members) == len(originals) == manifest["source_versions"],
        "Incomplete census",
    )
    _check([p["index"] for p in pages] == list(range(len(pages))), "Invalid census pages")
    _check(
        sum(p["scanned_versions"] for p in pages) == manifest["scanned_visible_versions"],
        "Incomplete source scan",
    )
    _check(sum(p["matched_versions"] for p in pages) == len(members), "Incomplete page membership")
    _check(digest(members) == manifest["membership_sha256"], "Membership changed")
    seen, offset = set(), 0
    for page in pages:
        batch = members[offset : offset + page["matched_versions"]]
        _check(digest(batch) == page["members_sha256"], "Page membership changed")
        offset += len(batch)
    for member, content in zip(members, originals, strict=True):
        source = member["source"]
        identity = tuple(source[k] for k in ("company", "branch", "system", "record", "version"))
        _check(identity not in seen, "Duplicate census member")
        seen.add(identity)
        _check(
            isinstance(content, bytes)
            and len(content) == member["bytes"]
            and hashlib.sha256(content).hexdigest() == source["sha256"],
            "Native census source changed",
        )
    return {"status": "VERIFIED_EXACT_SOURCE_CENSUS", "members": len(members)}
