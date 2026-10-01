"""Auditor-owned isolated JSON byte recovery from actually retained company originals.

No runtime script, archive path, producer fixture, historical marker or private
source store is executed/read. Local checkpoint age is not application data age.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _json, _time
from .fresh_sec003_procedure import NATIVE_ID, require
from .source_library_audit import BUSINESS_REFERENCE, private_file, typed_content

TASK = "TASK-SH-BCM-003-corporate-TOE"
JSON_PREDICATE = {
    "schema": "SH_AUDITOR_TYPED_RETRY_CONFIGURATION_PREDICATE_V1",
    "required_fields": ["attempts", "timeout_ms", "max_total_ms"],
    "integer_rule": "exact_int_not_bool_positive",
    "minimum_budget_rule": "max_total_ms_at_least_timeout_ms",
    "scope": "LOCAL_CONFIGURATION_JSON_READABILITY_AND_MINIMUM_SINGLE_ATTEMPT_BUDGET_ONLY",
    "executes_source_code": False,
}
_PRESEALED_PREDICATE_BYTES = _json(JSON_PREDICATE).encode()
ROLE_SYSTEMS = {
    "restore_job": "backup-runtime-history.restore_job",
    "runtime_definition": "backup-runtime-history.runtime_definition",
    "operating_period_original": "period-history.operating_period_ledger",
    "backup_object": "backup-runtime-history.backup_object",
    "company_restored_dataset": "backup-runtime-history.restored_dataset",
    "comparison_configuration": "backup-runtime-history.source_dataset",
    "captured_configuration": "backup-runtime-history.source_dataset",
    "restore_credential": "backup-runtime-history.credential_event",
    "backup_credential": "backup-runtime-history.credential_event",
    "backup_job": "backup-runtime-history.backup_job",
    "producer_export": "configuration-runtime-history.configuration_export",
    "producer_runtime": "configuration-runtime-history.configuration_runtime",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CollectionContext:
    company: str
    branch: str
    engagement: str
    auditor: str
    simulated_at: str


def retained_inputs(engine, auditor, engagement, artifact_ids):
    """Read real retained originals; derive the cutoff from the bound engagement."""
    state = engine.store.get(auditor, engagement)
    bound = state.get("company_source_binding")
    require(
        bound is not None
        and engine.company_bindings.get(engagement) == bound
        and state.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION",
        "Activated actual company-source engagement required",
    )
    require(
        artifact_ids and len(set(artifact_ids)) == len(artifact_ids),
        "Distinct actually collected artifact IDs required",
    )
    artifacts = {item["id"]: item for item in state["artifacts"]}
    context = CollectionContext(
        bound["company"], bound["branch"], engagement, auditor, state["simulated_at"]
    )
    rows = []
    for artifact_id in artifact_ids:
        require(artifact_id in artifacts, "Actually retained company artifact required")
        artifact = artifacts[artifact_id]
        require(
            artifact["source"].get("kind") == "COLLECTED_COMPANY_SOURCE",
            "Prepared evidence cannot supply the byte-recovery method",
        )
        receipt = artifact["source"]["receipt"]
        rows.append(
            {
                "source": receipt["source"],
                "receipt": receipt,
                "content": engine.artifacts.read(artifact),
                "artifact_id": artifact_id,
                "artifact_sha256": artifact["sha256"],
            }
        )
    checked_originals(rows, context)
    return rows, context


def checked_originals(rows, context):
    result = {}
    for item in rows:
        source, raw, receipt = item["source"], item["content"], item["receipt"]
        require(
            type(source["version"]) is int
            and source["version"] >= 1
            and source["company"] == context.company
            and source["branch"] == context.branch
            and receipt["source"] == source
            and receipt["principal_id"] == context.auditor
            and receipt["engagement_id"] == context.engagement
            and sha(raw) == source["sha256"] == item["artifact_sha256"]
            and len(raw) == receipt["content_bytes"]
            and _time(source["available_at"])
            <= _time(receipt["simulated_as_of"])
            <= _time(context.simulated_at)
            and (
                source["event_at"] is None
                or _time(source["event_at"]) <= _time(receipt["simulated_as_of"])
            )
            and _time(source["imported_at"])
            <= _time(receipt["collected_at"])
            <= _time(datetime.now(UTC).isoformat()),
            "Retained company byte custody, branch, clocks or audit receipt differs",
        )
        typed_content({**source, "content": raw})
        key = tuple(source[k] for k in NATIVE_ID)
        require(key not in result, "Duplicate exact retained company original")
        result[key] = {
            **item,
            "source": json.loads(_json(source)),
            "receipt": json.loads(_json(receipt)),
            "content": raw,
        }
    return result


def reference(source):
    return {k: source[k] for k in BUSINESS_REFERENCE}


def join(pointer, originals):
    require(
        isinstance(pointer, dict)
        and set(BUSINESS_REFERENCE) <= pointer.keys()
        and pointer.keys() <= set(BUSINESS_REFERENCE) | {"imported_at"}
        and type(pointer["version"]) is int
        and pointer["version"] >= 1,
        "Exact native version and digest reference required",
    )
    item = originals.get(tuple(pointer[k] for k in NATIVE_ID))
    if item is None:
        return None
    require(
        all(k in item["source"] and item["source"][k] == value for k, value in pointer.items()),
        "Collected exact native pointer differs",
    )
    return item


def body(item):
    data, mime = typed_content({**item["source"], "content": item["content"]})
    require(
        mime == "application/json" and isinstance(data, dict),
        "Collected native JSON object required",
    )
    return data


def native_role(item, role):
    system = ROLE_SYSTEMS[role]
    require(
        item["source"]["system"] == system
        and ("logical_family" not in item or item["logical_family"] == system.split(".", 1)[0])
        and ("logical_system" not in item or item["logical_system"] == system.split(".", 1)[1]),
        "Collected original has another actual native operating role: " + role,
    )


def available_to(item, when):
    source = item["source"]
    return _time(source["available_at"]) <= _time(when) and (
        source["event_at"] is None or _time(source["event_at"]) <= _time(when)
    )


def published_join(header, originals):
    """Resolve core custody, retaining declared business extras as attribution."""
    require(isinstance(header, dict), "Published admission header required")
    if not set(BUSINESS_REFERENCE) <= header.keys():
        require(
            isinstance(header.get("status"), str)
            and re.fullmatch(r"UPSTREAM-[0-9a-f]{24}", header.get("custody_id", "")),
            "Exact published header or explicitly restricted dependency required",
        )
        return None
    return join({k: header[k] for k in BUSINESS_REFERENCE}, originals)


def admission_observation(item, originals, *, runtime_item, dataset_id, label, needed):
    """Inspect separately retained operational admission, never archive recipes."""
    operational = item["source"]["provenance"].get("operational_metadata", {})
    admission = operational.get("source_admission")
    if not isinstance(admission, dict):
        return None, [label + ".source_admission"]
    require(
        {
            "dataset_id",
            "consumer_runtime_id",
            "consumer_runtime_sha256",
            "consumed_at",
            "source_pin",
            "source_definition_pin",
            "metadata",
            "definition_metadata",
            "original_metadata_digest_basis",
            "original_metadata_sha256",
            "projected_metadata_digest_basis",
            "projected_metadata_sha256",
        }
        <= admission.keys(),
        "Complete declared configuration source-admission metadata required",
    )
    require(
        admission["dataset_id"] == dataset_id
        and admission["consumer_runtime_id"] == body(runtime_item)["runtime_id"]
        and admission["consumer_runtime_sha256"] == runtime_item["source"]["sha256"]
        and admission["original_metadata_digest_basis"]
        == "EXACT_PRIVATE_ORIGINAL_EXPORT_AND_RUNTIME_METADATA_WITH_ORIGINAL_PROVENANCE"
        and re.fullmatch(r"[0-9a-f]{64}", admission["original_metadata_sha256"])
        and isinstance(admission["projected_metadata_digest_basis"], str)
        and admission["projected_metadata_digest_basis"],
        "Collected configuration admission runtime, dataset or digest basis differs",
    )
    pair = {"original": admission["metadata"], "definition": admission["definition_metadata"]}
    require(
        sha(_json(pair).encode()) == admission["projected_metadata_sha256"],
        "Published configuration admission header-pair digest differs",
    )
    missing = []
    for role, pin, metadata in (
        ("producer_export", admission["source_pin"], pair["original"]),
        ("producer_runtime", admission["source_definition_pin"], pair["definition"]),
    ):
        target, corroboration = published_join(pin, originals), published_join(metadata, originals)
        require(
            target is None or corroboration is None or target["source"] == corroboration["source"],
            "Admission pin and published metadata resolve to different originals",
        )
        name = label + "." + role
        if target is None or corroboration is None:
            missing.append(name)
        else:
            needed[name] = target
    if missing:
        return None, missing
    exported = needed[label + ".producer_export"]
    definition = needed[label + ".producer_runtime"]
    body(definition)
    native_role(exported, "producer_export")
    native_role(definition, "producer_runtime")
    producer_facts = {}
    for role, target in (("export", exported), ("runtime", definition)):
        facts = target["source"]["provenance"].get("operational_metadata")
        if not isinstance(facts, dict) or not facts:
            return None, [label + ".producer_" + role + ".operational_metadata"]
        producer_facts[role] = facts
    consumed_at = _time(admission["consumed_at"])
    return {
        "consumer_source": reference(item["source"]),
        "consumed_at": consumed_at,
        "consumer_runtime_id": admission["consumer_runtime_id"],
        "consumer_runtime_sha256": admission["consumer_runtime_sha256"],
        "producer_export": reference(exported["source"]),
        "producer_runtime": reference(definition["source"]),
        "consumer_bytes_equal_collected_export": item["content"] == exported["content"],
        "producer_export_available_at_consumption": _time(exported["source"]["available_at"])
        <= consumed_at,
        "producer_runtime_available_at_consumption": _time(definition["source"]["available_at"])
        <= consumed_at,
        "producer_operational_facts": json.loads(_json(producer_facts)),
        "declared_admission": json.loads(_json(admission)),
        "projected_header_pair_digest_independently_verified": True,
        "original_archive_metadata_independently_authenticated": False,
        "archive_digest_relabelled_as_projected_metadata_digest": False,
    }, []


def positive_number(value):
    return type(value) in {int, float} and math.isfinite(value) and value >= 0


def credential_observation(item, job):
    data = body(item)
    at = _time(job["business_attempted_at"])
    return {
        "source": reference(item["source"]),
        "enabled": data["enabled"] is True,
        "principal_matches_company_performer": data["principal_id"] == job["performed_by"],
        "lease_covers_business_attempt": _time(data["valid_from"])
        <= at
        < _time(data["expires_at"]),
        "authority_attributed_to_company_source": data["authority"],
        "corporate_or_legal_authority_accepted": False,
    }


def unavailable(missing, sources, limitations=None):
    return {
        "schema": "SH_COLLECTED_LOCAL_BYTE_RECOVERY_METHOD_V1",
        "task_id": TASK,
        "status": "SUPPORT_UNAVAILABLE",
        "missing_exact_originals": missing,
        "contemporaneous_support_limitations": limitations or [],
        "collected_source_references": sources,
        "real_isolated_byte_restore_performed": False,
        "application_or_ephi_recovered_data_age_established": False,
        "historical_august_marker_restore_reperformed": False,
        "full_task_credit": False,
        "conclusion": "LIMITATION",
    }


def examine_restore(
    rows, *, context, restore_ref, runtime_ref, period_ref, scratch, predicate=None
):
    """Reperform one selected retained backup in a new auditor-owned file sandbox.

    The three supplied locators are auditor-selected source business metadata.
    A prior company failure/retest remains its own dated version, never a cure.
    """
    require(
        predicate is None or _json(predicate).encode() == _PRESEALED_PREDICATE_BYTES,
        "Exact presealed nonexecutable JSON predicate required",
    )
    predicate = json.loads(_PRESEALED_PREDICATE_BYTES)
    originals = checked_originals(rows, context)
    needed = {
        name: join(ref, originals)
        for name, ref in {
            "restore_job": restore_ref,
            "runtime_definition": runtime_ref,
            "operating_period_original": period_ref,
        }.items()
    }
    missing = [name for name, item in needed.items() if item is None]
    if missing:
        return unavailable(missing, [reference(i["source"]) for i in needed.values() if i])
    for role, item in needed.items():
        native_role(item, role)
    restore, runtime, period = (
        body(needed[k]) for k in ("restore_job", "runtime_definition", "operating_period_original")
    )
    require(
        runtime["plan"] == period["plan"]
        and runtime["declaration_original_sha256"]
        == needed["operating_period_original"]["source"]["sha256"],
        "Executed original runtime and operating-period declaration differ",
    )
    require(
        restore["runtime_id"] == runtime["runtime_id"]
        and restore["dataset_id"] in runtime["datasets"]
        and restore["operation"] == "RESTORE",
        "Selected restore belongs to another runtime/dataset",
    )
    binding = runtime["bindings"].get(needed["restore_job"]["source"]["record"])
    require(
        binding is not None
        and all(binding[k] == restore[k] for k in ("dataset_id", "occurrence_id", "operation")),
        "Selected restore is outside the original execution binding",
    )
    attempted = _time(restore["business_attempted_at"])
    plan = runtime["plan"]
    require(
        _time(plan["period_start"]) <= attempted < _time(plan["period_end_exclusive"]),
        "Selected restore outside its genuine declared local operating period",
    )
    require(
        positive_number(restore["actual_elapsed_seconds"])
        and isinstance(restore["duration_basis"], str),
        "Source duration must retain its actual declared basis",
    )
    for name, pointer in {
        "backup_object": restore["source_pin"],
        "company_restored_dataset": restore["object_pin"],
        "comparison_configuration": restore["comparison_source_pin"],
        "restore_credential": restore["lease_pin"],
    }.items():
        needed[name] = join(pointer, originals) if pointer is not None else None
    missing = [name for name, item in needed.items() if item is None]
    if missing:
        return unavailable(missing, [reference(i["source"]) for i in needed.values() if i])
    for role, item in needed.items():
        native_role(item, role)
    backup_pointer = reference(needed["backup_object"]["source"])
    candidates = []
    for item in originals.values():
        if item["source"]["system"] == ROLE_SYSTEMS["backup_job"]:
            data = body(item)
            pointer = data.get("object_pin")
            if pointer and all(pointer.get(k) == backup_pointer[k] for k in NATIVE_ID):
                if join(pointer, originals) is not None:
                    candidates.append((item, data))
    if len(candidates) != 1:
        return unavailable(
            ["unique_backup_job_original"], [reference(i["source"]) for i in needed.values()]
        )
    backup_item, backup = candidates[0]
    needed["backup_job"] = backup_item
    native_role(backup_item, "backup_job")
    require(
        backup["runtime_id"] == runtime["runtime_id"]
        and backup["dataset_id"] == restore["dataset_id"]
        and backup["operation"] == "BACKUP",
        "Backup runtime/dataset differs",
    )
    backup_binding = runtime["bindings"].get(backup_item["source"]["record"])
    require(
        backup_binding is not None
        and all(
            backup_binding[k] == backup[k] for k in ("dataset_id", "occurrence_id", "operation")
        )
        and _time(plan["period_start"])
        <= _time(backup["business_attempted_at"])
        < _time(plan["period_end_exclusive"]),
        "Selected backup is outside the original execution binding/period",
    )
    for name, pointer in {
        "captured_configuration": backup["source_pin"],
        "backup_credential": backup["lease_pin"],
    }.items():
        needed[name] = join(pointer, originals)
    missing = [name for name, item in needed.items() if item is None]
    if missing:
        return unavailable(missing, [reference(i["source"]) for i in needed.values() if i])
    for role, item in needed.items():
        native_role(item, role)
    admissions = {}
    missing = []
    for label in ("captured_configuration", "comparison_configuration"):
        observations, gaps = admission_observation(
            needed[label],
            originals,
            runtime_item=needed["runtime_definition"],
            dataset_id=restore["dataset_id"],
            label=label,
            needed=needed,
        )
        admissions[label] = observations
        missing.extend(gaps)
    if missing:
        return unavailable(missing, [reference(i["source"]) for i in needed.values() if i])
    limitations = []
    backup_attempted = _time(backup["business_attempted_at"])
    if backup_attempted > attempted:
        limitations.append(
            {
                "role": "backup_job",
                "source": reference(backup_item["source"]),
                "backup_business_attempted_at": backup_attempted,
                "restore_business_attempted_at": attempted,
                "basis": "BACKUP_ATTEMPT_AFTER_SELECTED_RESTORE_ATTEMPT",
            }
        )
    for role in ("captured_configuration", "backup_object"):
        stamp = needed[role]["source"]["event_at"]
        if stamp is None or _time(stamp) > backup_attempted:
            limitations.append(
                {
                    "role": role,
                    "source": reference(needed[role]["source"]),
                    "backup_business_attempted_at": backup_attempted,
                    "basis": "CAPTURE_TIME_UNKNOWN_OR_AFTER_SELECTED_BACKUP_ATTEMPT",
                }
            )
    copied_at = needed["company_restored_dataset"]["source"]["event_at"]
    if copied_at is not None and _time(copied_at) < attempted:
        limitations.append(
            {
                "role": "company_restored_dataset",
                "source": reference(needed["company_restored_dataset"]["source"]),
                "restore_business_attempted_at": attempted,
                "basis": "RECORDED_RESTORED_OBJECT_PRECEDES_SELECTED_RESTORE_ATTEMPT",
            }
        )
    for field in ("business_completed_at", "completed_at", "finished_at"):
        if field in restore and (
            restore[field] is None
            or _time(restore[field]) < attempted
            or (copied_at is not None and _time(restore[field]) < _time(copied_at))
        ):
            limitations.append(
                {
                    "role": "restore_job." + field,
                    "source": reference(needed["restore_job"]["source"]),
                    "restore_business_attempted_at": attempted,
                    "declared_completion_at": restore[field],
                    "basis": "DECLARED_COMPANY_COMPLETION_UNKNOWN_OR_PRECEDES_RESTORE_COPY",
                }
            )
    for operation, job in (("backup", backup), ("restore", restore)):
        when = job["business_attempted_at"]
        roles = ["runtime_definition", "operating_period_original", operation + "_credential"]
        if operation == "backup":
            roles.append("captured_configuration")
        else:
            roles.extend(["backup_object", "comparison_configuration"])
        for role in roles:
            if not available_to(needed[role], when):
                limitations.append(
                    {
                        "role": role,
                        "source": reference(needed[role]["source"]),
                        "required_at_company_operation": operation,
                        "business_attempted_at": when,
                        "basis": "COLLECTED_ORIGINAL_NOT_CONTEMPORANEOUSLY_AVAILABLE",
                    }
                )
        credential = credential_observation(needed[operation + "_credential"], job)
        if not all(
            credential[key]
            for key in (
                "enabled",
                "principal_matches_company_performer",
                "lease_covers_business_attempt",
            )
        ):
            limitations.append(
                {
                    "role": operation + "_credential",
                    "source": credential["source"],
                    "business_attempted_at": when,
                    "credential_observation": credential,
                    "basis": "DECLARED_COPY_LEASE_NOT_ENABLED_BOUND_AND_VALID_AT_ATTEMPT",
                }
            )
    for label, observations in admissions.items():
        when = backup["business_attempted_at"] if label == "captured_configuration" else attempted
        if _time(observations["consumed_at"]) > _time(when):
            limitations.append(
                {
                    "role": label + ".source_admission",
                    "source": observations["consumer_source"],
                    "consumed_at": observations["consumed_at"],
                    "business_attempted_at": when,
                    "basis": "CONFIGURATION_CONSUMPTION_AFTER_COMPANY_OPERATION",
                }
            )
        for role in ("producer_export", "producer_runtime"):
            if not available_to(needed[label + "." + role], observations["consumed_at"]):
                limitations.append(
                    {
                        "role": label + "." + role,
                        "source": reference(needed[label + "." + role]["source"]),
                        "consumed_at": observations["consumed_at"],
                        "basis": "PRODUCER_NOT_CONTEMPORANEOUSLY_AVAILABLE_AT_CONSUMPTION",
                    }
                )
    if limitations:
        return unavailable(
            [item["role"] for item in limitations],
            [reference(i["source"]) for i in needed.values()],
            limitations,
        )
    # Archive paths remain attributed company fields. Never open or execute them.
    scratch = Path(scratch).absolute()
    require(
        not scratch.exists()
        and not any(p.is_symlink() for p in [scratch, *scratch.parents])
        and stat.S_IMODE(scratch.parent.stat().st_mode) == 0o700,
        "New private unaliased auditor restore scratch required",
    )
    scratch.mkdir(mode=0o700)
    restored_path = scratch / "auditor-restored-configuration.json"
    started_at, started_ns = datetime.now(UTC).isoformat(), time.monotonic_ns()
    fd = os.open(restored_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    raw = needed["backup_object"]["content"]
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    private_file(restored_path)
    retained = restored_path.read_bytes()
    elapsed_ns = time.monotonic_ns() - started_ns
    completed_at = datetime.now(UTC).isoformat()
    decoded = json.loads(retained)
    fields = predicate["required_fields"]
    typed = isinstance(decoded, dict) and all(
        key in decoded and type(decoded[key]) is int and decoded[key] > 0 for key in fields
    )
    useful = typed and decoded["max_total_ms"] >= decoded["timeout_ms"]
    checkpoint_at = needed["backup_object"]["source"]["event_at"]
    snapshot_at = needed["captured_configuration"]["source"]["event_at"]

    def age(stamp):
        if stamp is None:
            return None
        return (
            datetime.fromisoformat(attempted) - datetime.fromisoformat(_time(stamp))
        ).total_seconds()

    return {
        "schema": "SH_COLLECTED_LOCAL_BYTE_RECOVERY_METHOD_V1",
        "task_id": TASK,
        "status": "SELECTED_LOCAL_BYTE_EXAMINATION_PERFORMED",
        "conclusion": "LIMITATION",
        "source_service_id": runtime["service_id"],
        "source_runtime_id": runtime["runtime_id"],
        "source_operating_period_id": plan["period_id"],
        "dataset_id": restore["dataset_id"],
        "selected_restore": reference(needed["restore_job"]["source"]),
        "collected_source_references": {name: reference(i["source"]) for name, i in needed.items()},
        "company_operation_attribution": {
            "business_attempted_at": attempted,
            "native_event_at": needed["restore_job"]["source"]["event_at"],
            "available_at": needed["restore_job"]["source"]["available_at"],
            "actual_elapsed_seconds": restore["actual_elapsed_seconds"],
            "duration_basis": restore["duration_basis"],
            "status": restore["status"],
            "checkpoint_age_seconds": restore["checkpoint_age_seconds"],
            "source_reported_byte_match": restore["byte_copy_matches_selected_backup"],
            "source_reported_comparison_match": restore["comparison_bytes_equal"],
            "qualification": restore["qualification"],
        },
        "real_isolated_byte_restore_performed": True,
        "auditor_execution": {
            "started_at": started_at,
            "completed_at": completed_at,
            "elapsed_ns": elapsed_ns,
            "restored_path": str(restored_path),
            "restored_sha256": sha(retained),
            "bytes": len(retained),
            "operation": "NEW_ISOLATED_FILE_COPY_AND_TYPED_JSON_READ_ONLY",
        },
        "independent_byte_checks": {
            "auditor_restore_equals_selected_backup": retained == raw,
            "backup_equals_its_captured_source": raw == needed["captured_configuration"]["content"],
            "company_restore_equals_selected_backup": needed["company_restored_dataset"]["content"]
            == raw,
            "company_restore_equals_selected_comparison": needed["company_restored_dataset"][
                "content"
            ]
            == needed["comparison_configuration"]["content"],
        },
        "typed_json_usability": {
            "predicate": predicate,
            "exact_positive_integer_fields": typed,
            "minimum_single_attempt_budget": useful,
            "application_workflow_usability_established": False,
        },
        "source_input_availability_at_company_attempt": {
            "captured_configuration_available_to_backup": _time(
                needed["captured_configuration"]["source"]["available_at"]
            )
            <= _time(backup["business_attempted_at"]),
            "selected_backup_available_to_restore": _time(
                needed["backup_object"]["source"]["available_at"]
            )
            <= attempted,
            "comparison_configuration_available_to_restore": _time(
                needed["comparison_configuration"]["source"]["available_at"]
            )
            <= attempted,
        },
        "attributable_local_age": {
            "backup_checkpoint_age_seconds": age(checkpoint_at),
            "configuration_capture_event_age_seconds": age(snapshot_at),
            "source_reported_checkpoint_age_agrees": age(checkpoint_at)
            == restore["checkpoint_age_seconds"],
            "age_basis": "SOURCE_BUSINESS_ATTEMPT_MINUS_SELECTED_NATIVE_EVENT",
            "application_or_ephi_data_as_of_established": False,
        },
        "credential_observations": {
            "backup": credential_observation(needed["backup_credential"], backup),
            "restore": credential_observation(needed["restore_credential"], restore),
        },
        "configuration_admission_observations": admissions,
        "runtime_qualification": runtime["qualification"],
        "original_archive_runtime_executed_by_auditor": False,
        "historical_august_marker_restore_reperformed": False,
        "site_failover_or_ephi_recovery_established": False,
        "accepted_business_rto_rpo_established": False,
        "full_period_population_or_critical_dataset_risk_selection_established": False,
        "full_task_credit": False,
    }
