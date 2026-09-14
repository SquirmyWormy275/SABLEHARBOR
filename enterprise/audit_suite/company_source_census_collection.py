"""Collect a scoped one-system census and propose, never approve, population registration."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .company_collection import binding
from .company_source_census import (
    QUALIFICATION,
    export_census,
    instant,
    validate_query,
    verify_export,
)
from .company_store import CompanyStoreError
from .store import DomainError, canonical, digest


def _period(scope, query):
    zone = ZoneInfo(scope.get("timezone", "UTC"))

    def bound(value, end=False):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if len(value) == 10 and end:
            parsed += timedelta(days=1)
        return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed

    start, end = (instant(query["event_window"][k]) for k in ("start", "end"))
    if start < bound(scope["period_start"]) or end > bound(scope["period_end"], True):
        raise DomainError(
            "Source event window exceeds the audit period", code="INVALID_CENSUS_QUERY"
        )
    return start.isoformat(), (end - timedelta(microseconds=1)).isoformat()


def collect(engine, state, payload, stamped, command_id):
    if not isinstance(payload, dict) or set(payload) != {"request_id", "system_id", "query"}:
        raise DomainError(
            "Choose one source system, an issued request and exact census query",
            code="INVALID_CENSUS_QUERY",
        )
    request = next((r for r in state["requests"] if r["id"] == payload["request_id"]), None)
    if not request or request["status"] not in {
        "ISSUED",
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "CLARIFICATION",
        "SUBMITTED",
    }:
        raise DomainError(
            "Issue the evidence request before collecting a census", code="INVALID_CENSUS_QUERY"
        )
    boundary = request.get("boundary_id")
    if boundary not in state["scope"]["boundaries"]:
        raise DomainError("Request must identify a scoped boundary", code="INVALID_CENSUS_QUERY")
    bound = dict(binding(engine, state))
    try:
        query = validate_query(payload["query"])
    except CompanyStoreError as exc:
        raise DomainError(
            "Invalid source census query", code="INVALID_CENSUS_QUERY", status=400
        ) from exc
    try:
        start, end = _period(state["scope"], query)
        exported = export_census(
            engine.company_store,
            principal_id=stamped["actor"],
            engagement_id=state["id"],
            company_id=bound["company"],
            branch_id=bound["branch"],
            system_id=payload["system_id"],
            as_of=state["simulated_at"],
            query=query,
        )
        manifest = exported["manifest"]
        manifest_hash = digest(manifest)
        verify_export(exported, expected_manifest_sha256=manifest_hash)
        prior = next(
            (
                x
                for x in request.get("company_census_collections", [])
                if x["snapshot_id"] == manifest["snapshot_id"]
            ),
            None,
        )
        if prior:
            return prior
        originals = []
        for member, content in zip(manifest["members"], exported["originals"], strict=True):
            source = member["source"]
            args = (
                stamped["actor"],
                state["id"],
                bound["company"],
                bound["branch"],
                payload["system_id"],
                source["record"],
            )
            receipt = engine.company_store.collect(
                *args,
                version=source["version"],
                as_of=state["simulated_at"],
                command_id="CEN-" + digest([state["id"], command_id, member]),
            )
            upstream = receipt.get("upstream_receipt", receipt)
            if upstream["source"] != source or upstream["content_bytes"] != len(content):
                raise CompanyStoreError("Census original differs from snapshot")
            originals.append((member, content, receipt))
        _current(engine, state, stamped["actor"], bound, payload["system_id"])
    except CompanyStoreError as exc:
        raise DomainError(
            "Source census unavailable, changed or exceeds its bounded query limits",
            code="SOURCE_CENSUS_UNAVAILABLE",
            status=403,
        ) from exc

    retained = []
    coverage = {
        "request_id": request["id"],
        "control_id": request.get("control_id"),
        "professional_sufficiency": "NOT_ASSERTED",
    }

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
        source = member["source"]
        name = source["provenance"].get("name")
        if not isinstance(name, str) or not name:
            name = "Source-original-" + source["sha256"] + ".bin"
        artifact = retain(name, content, {"kind": "COLLECTED_COMPANY_SOURCE", "receipt": receipt})
        native.append({"artifact_id": artifact["id"], "source": receipt["source"]})
    route = {
        k: manifest[k]
        for k in (
            "portfolio_binding",
            "source_store_id",
            "source_system_alias",
            "portfolio_qualification",
        )
        if k in manifest
    }
    rows = [
        {
            "id": "SV-" + digest({"source": member["source"], "route": route}),
            **member,
            "route": route,
        }
        for member in manifest["members"]
    ]
    query_artifact = retain(
        "Source-census-query-manifest.json",
        canonical(manifest).encode(),
        {"kind": "COMPANY_CENSUS_QUERY", "sha256": manifest_hash},
    )
    rows_artifact = retain(
        "Source-record-version-census.json",
        canonical(rows).encode(),
        {"kind": "COMPANY_CENSUS_DERIVATION", "query_manifest_sha256": manifest_hash},
    )
    next_command = None
    if rows:
        next_command = {
            "kind": "population.import",
            "payload": {
                "title": f"{payload['system_id']} source-record-version census",
                "artifact_id": rows_artifact["id"],
                "rows": rows,
                "scope": {
                    "boundary_id": boundary,
                    "unit": "SOURCE_RECORD_VERSION",
                    "timezone": state["scope"].get("timezone", "UTC"),
                    "period_start": start,
                    "period_end": end,
                    "period_basis": "DECLARED_EVENT_QUERY_NOT_UNDATED_EVENT_COVERAGE",
                },
                "source": {
                    "source_id": manifest["snapshot_id"],
                    "query": canonical(query),
                    "query_manifest_artifact_id": query_artifact["id"],
                    "query_manifest_sha256": manifest_hash,
                    "as_of": manifest["as_of"],
                    "strata": manifest["strata"],
                    "completeness_representation": QUALIFICATION,
                },
            },
        }
    result = {
        "snapshot_id": manifest["snapshot_id"],
        "manifest_sha256": manifest_hash,
        "query": query,
        "system_id": payload["system_id"],
        "as_of": manifest["as_of"],
        "sampling_unit": "SOURCE_RECORD_VERSION",
        "source_versions": len(rows),
        "distinct_source_records": manifest["distinct_source_records"],
        "strata": manifest["strata"],
        "excluded": manifest["excluded"],
        "native_artifacts": native,
        "manifest_artifact_id": query_artifact["id"],
        "population_artifact_id": rows_artifact["id"],
        "next_command": next_command,
        "registration": "AWAITING_EXPLICIT_IMPORT" if rows else "EMPTY_CENSUS",
        "independent_review": "NOT_PERFORMED",
        "qualification": QUALIFICATION,
        "snapshot_isolation": manifest["snapshot_isolation"],
        **route,
        **stamped,
    }
    try:
        _current(engine, state, stamped["actor"], bound, payload["system_id"])
    except CompanyStoreError as exc:
        raise DomainError(
            "Source authority changed during census retention",
            code="SOURCE_CENSUS_UNAVAILABLE",
            status=409,
        ) from exc
    state["artifacts"].extend(retained)
    request.setdefault("artifact_ids", []).extend(a["id"] for a in retained)
    request.setdefault("company_census_collections", []).append(result)
    request.update(status="SUBMITTED", unread=True)
    return result


def _current(engine, state, actor, bound, system_id):
    if binding(engine, state) != bound:
        raise CompanyStoreError("Source binding changed")
    systems = engine.company_store.list_systems(
        actor, state["id"], bound["company"], bound["branch"]
    )["systems"]
    if system_id not in {s["system"] for s in systems}:
        raise CompanyStoreError("Source grant revoked")
