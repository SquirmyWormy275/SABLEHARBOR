"""Collect an authorized operating-source population without approving reliability.

Called inside the Engine reducer; never opens an engagement or changes its mode.
Original version bytes, query manifest and working rows are separate artifacts.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .company_collection import binding
from .company_population import export_population, validate_query, verify_export
from .company_store import CompanyStoreError
from .operating_source_bridge import encoded, sha
from .store import DomainError, digest


def _period(scope, query):
    zone = ZoneInfo(scope.get("timezone", "UTC"))

    def bound(value, end=False):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if len(value) == 10 and end:
            parsed += timedelta(days=1)
        return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed

    first, last = query["month_start"], query["month_end"]
    start = datetime(2027 + (first - 1) // 12, (first - 1) % 12 + 1, 1, tzinfo=zone)
    year, month = 2027 + (last - 1) // 12, (last - 1) % 12 + 1
    end = datetime(year, month, calendar.monthrange(year, month)[1], tzinfo=zone)
    end += timedelta(days=1)
    if start < bound(scope["period_start"]) or end > bound(scope["period_end"], True):
        raise DomainError("Requested complete source months exceed the audit period")
    return start.isoformat(), (end - timedelta(microseconds=1)).isoformat()


def collect(engine, state, payload, stamped, command_id):
    """Return a receipt and explicit next population.import command (no auto approval)."""
    fields = {"table", "source_scenario", "month_start", "month_end", "units"}
    if (
        not isinstance(payload, dict)
        or set(payload) != {"request_id", "query"}
        or not isinstance(payload["query"], dict)
        or set(payload["query"]) != fields
    ):
        raise DomainError("Choose an issued request and exact typed source query")
    request = next((r for r in state["requests"] if r["id"] == payload["request_id"]), None)
    if not request or request["status"] not in {
        "ISSUED",
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "CLARIFICATION",
        "SUBMITTED",
    }:
        raise DomainError("Issue an evidence request before collecting a population")
    boundary = request.get("boundary_id")
    if boundary not in state["scope"]["boundaries"]:
        raise DomainError("Request must identify an existing scoped boundary")
    bound = binding(engine, state)
    try:
        query, _, _ = validate_query(
            {**payload["query"], "as_of": state["simulated_at"]}, engine.repository
        )
        start, end = _period(state["scope"], query)
        exported = export_population(
            engine.company_store,
            principal_id=stamped["actor"],
            engagement_id=state["id"],
            company_id=bound["company"],
            branch_id=bound["branch"],
            query=query,
            repository=engine.repository,
        )
        manifest = exported["manifest"]
        manifest_hash = sha(encoded(manifest))
        verify_export(exported, expected_manifest_sha256=manifest_hash)
        prior = next(
            (
                r
                for r in request.get("company_population_collections", [])
                if r["snapshot_id"] == manifest["snapshot_id"]
            ),
            None,
        )
        if prior:
            return prior
        originals = []
        for member in manifest["members"]:
            args = (
                stamped["actor"],
                state["id"],
                bound["company"],
                bound["branch"],
                member["system"],
                member["record"],
            )
            kwargs = {"version": member["version"], "as_of": state["simulated_at"]}
            record = engine.company_store.read_version(*args, **kwargs)
            if sha(record["content"]) != member["sha256"]:
                raise DomainError("Population original differs from pinned snapshot", status=409)
            receipt = engine.company_store.collect(
                *args, **kwargs, command_id="COL-" + digest([state["id"], command_id, member])
            )
            originals.append((member, record["content"], receipt))
    except CompanyStoreError as exc:
        raise DomainError("Company population unavailable or query invalid", status=403) from exc

    coverage = {
        "request_id": request["id"],
        "control_id": request.get("control_id"),
        "professional_sufficiency": "NOT_ASSERTED",
    }
    retained = []

    def retain(name, content, source):
        artifact = engine.artifacts.retain(
            state["id"], name, content, source=source, coverage=coverage
        )
        artifact.update(stamped)
        artifact.update(request_id=request["id"], received_at=stamped["recorded_at"])
        retained.append(artifact)
        return artifact

    native = []
    for member, content, receipt in originals:
        artifact = retain(
            f"{member['record']}-v{member['version']}.json",
            content,
            {"kind": "COLLECTED_COMPANY_SOURCE", "receipt": receipt},
        )
        native.append({"artifact_id": artifact["id"], "source": member})
    rows = [{"id": "SV-" + digest(row["source"]), **row} for row in exported["records"]]
    query_artifact = retain(
        "Population-query-manifest.json",
        encoded(manifest),
        {"kind": "COMPANY_POPULATION_QUERY", "sha256": manifest_hash},
    )
    population_artifact = retain(
        "Source-version-population.json",
        encoded(rows),
        {"kind": "COMPANY_POPULATION_DERIVATION", "query_manifest_sha256": manifest_hash},
    )
    next_command = {
        "kind": "population.import",
        "payload": {
            "title": f"{query['table']} source-version population",
            "artifact_id": population_artifact["id"],
            "rows": rows,
            "scope": {
                "boundary_id": boundary,
                "unit": "SOURCE_RECORD_VERSION",
                "timezone": state["scope"].get("timezone", "UTC"),
                "period_start": start,
                "period_end": end,
            },
            "source": {
                "source_id": manifest["snapshot_id"],
                "query": encoded(query).decode(),
                "query_manifest_artifact_id": query_artifact["id"],
                "query_manifest_sha256": manifest_hash,
                "completeness_representation": (
                    "Authorized visible imported versions matching query; "
                    "unimported activity, unit-to-boundary applicability, accuracy and "
                    "independent reliability remain unassessed."
                ),
            },
        },
    }
    result = {
        "snapshot_id": manifest["snapshot_id"],
        "manifest_sha256": manifest_hash,
        "sampling_unit": "SOURCE_RECORD_VERSION",
        "source_versions": len(rows),
        "distinct_source_records": len({m["record"] for m in manifest["members"]}),
        "native_artifacts": native,
        "manifest_artifact_id": query_artifact["id"],
        "population_artifact_id": population_artifact["id"],
        "next_command": next_command,
        "registration": "AWAITING_EXPLICIT_IMPORT",
        "independent_review": "NOT_PERFORMED",
        **stamped,
    }
    state["artifacts"].extend(retained)
    request.setdefault("artifact_ids", []).extend(a["id"] for a in retained)
    request.setdefault("company_population_collections", []).append(result)
    request.update(status="SUBMITTED", unread=True)
    return result
