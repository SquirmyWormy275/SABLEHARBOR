"""Authorized, fixed-query populations over imported operating source versions.

All pages share one SQLite read transaction. Completeness means matching visible
imported records, never an assertion about unimported operations or audit sufficiency.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import TABLE_KEYS, encoded, month_bounds, sha

QUERY_FIELDS = {"table", "source_scenario", "month_start", "month_end", "units", "as_of"}
BASIS = "ALL_VISIBLE_IMPORTED_SOURCE_VERSIONS_IN_MONTH_INTERVAL"


def validate_query(query, repository: Path):
    if not isinstance(query, dict) or set(query) != QUERY_FIELDS:
        raise CompanyStoreError("Exact typed population query fields required")
    if query["table"] not in TABLE_KEYS or query["source_scenario"] not in {
        "base",
        "downside",
        "expansion",
    }:
        raise CompanyStoreError("Unknown operating table or scenario")
    start, end = query["month_start"], query["month_end"]
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 60:
        raise CompanyStoreError("Explicit source month interval1–60 required")
    scope_path = repository / "enterprise/operations/export_scope.json"
    schema_path = repository / "enterprise/operations/export_schema.json"
    scope = json.loads(scope_path.read_text())[query["table"]]
    schema = json.loads(schema_path.read_text())[query["table"]]
    units = query["units"]
    allowed = scope["allowed_values"].get("unit", [])
    if (
        not isinstance(units, list)
        or not units
        or any(not isinstance(x, str) for x in units)
        or len(units) != len(set(units))
        or set(units) - set(allowed)
    ):
        raise CompanyStoreError("Select explicit distinct approved source units")
    as_of = _time(query["as_of"])
    # Calendar conversion is the retained model's month index, not an event-date inference.
    import calendar
    from datetime import date

    year, month = 2027 + (end - 1) // 12, (end - 1) % 12 + 1
    last = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    close = month_bounds({"month_index": end, "period": last})[2]
    if as_of < _time(close):
        raise CompanyStoreError("Requested source month interval has not closed")
    return (
        {**query, "units": sorted(units), "as_of": as_of},
        schema,
        {
            "schema_path": str(schema_path.relative_to(repository)),
            "schema_sha256": sha(schema_path.read_bytes()),
            "scope_path": str(scope_path.relative_to(repository)),
            "scope_sha256": sha(scope_path.read_bytes()),
            "allowed_values": scope["allowed_values"],
        },
    )


def verify_export(export, *, expected_manifest_sha256):
    """Verify against a separately retained trusted manifest hash, not a caller's new hash."""
    if not isinstance(export, dict) or set(export) != {"manifest", "records"}:
        raise CompanyStoreError("Population export shape invalid")
    manifest, records = export["manifest"], export["records"]
    if sha(encoded(manifest)) != expected_manifest_sha256:
        raise CompanyStoreError("Population manifest changed")
    members, pages = manifest["members"], manifest["pages"]
    if len(records) != manifest["matched_versions"] or len(members) != len(records):
        raise CompanyStoreError("Incomplete population export")
    if not manifest["pagination_complete"] or [p["index"] for p in pages] != list(
        range(len(pages))
    ):
        raise CompanyStoreError("Incomplete or repeated population pages")
    if sum(p["scanned_versions"] for p in pages) != manifest["scanned_versions"]:
        raise CompanyStoreError("Incomplete source scan")
    if sum(p["matched_versions"] for p in pages) != len(records):
        raise CompanyStoreError("Page membership count mismatch")
    identities = set()
    for member, record in zip(members, records, strict=True):
        if set(record) != {"source", "source_row"} or record["source"] != member:
            raise CompanyStoreError("Population member changed")
        identity = (member["record"], member["version"])
        if identity in identities:
            raise CompanyStoreError("Duplicate population member")
        identities.add(identity)
        if sha(encoded(record["source_row"])) != member["source_row_sha256"]:
            raise CompanyStoreError("Population source row changed")
    return {"status": "VERIFIED_PINNED_IMPORTED_SOURCE_POPULATION", "members": len(members)}


def export_population(
    store: CompanyStore,
    *,
    principal_id,
    engagement_id,
    company_id,
    branch_id,
    query,
    repository: Path,
    page_size=100,
    max_pages=10000,
):
    if getattr(store, "is_federated", False):
        from .store import DomainError

        raise DomainError(
            "Portfolio population export requires a concrete source snapshot",
            code="FEDERATION_OPERATION_UNSUPPORTED",
            status=409,
        )
    query, schema, source_schema = validate_query(query, repository)
    if type(page_size) is not int or not 1 <= page_size <= 1000:
        raise CompanyStoreError("Page size must be1–1000")
    if type(max_pages) is not int or not 1 <= max_pages <= 10000:
        raise CompanyStoreError("Explicit bounded page budget required")
    key = store._key(company_id, branch_id, query["table"])
    pages, records, members, excluded = [], [], [], {"unit": 0, "month": 0}
    # SQL shape is constant. No SQL fragment, column name or predicate is caller supplied.
    with store._db() as db:
        db.execute("BEGIN")
        allowed = db.execute(
            "SELECT active FROM grants WHERE principal=? AND engagement=? "
            "AND company=? AND branch=? AND system=?",
            (principal_id, engagement_id, *key),
        ).fetchone()
        if not allowed or not allowed[0]:
            raise CompanyStoreError("Source unavailable or unauthorized")
        cursor = db.execute(
            "SELECT record,version FROM versions WHERE company=? AND branch=? AND system=? "
            "AND available_at<=? AND (event_at IS NULL OR event_at<=?) ORDER BY record,version",
            (*key, query["as_of"], query["as_of"]),
        )
        previous, scanned = None, 0
        while True:
            batch = cursor.fetchmany(page_size)
            if not batch:
                break
            if len(pages) >= max_pages:
                raise CompanyStoreError("Incomplete pagination: page budget exhausted")
            page_members = []
            for identity in batch:
                current = (identity["record"], identity["version"])
                if previous is not None and current <= previous:
                    raise CompanyStoreError("Duplicate or reordered source member")
                previous = current
                stored = store._read(
                    db, principal_id, engagement_id, (*key, current[0]), current[1], query["as_of"]
                )
                envelope = json.loads(stored["content"])
                if (
                    envelope.get("record_origin") != "MODEL_DERIVED_SYNTHETIC_HISTORY"
                    or envelope.get("source_table") != query["table"]
                    or envelope.get("source_scenario") != query["source_scenario"]
                ):
                    raise CompanyStoreError("Source branch/table/qualification mismatch")
                row = envelope.get("source_row")
                if not isinstance(row, dict) or set(row) != set(schema):
                    raise CompanyStoreError("Unknown or missing source fields")
                if any(
                    row.get(field) not in values
                    for field, values in source_schema["allowed_values"].items()
                ):
                    raise CompanyStoreError("Source record violates approved source scope")
                if row["scenario"] != query["source_scenario"]:
                    raise CompanyStoreError("Source scenario mismatch")
                provenance = json.loads(stored["provenance"])
                row_hash = sha(encoded(row))
                if row_hash != provenance.get("source_row_sha256"):
                    raise CompanyStoreError("Source row/provenance hash mismatch")
                month_bounds(row)
                scanned += 1
                if row["unit"] not in query["units"]:
                    excluded["unit"] += 1
                    continue
                if not query["month_start"] <= row["month_index"] <= query["month_end"]:
                    excluded["month"] += 1
                    continue
                member = {
                    "company": company_id,
                    "branch": branch_id,
                    "system": query["table"],
                    "record": current[0],
                    "version": current[1],
                    "sha256": stored["sha256"],
                    "source_row_sha256": row_hash,
                    "available_at": stored["available_at"],
                    "imported_at": stored["imported_at"],
                    "event_at": stored["event_at"],
                }
                members.append(member)
                records.append({"source": member, "source_row": row})
                page_members.append(member)
            pages.append(
                {
                    "index": len(pages),
                    "scanned_versions": len(batch),
                    "matched_versions": len(page_members),
                    "membership_sha256": sha(encoded(page_members)),
                }
            )
    # Check current grant again before returning the materialized immutable snapshot.
    systems = store.list_systems(principal_id, engagement_id, company_id, branch_id)["systems"]
    if query["table"] not in {s["system"] for s in systems}:
        raise CompanyStoreError("Source grant revoked during population export")
    manifest = {
        "schema_version": "1.0",
        "population_basis": BASIS,
        "query": query,
        "source_schema": source_schema,
        "company": company_id,
        "branch": branch_id,
        "principal": principal_id,
        "engagement": engagement_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "snapshot_isolation": "ONE_SQLITE_READ_TRANSACTION_ACROSS_ALL_PAGES",
        "scanned_versions": scanned,
        "matched_versions": len(members),
        "excluded_versions": excluded,
        "pages": pages,
        "pagination_complete": True,
        "members": members,
        "membership_sha256": sha(encoded(members)),
        "snapshot_id": sha(encoded([query, key, source_schema, members])),
        "implementation_sha256": sha(Path(__file__).read_bytes()),
        "professional_sufficiency": "NOT_ASSESSED",
        "independent_population_review": "NOT_PERFORMED",
        "limits": [
            "Complete only for authorized visible imported source versions matching this query.",
            "Source forecasts/planning states and unknown exact event times remain unchanged.",
            "Unimported activity and independent corroboration completeness are not asserted.",
        ],
    }
    export = {"manifest": manifest, "records": records}
    verify_export(export, expected_manifest_sha256=sha(encoded(manifest)))
    return export
