"""Bind private clean-company plans to a scoped training engagement.

This module contains no authored company answers. ``build_control`` returns a
private plan, never an authorized learner response. The caller must retain it
privately and enforce request permissions and ``available_by`` before rendering.
Native source exports remain explicitly forecast/model evidence.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .artifacts import safe_name

MAX_PLAN_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 20 * 1024 * 1024


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def control_contract(control: dict) -> dict:
    """Normalize native registry records and the engine's scoped projection."""
    data = control.get("data", control)
    return {
        "id": control["id"],
        "statement": data.get("statement", data.get("description", "")),
        "evidence_expectation": data.get("evidence_expectation", ""),
        "frequency": data.get("frequency_or_trigger", data.get("frequency", "")),
    }


def _private_file(root: Path, name: str) -> Path:
    root = root.resolve(strict=True)
    candidate = root / name
    if candidate.is_symlink() or candidate.resolve(strict=True).parent != root:
        raise ValueError("Private plan must be a direct regular file")
    if not candidate.is_file() or candidate.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("Invalid private plan file")
    if candidate.stat().st_mode & 0o077:
        raise ValueError("Private plan permissions must exclude group and other access")
    return candidate


def _instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid scope date") from exc
    if len(value) == 10:
        parsed = datetime.combine(date.fromisoformat(value), time(), UTC)
    if parsed.tzinfo is None:
        raise ValueError("Scope timestamps require timezone")
    return parsed.astimezone(UTC)


def _scope_instant(value: str, timezone: str, *, end_of_date: bool = False) -> datetime:
    if isinstance(value, str) and len(value) == 10:
        return datetime.combine(
            date.fromisoformat(value), time.max if end_of_date else time(), ZoneInfo(timezone)
        )
    # Offset-bearing values retain both their instant and declared offset.
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Scope timestamps require timezone")
    return parsed


def _bind(value, bindings):
    if isinstance(value, str):

        def replace(match):
            if match[1] not in bindings:
                raise ValueError("Unknown private binding token")
            return str(bindings[match[1]])

        return re.sub(r"\{\{([a-z_]+)\}\}", replace, value)
    if isinstance(value, list):
        return [_bind(item, bindings) for item in value]
    if isinstance(value, dict):
        return {key: _bind(item, bindings) for key, item in value.items()}
    return value


def _source_recipe(source: dict, repository: Path) -> tuple[dict, dict]:
    relative = source["path"]
    root = (repository / "docs/finance/evidence").resolve(strict=True)
    path = (repository / relative).resolve(strict=True)
    if not path.is_relative_to(root) or path.suffix != ".csv":
        raise ValueError("Source must be a finance evidence CSV inside repository")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Source export exceeds size limit")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source["sha256"]:
        raise ValueError("Source changed since private plan authoring")
    reader = csv.DictReader(raw.decode("utf-8-sig").splitlines())
    rows = list(reader)
    if not reader.fieldnames or len(rows) > 100000:
        raise ValueError("Invalid source table")
    recipe = {
        "format": "csv",
        "title": "Retained base 2027 model source: " + path.stem,
        "columns": reader.fieldnames,
        "rows": rows,
        "paragraphs": [
            (
                "Synthetic forecast source; not actual-period transactions or a "
                "third-party confirmation."
            )
        ],
    }
    return recipe, {
        "source_path": relative,
        "source_sha256": digest,
        "source_rows": len(rows),
        "source_basis": "RETAINED_BASE_2027_MODEL_NOT_ACTUAL_TRANSACTIONS",
    }


def occurrence_dates(
    frequency: str, start: datetime, end: datetime, *, planned_dates=()
) -> list[datetime]:
    """Calendar closes for named frequencies; other triggers use explicit dates.

    Calendar dates are training scheduling conventions, not requirements inferred
    from an assurance framework. Point-in-time observations are handled separately.
    """
    text = frequency.lower()
    if start > end:
        raise ValueError("Reversed occurrence interval")
    if start == end:
        return []
    values = []
    if any(word in text for word in ("monthly", "quarterly", "annual", "yearly")):
        for year in range(start.year, end.year + 1):
            for month in range(1, 13):
                if "quarter" in text and month not in {3, 6, 9, 12}:
                    continue
                if ("annual" in text or "yearly" in text) and month != 12:
                    continue
                value = datetime.combine(
                    date(year, month, calendar.monthrange(year, month)[1]), time.max, start.tzinfo
                )
                if start <= value <= end:
                    values.append(value)
    elif "daily" in text or "weekly" in text:
        day = start.date()
        while day <= end.date():
            value = datetime.combine(day, time.max, start.tzinfo)
            if ("daily" in text or day.weekday() == 4) and start <= value <= end:
                values.append(value)
            day += timedelta(days=1)
    else:
        planned = [
            datetime.combine(date.fromisoformat(value), time(), start.tzinfo)
            if len(value) == 10
            else _instant(value)
            for value in planned_dates
        ]
        values = sorted({value for value in planned if start <= value <= end})
    if len(values) > 3660:
        raise ValueError("Occurrence schedule exceeds supported bounds")
    return values


def build_control(control: dict, assignment: dict, scope: dict, *, private_root: Path) -> dict:
    """Return private facts, actor knowledge, dated requests and inert events.

    ``private_root`` names the clean directory. Scope requires period_start,
    period_end and boundary_id; optional repository enables pinned finance CSVs.
    ``owner_names`` may map assigned person IDs to period-valid display names.
    Plans must be mode 0600, contract-matched, and explicitly authored training
    material. Request coverage reports support status, never a test conclusion.
    """
    contract = control_contract(control)
    cid = contract["id"]
    if not re.fullmatch(r"SH-[A-Z]{3}-\d{3}", cid):
        raise ValueError("Invalid native control ID")
    path = _private_file(Path(private_root), cid + ".json")
    plan = json.loads(path.read_text())
    if plan.get("schema_version") != 1 or plan.get("control_contract") != contract:
        raise ValueError("Private clean plan does not match current control contract")
    if plan.get("origin") != "SYNTHETIC_TRAINING":
        raise ValueError("Clean plan must declare synthetic training origin")
    timezone = scope.get("timezone", "UTC")
    point_in_time = (
        scope.get("temporal_basis") == "POINT_IN_TIME"
        or str(scope.get("report_type", "")).replace(" ", "").upper() == "TYPE1"
        or (
            scope["period_start"] == scope["period_end"] and scope.get("temporal_basis") != "PERIOD"
        )
    )
    date_end = len(scope["period_end"]) == 10 and not point_in_time
    start = _scope_instant(scope["period_start"], timezone)
    end = _scope_instant(scope["period_end"], timezone, end_of_date=date_end)
    complete_available = end + timedelta(microseconds=1) if date_end else end
    if start > end:
        raise ValueError("Reversed engagement period")
    boundary = scope.get("boundary_id")
    if not isinstance(boundary, str) or not boundary.strip():
        raise ValueError("Explicit local boundary required")
    if assignment.get("control_id", cid) != cid:
        raise ValueError("Assignment is for another control")
    if assignment.get("status") == "HISTORICAL_ASSIGNMENT_REQUIRED":
        raise ValueError("A period-valid assignment or explicit organization overlay is required")
    if (
        assignment.get("effective_from")
        and _scope_instant(assignment["effective_from"], timezone) > start
    ):
        raise ValueError("Assignment begins after the scoped period")
    if (
        assignment.get("effective_to")
        and _scope_instant(assignment["effective_to"], timezone) <= end
    ):
        raise ValueError("Assignment does not cover the scoped period")
    owner = assignment.get("primary_person_id")
    reviewer = assignment.get("operating_reviewer_person_id")
    if not owner or not reviewer or reviewer in {owner, assignment.get("custodian_person_id")}:
        raise ValueError("Distinct assigned owner and operating reviewer are required")
    if reviewer == assignment.get("reviewer_person_id"):
        raise ValueError("Assurance reviewer cannot review their own operating approval")
    if reviewer == "AS-P009" or reviewer in scope.get("internal_audit_person_ids", []):
        raise ValueError("Internal Audit cannot approve management operating records")
    names = scope.get("owner_names", {})
    from .supporting_sources import demonstration_time

    bindings = {
        "control_id": cid,
        "boundary": boundary,
        "other_boundary": "fictional-counterfactual-" + boundary,
        "before_period_start": (start - timedelta(days=1)).isoformat(),
        "scheduled_demo_at": demonstration_time(scope),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "owner": names.get(owner, owner),
        "reviewer": names.get(reviewer, reviewer),
        "custodian": names.get(
            assignment.get("custodian_person_id"), assignment.get("custodian_person_id", owner)
        ),
    }
    bound = _bind(plan, bindings)
    if assignment.get("collective_approval_required"):
        support = bound.get("collective_decision_support", {})
        votes = support.get("votes", [])
        if not support.get("body_id") or not support.get("resolution_id") or not votes:
            raise ValueError("Collective approval requires retained individual member actions")
        member_ids = [v.get("director_id") for v in votes]
        if not all(member_ids) or len(member_ids) != len(set(member_ids)):
            raise ValueError("Collective member identities must be distinct")
        eligible = [
            v for v in votes if v.get("present") and v.get("eligible") and not v.get("recused")
        ]
        tally = support.get("tally", {})
        if tally.get("eligible_present") != len(eligible) or tally.get("votes_for") != sum(
            v.get("vote") == "FOR" for v in eligible
        ):
            raise ValueError("Collective member actions do not reconcile to retained tally")
        rule = support.get("meeting_rule", {})
        quorum, required = rule.get("required_quorum"), rule.get("votes_required")
        if (
            type(quorum) is not int
            or type(required) is not int
            or not 1 <= quorum <= len(votes)
            or not 1 <= required <= len(votes)
            or len(eligible) < quorum
            or tally["votes_for"] < required
        ):
            raise ValueError("Collective action does not satisfy its explicit meeting rule")
        if not any(a.get("recipe", {}).get("document") == support for a in bound["artifacts"]):
            raise ValueError("Collective member action record must be downloadable")

    reserved = {"id", "record_id", "boundary_id", "occurred_at", "effective_from", "effective_to"}
    if not isinstance(bound.get("record_fields"), dict) or reserved & set(bound["record_fields"]):
        raise ValueError("Private occurrence fields cannot replace scope or identity metadata")
    count = int(plan.get("occurrences", 1))
    if not 1 <= count <= 366:
        raise ValueError("Invalid authored occurrence count")
    moments = (
        [end]
        if point_in_time
        else occurrence_dates(
            contract["frequency"], start, end, planned_dates=bound.get("planned_dates", [])
        )
    )
    records = [
        {
            "id": f"{cid}-{i + 1:03d}",
            "record_id": f"{cid}-{i + 1:03d}",
            "boundary_id": boundary,
            "occurred_at": moment.isoformat(),
            **bound["record_fields"],
        }
        for i, moment in enumerate(moments)
    ]
    if bound.get("source_occurrences") and not point_in_time:
        occurrences = bound["source_occurrences"]
        if not isinstance(occurrences, list) or len(occurrences) > 10000:
            raise ValueError("Invalid authored source occurrence population")
        records = []
        seen = set()
        for occurrence in occurrences:
            moment = _instant(occurrence["occurred_at"])
            fields = occurrence["fields"]
            if not isinstance(fields, dict) or reserved & set(fields):
                raise ValueError("Source occurrence cannot replace scope metadata")
            if occurrence["id"] in seen:
                raise ValueError("Duplicate source occurrence identity")
            seen.add(occurrence["id"])
            if start <= moment <= end:
                records.append(
                    {
                        **bound["record_fields"],
                        **fields,
                        "id": occurrence["id"],
                        "record_id": occurrence["id"],
                        "boundary_id": boundary,
                        "occurred_at": moment.isoformat(),
                    }
                )
        records.sort(key=lambda item: (item["occurred_at"], item["id"]))
        moments = [_instant(item["occurred_at"]) for item in records]
    design_recipe = {
        "format": "pdf",
        "title": cid + " local control procedure",
        "paragraphs": [
            (
                "Synthetic training policy; thresholds and procedures are "
                "scenario assumptions, not assertions about SOC 2 or other "
                "standards."
            ),
            bound["policy"],
            "Explicit scenario policy criteria: " + _canonical(bound.get("policy_criteria", {})),
            "Frequency or trigger: " + contract["frequency"],
            "Execution: " + bound["process"],
            "Walkthrough: " + bound["walkthrough"],
            (
                "Before execution, reconcile the input scope and retain the "
                "source record. Record the action and obtain the assigned "
                "management record-quality review."
            ),
            (
                "If a required criterion is unmet, record and escalate the "
                "exception; completion requires an explicit authorized "
                "disposition."
            ),
            (
                "Retain the source, performed activity, reviewer decision and "
                "disposition under the applicable record schedule."
            ),
        ],
        "columns": [
            "control_id",
            "boundary_id",
            "effective_from",
            "effective_to",
            "owner",
            "reviewer",
            "frequency",
        ],
        "rows": [
            {
                "control_id": cid,
                "boundary_id": boundary,
                "effective_from": start.isoformat(),
                "effective_to": end.isoformat(),
                "owner": bindings["owner"],
                "reviewer": bindings["reviewer"],
                "frequency": contract["frequency"],
            }
        ],
    }
    requests = [
        {
            "id": cid + "-CLEAN-DESIGN",
            "title": "Local control procedure and walkthrough",
            "purpose": (
                "Inspect the scoped policy, responsibilities, execution steps and "
                "exception route before operating tests."
            ),
            "available_by": start.isoformat(),
            "artifact_recipes": [
                {
                    "name": "local-control-procedure.pdf",
                    "recipe": design_recipe,
                    "available_by": start.isoformat(),
                }
            ],
            "coverage": {
                "control_id": cid,
                "boundary_id": boundary,
                "kind": "DESIGN_SUPPORT",
                "professional_sufficiency": "NOT_ASSERTED",
            },
        }
    ]
    for index, artifact in enumerate(bound["artifacts"]):
        name = safe_name(artifact["name"])
        format_name = artifact["format"]
        is_design = artifact.get("timing") == "DESIGN"
        artifact_fields = artifact.get("record_fields", bound["record_fields"])
        if not isinstance(artifact_fields, dict):
            raise ValueError("Artifact fields must be an object")
        if "boundary_id" in artifact_fields and artifact_fields["boundary_id"] != boundary:
            raise ValueError("Artifact fields cannot change the scoped boundary")
        if "source_payload" in artifact_fields:
            artifact_fields = dict(artifact_fields)
            payload_bytes = _canonical(artifact_fields["source_payload"]).encode()
            artifact_fields["source_serialized_utf8"] = payload_bytes.decode()
            artifact_fields["source_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
        if (
            artifact.get("artifact_kind") == "PROVENANCE_MANIFEST"
            and "original_context" in artifact_fields
        ):
            artifact_fields = dict(artifact_fields)
            original = _canonical(artifact_fields["original_context"])
            artifact_fields["source_serialized_utf8"] = original
            artifact_fields["source_sha256"] = hashlib.sha256(original.encode()).hexdigest()
            artifact_fields["source_serialization"] = (
                "Exact UTF-8 bytes of source_serialized_utf8, without appended newline"
            )
            artifact_fields["transformation"] = (
                "Private template tokens bound before canonical source serialization and hashing"
            )
        if not records and not is_design and not artifact.get("recipe"):
            continue
        data = (
            [{"boundary_id": boundary, "effective_from": start.isoformat(), **artifact_fields}]
            if is_design
            else [
                {**artifact_fields, **item}
                if bound.get("source_occurrences")
                else {
                    **artifact_fields,
                    "id": item["id"],
                    "record_id": item["record_id"],
                    "boundary_id": boundary,
                    "occurred_at": item["occurred_at"],
                }
                for item in records
            ]
        )
        recipe = {
            "format": format_name,
            "title": artifact["title"],
            "paragraphs": [
                (
                    "Synthetic training company record; does not assert real "
                    "deployment or external acceptance."
                ),
                *artifact.get("paragraphs", []),
            ],
            "columns": list(data[0]) if data else [],
            "rows": data,
        }
        if artifact.get("recipe"):
            recipe = artifact["recipe"]
            if recipe.get("format") != format_name:
                raise ValueError("Artifact format and authored recipe disagree")
        if format_name == "xlsx" and not artifact.get("recipe"):
            recipe["total_columns"] = artifact.get("total_columns", [])
        available = start.isoformat() if is_design else complete_available.isoformat()
        coverage = {
            "control_id": cid,
            "boundary_id": boundary,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "expectation": artifact["expectation"],
            "support_status": artifact["support_status"],
            "professional_sufficiency": "NOT_ASSERTED",
        }
        requests.append(
            {
                "id": f"{cid}-CLEAN-{index + 1:02d}",
                "title": artifact["title"],
                "purpose": artifact["purpose"],
                "available_by": available,
                "artifact_recipes": [
                    {
                        "name": name,
                        "recipe": recipe,
                        "available_by": available,
                        **{
                            key: artifact[key]
                            for key in ("artifact_kind", "source_identity", "source_role")
                            if key in artifact
                        },
                    }
                ],
                "coverage": coverage,
            }
        )
    if records and not point_in_time:
        population = {
            "format": "csv",
            "title": cid + " authored occurrence population",
            "columns": list(records[0]),
            "rows": records,
        }
        requests.append(
            {
                "id": cid + "-CLEAN-POP",
                "title": "Occurrence population",
                "purpose": "Request and reconcile the scoped training population before sampling.",
                "available_by": complete_available.isoformat(),
                "artifact_recipes": [
                    {
                        "name": "occurrence-population.csv",
                        "recipe": population,
                        "available_by": complete_available.isoformat(),
                    }
                ],
                "coverage": {
                    "origin": "AUTHORED_TRAINING_POPULATION",
                    "independent_external_census": False,
                },
            }
        )
    sources = []
    for index, source in enumerate(plan.get("source_tables", [])):
        if start.year != 2027 or end.year != 2027:
            raise ValueError("Retained base 2027 finance exports require a 2027 scoped period")
        if not scope.get("repository"):
            raise ValueError("Repository path required for pinned finance sources")
        recipe, provenance = _source_recipe(source, Path(scope["repository"]))
        sources.append(provenance)
        requests.append(
            {
                "id": f"{cid}-CLEAN-SOURCE-{index + 1:02d}",
                "title": recipe["title"],
                "purpose": (
                    "Inspect retained model inputs separately from authored training approvals."
                ),
                "available_by": complete_available.isoformat(),
                "artifact_recipes": [
                    {
                        "name": f"model-source-{index + 1:02d}.csv",
                        "recipe": recipe,
                        "available_by": complete_available.isoformat(),
                    }
                ],
                "coverage": provenance,
            }
        )
    from .supporting_sources import requests as supporting_requests

    requests.extend(
        supporting_requests(
            bound.get("supporting_sources", []), control_id=cid, boundary_id=boundary
        )
    )
    return {
        "control_id": cid,
        "origin": "SYNTHETIC_TRAINING",
        "facts": {
            "policy": bound["policy"],
            "process": bound["process"],
            "walkthrough": bound["walkthrough"],
            "records": records,
            "sources": sources,
            "limitations": bound.get("limitations", []),
        },
        "actor_knowledge": [
            {
                "person_id": owner,
                "summary": bound["walkthrough"],
                "available_by": start.isoformat(),
            },
            {"person_id": reviewer, "summary": bound["process"], "available_by": start.isoformat()},
        ],
        "requests": requests,
        "events": [
            {
                "id": f"{cid}-CLEAN-EVENT-{i + 1:03d}",
                "scheduled_at": moment.isoformat(),
                "kind": "TRAINING_OCCURRENCE_AVAILABLE",
                "record_id": records[i]["record_id"],
            }
            for i, moment in enumerate(moments)
        ],
        "plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "coverage_status": plan["coverage_status"],
        "temporal_bounds": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "complete_available": complete_available.isoformat(),
            "date_only_point_basis": "LOCAL_MIDNIGHT_AS_OF_POINT",
            "date_only_period_basis": "INCLUSIVE_LOCAL_CALENDAR_DAYS",
        },
        "temporal_support": "POINT_IN_TIME_OBSERVATION_NOT_PERIOD_TOE"
        if point_in_time
        else "SCHEDULED_OPERATING_OCCURRENCES",
    }
