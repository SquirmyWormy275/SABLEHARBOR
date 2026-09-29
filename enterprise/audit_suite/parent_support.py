"""Company-supplied multistage populations over frozen private source records.

Requests select existing company rows; learners cannot inject the child census.
The original source bytes remain private and immutable. Only the scoped projection
and its provenance are released through the normal issued-PBC delivery path.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
from dataclasses import asdict
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import populations
from .artifacts import render
from .generation import epoch_directory
from .store import DomainError, canonical, digest

MAX_SOURCE_BYTES = 8 * 1024 * 1024
KINDS = {
    "sites": (None, None),
    "tickets": ("sites", "site_id"),
    "support": ("tickets", "ticket_id"),
}


def _instant(value):
    if len(value) == 10:
        value += "T00:00:00+00:00"
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise DomainError("Source and scope timestamps require timezone offsets")
    return result


def _scope_period(scope):
    start, end = scope["period_start"], scope["period_end"]
    zone = ZoneInfo(scope.get("timezone", "UTC"))
    if len(start) == 10:
        start = datetime.combine(date.fromisoformat(start), time(0), zone).isoformat()
    if len(end) == 10:
        end = datetime.combine(date.fromisoformat(end), time(23, 59, 59), zone).isoformat()
    if _instant(start) > _instant(end):
        raise DomainError("Invalid source request period")
    return start, end


def _private_bytes(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise DomainError(
            "Private company source is unavailable", code="COMPANY_SOURCE_UNAVAILABLE"
        ) from exc
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise DomainError("Private company source requires a regular mode-0600 file")
        data = handle.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise DomainError("Company source exceeds the bounded reader limit")
    return data


def _retain(path, data):
    if len(data) > MAX_SOURCE_BYTES:
        raise DomainError("Private company request exceeds the bounded plan limit")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.parent.stat().st_mode & 0o077:
        raise DomainError("Private company plan directory requires mode 0700")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if _private_bytes(path) != data:
            raise DomainError("Immutable company source or request plan differs on retry") from None
        return
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _source(engine, state):
    directory = (
        epoch_directory(engine, state["id"], state.get("generation_epoch", 0)) / "parent-support"
    )
    frozen = directory / "source.json"
    if frozen.exists() or frozen.is_symlink():
        data = _private_bytes(frozen)
    else:
        data = _private_bytes(Path(engine.corpus_root) / "parent-support/source.json")
    value = json.loads(data)
    if value.get("schema_version") != 1 or value.get("origin") != "AUTHORED_TRAINING_RECORDS":
        raise DomainError("Unsupported company source contract")
    if (
        not value.get("source_id")
        or not value.get("version")
        or set(value.get("tables", {})) != set(KINDS)
    ):
        raise DomainError("Company source requires all three versioned native tables")
    for kind, table in value["tables"].items():
        columns, rows = table.get("columns"), table.get("rows")
        if (
            not isinstance(columns, list)
            or len(columns) != len(set(columns))
            or not {"id", "boundary_id", "occurred_at"} <= set(columns)
        ):
            raise DomainError("Company table requires explicit unique source columns")
        if not isinstance(rows, list) or len(rows) > 100000:
            raise DomainError("Invalid company table size")
        ids = set()
        for row in rows:
            if (
                set(row) != set(columns)
                or any(not isinstance(v, str) for v in row.values())
                or not row["id"]
                or row["id"] in ids
            ):
                raise DomainError(
                    "Company table rows require unique IDs and exact native string fields"
                )
            ids.add(row["id"])
            _instant(row["occurred_at"])
        parent_kind, parent_key = KINDS[kind]
        if parent_kind:
            parents = {r["id"]: r for r in value["tables"][parent_kind]["rows"]}
            if parent_key not in columns or any(
                r[parent_key] not in parents
                or r["boundary_id"] != parents[r[parent_key]]["boundary_id"]
                for r in rows
            ):
                raise DomainError("Company source contains an orphan or wrong-boundary child")
    _retain(frozen, data)
    source_hash = hashlib.sha256(data).hexdigest()
    _retain(directory / "source.sha256", (source_hash + "\n").encode())
    return value, source_hash, directory


def _find(state, collection, row_id):
    rows = [r for r in state[collection] if r["id"] == row_id]
    if len(rows) != 1:
        raise DomainError("Unknown or ambiguous engagement item", status=404)
    return rows[0]


def _parent(engine, state, selection_id, expected_kind, source_hash):
    row = _find(state, "selections", selection_id)
    selected = engine._selection(row)
    parent_row = _find(state, "populations", selected.population_id)
    parent = engine._population(parent_row)
    populations.validate_selection(parent, selected)
    company = parent_row.get("company_support", {})
    if (
        company.get("kind") != expected_kind
        or company.get("source_sha256") != source_hash
        or company.get("epoch") != state.get("generation_epoch", 0)
    ):
        raise DomainError(
            "Parent must be a delivered company population from the same "
            "frozen source and scope epoch"
        )
    request = _find(state, "requests", parent_row.get("request_id"))
    plan = request_plan(engine, state, request)
    if parent.rows != tuple(plan["population_rows"]):
        raise DomainError("Parent population no longer matches delivered original company rows")
    artifact = _find(state, "artifacts", parent_row.get("artifact_id"))
    if (
        artifact["id"] not in request["artifact_ids"]
        or artifact["status"] != "AVAILABLE"
        or artifact.get("origin") != "SYNTHETIC"
    ):
        raise DomainError("Parent source artifact has not been delivered")
    expected = next(
        a for a in plan["prepared_artifacts"] if a["name"] == plan["population_filename"]
    )
    if artifact["sha256"] != expected["sha256"]:
        raise DomainError("Parent source artifact differs from the frozen company delivery")
    engine.artifacts.read(artifact)
    return parent, selected, parent_row


def create_request(engine, state, payload, stamped):
    """Return a draft PBC. Caller appends it once inside its authorized transaction."""
    if state["phase"] != "ACTIVE":
        raise DomainError("Kickoff must precede company population requests")
    allowed = {
        "support_kind",
        "parent_selection_id",
        "control_id",
        "boundary_id",
        "purpose",
        "rationale",
    }
    if set(payload) - allowed:
        raise DomainError("Company support request contains unsupported fields")
    kind = payload.get("support_kind")
    if kind not in KINDS:
        raise DomainError("Choose sites, tickets or support")
    for field in ("purpose", "rationale"):
        if (
            not isinstance(payload.get(field), str)
            or not payload[field].strip()
            or len(payload[field]) > 20000
        ):
            raise DomainError("Company support requires a bounded purpose and rationale")
    source, source_hash, directory = _source(engine, state)
    parent_kind, parent_key = KINDS[kind]
    parent = selected = parent_row = None
    if parent_kind:
        parent, selected, parent_row = _parent(
            engine, state, payload.get("parent_selection_id"), parent_kind, source_hash
        )
        boundary = parent.scope["boundary_id"]
        start, end = parent.scope["period_start"], parent.scope["period_end"]
        control_id = parent_row["company_support"]["control_id"]
        if (
            payload.get("boundary_id", boundary) != boundary
            or payload.get("control_id", control_id) != control_id
        ):
            raise DomainError("Child request cannot change its parent control or boundary")
    else:
        if payload.get("parent_selection_id"):
            raise DomainError("Initial sites population does not take a parent selection")
        boundary, control_id = payload.get("boundary_id"), payload.get("control_id")
        start, end = _scope_period(state["scope"])
    if boundary not in state["scope"]["boundaries"]:
        raise DomainError("Company support boundary is outside the active scope")
    control = _find(state, "controls", control_id)
    if control_id not in source["applicable_control_ids"] or boundary not in source["boundaries"]:
        raise DomainError(
            "No company source is authored for this control and boundary",
            code="COMPANY_SOURCE_SCOPE_UNAVAILABLE",
        )
    if (
        not _instant(source["period_start"])
        <= _instant(start)
        <= _instant(end)
        <= _instant(source["period_end"])
    ):
        raise DomainError(
            "Requested period exceeds retained source coverage",
            code="COMPANY_SOURCE_PERIOD_UNAVAILABLE",
        )
    custodian = control["assignment"].get("custodian_person_id")
    if custodian not in {p["id"] for p in state["people"]}:
        raise DomainError("Resolve a scoped company custodian before requesting support")
    table = source["tables"][kind]
    parent_ids = set(selected.all_ids) if selected else None
    rows = [
        r
        for r in table["rows"]
        if r["boundary_id"] == boundary
        and (
            (
                _instant(r.get("valid_from", r["occurred_at"])) <= _instant(end)
                and _instant(r.get("valid_to", source["period_end"])) >= _instant(start)
            )
            if kind == "sites"
            else _instant(start) <= _instant(r["occurred_at"]) <= _instant(end)
        )
        and (parent_ids is None or r[parent_key] in parent_ids)
    ]
    scope = {
        "boundary_id": boundary,
        "unit": kind,
        "timezone": state["scope"].get("timezone", "UTC"),
        "period_start": start,
        "period_end": end,
    }
    request_id = (
        "PBC-"
        + digest(
            [
                state["id"],
                state.get("generation_epoch", 0),
                payload,
                source_hash,
                selected.sha256 if selected else None,
            ]
        )[:24]
    )
    if any(r["id"] == request_id for r in state["requests"]):
        raise DomainError(
            "This exact company support request already exists; use its request and follow-up"
        )
    provenance = {
        "source_id": source["source_id"],
        "source_version": source["version"],
        "source_packet_sha256": source_hash,
        "query": payload["purpose"],
        "scope": scope,
        "source_kind": kind,
        "selected_parent_ids": list(selected.all_ids) if selected else [],
        "parent_selection_id": selected.id if selected else None,
        "parent_selection_digest": selected.sha256 if selected else None,
        "parent_population_digest": parent.sha256 if parent else None,
        "delivered_row_count": len(rows),
        "row_sha256": {r["id"]: digest(r) for r in rows},
        "completeness_representation": (
            "Company-supplied scoped source extraction; "
            "independent completeness and sampling sufficiency remain unestablished"
        ),
        "origin": source["origin"],
        "canonical_context": source.get("canonical_context", {}),
    }
    filename = kind + "-population.csv"
    recipe = {"format": "csv", "columns": table["columns"], "rows": rows}
    data, _ = render(recipe)
    if list(csv.DictReader(io.StringIO(data.decode("utf-8-sig")))) != rows:
        raise DomainError("Native source fields cannot be changed by CSV safety projection")
    plan_path = directory / (request_id + ".json")
    previous_plan = json.loads(_private_bytes(plan_path)) if plan_path.exists() else None
    if previous_plan and (
        previous_plan.get("engagement_id") != state["id"]
        or previous_plan.get("request_id") != request_id
        or previous_plan.get("source") != provenance
        or previous_plan.get("population_rows") != rows
    ):
        raise DomainError(
            "Retained request plan differs from the exact requested source projection"
        )
    prepared = []
    for name, content in [
        (filename, data),
        (kind + "-source-provenance.json", render({"format": "json", "document": provenance})[0]),
    ]:
        if previous_plan:
            artifact = next(a for a in previous_plan["prepared_artifacts"] if a["name"] == name)
            if engine.artifacts.read(artifact) != content:
                raise DomainError("Retained original differs on company request retry")
        else:
            artifact = engine.artifacts.retain(
                state["id"],
                name,
                content,
                source={"kind": "COMPANY_PARENT_SUPPORT", **provenance},
                coverage=scope,
                lineage=[parent_row["artifact_id"]] if parent_row else [],
                generated=True,
            )
            artifact["available_at"] = end
        prepared.append(artifact)
    plan = {
        "engagement_id": state["id"],
        "request_id": request_id,
        "source_sha256": source_hash,
        "kind": kind,
        "control_id": control_id,
        "scope": scope,
        "population_rows": rows,
        "population_filename": filename,
        "parent_selection_id": selected.id if selected else None,
        "parent_key": parent_key,
        "source": provenance,
        "prepared_artifacts": prepared,
    }
    plan_data = (canonical(plan) + "\n").encode()
    _retain(directory / (request_id + ".json"), plan_data)
    return {
        "id": request_id,
        "title": kind.title() + " source records",
        "purpose": payload["purpose"],
        "rationale": payload["rationale"],
        "control_id": control_id,
        "boundary_id": boundary,
        "person_id": custodian,
        "status": "DRAFT",
        "history": [],
        "artifact_ids": [],
        "parent_support": {
            "plan_sha256": hashlib.sha256(plan_data).hexdigest(),
            "epoch": state.get("generation_epoch", 0),
            "kind": kind,
        },
        "parent_selection_id": selected.id if selected else None,
        **stamped,
    }


def request_plan(engine, state, request):
    """Read a frozen delivery plan; never accept a caller-chosen file path."""
    marker = request.get("parent_support", {})
    request_id = request.get("id", "")
    if not re.fullmatch(r"PBC-[0-9a-f]{24}", request_id):
        raise DomainError("Invalid company request identity")
    path = (
        epoch_directory(engine, state["id"], marker.get("epoch", -1))
        / "parent-support"
        / (request_id + ".json")
    )
    data = _private_bytes(path)
    if hashlib.sha256(data).hexdigest() != marker.get("plan_sha256"):
        raise DomainError("Frozen company request plan integrity failure")
    plan = json.loads(data)
    if plan["engagement_id"] != state["id"] or plan["request_id"] != request_id:
        raise DomainError("Company plan belongs to a different engagement or request")
    return plan


def import_delivered_population(engine, state, manifest, request, stamped):
    """Import exactly delivered source CSV rows with immutable parent lineage."""
    plan = request_plan(engine, state, request)
    if manifest["name"] != plan["population_filename"]:
        return
    if any(p.get("artifact_id") == manifest["id"] for p in state["populations"]):
        return
    expected = next(
        a for a in plan["prepared_artifacts"] if a["name"] == plan["population_filename"]
    )
    if (
        manifest["id"] not in request["artifact_ids"]
        or manifest["status"] != "AVAILABLE"
        or manifest["sha256"] != expected["sha256"]
        or manifest["id"] != expected["id"]
        or manifest.get("origin") != "SYNTHETIC"
        or manifest.get("engagement_id") != state["id"]
        or request["status"]
        not in {"ISSUED", "CLARIFICATION", "IN_PROGRESS", "ACKNOWLEDGED", "SUBMITTED"}
        or _instant(state["simulated_at"]) < _instant(expected["available_at"])
    ):
        raise DomainError("Company rows must be imported from the delivered original artifact")
    rows = list(csv.DictReader(io.StringIO(engine.artifacts.read(manifest).decode("utf-8-sig"))))
    if rows != plan["population_rows"]:
        raise DomainError("Delivered rows differ from the frozen company source projection")
    parent = selection = None
    if plan["parent_selection_id"]:
        selected = _find(state, "selections", plan["parent_selection_id"])
        selection = engine._selection(selected)
        parent = engine._population(_find(state, "populations", selection.population_id))
    obj = populations.create_population(
        "POP-" + digest([request["id"], manifest["sha256"]])[:24],
        1,
        rows,
        scope=plan["scope"],
        source={**plan["source"], "original_sha256": manifest["sha256"]},
        parent_population=parent,
        parent_selection=selection,
        parent_key=plan["parent_key"],
    )
    state["populations"].append(
        {
            "id": obj.id,
            "title": plan["kind"].title() + " company population",
            "version": 1,
            "count": len(rows),
            "rows": rows,
            "status": obj.status,
            "artifact_id": manifest["id"],
            "request_id": request["id"],
            "parent_selection_id": plan["parent_selection_id"],
            "immutable": asdict(obj),
            "company_support": {
                "kind": plan["kind"],
                "source_sha256": plan["source_sha256"],
                "control_id": plan["control_id"],
                "epoch": request["parent_support"]["epoch"],
            },
            **stamped,
        }
    )
