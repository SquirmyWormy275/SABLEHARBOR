"""Persistent inert credential/consumer operations; no vendor accounts or deployment."""

import os
import tempfile
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from . import company_nonhuman_identity_activity as seed
from .company_backup_runtime import checked_bytes, database, exact_pin, native, private, require
from .company_lifecycle_activity import FIELDS, LifecycleSourceRef, read_inputs
from .company_nonhuman_identity_activity import LocalCopyIdentity, NonhumanIdentityRecipe
from .company_nonhuman_risk_criterion import resolve as resolve_local_risk_criterion
from .company_operating_period import QUALIFICATION as PERIOD_QUALIFICATION
from .company_operating_period import SYSTEM as PERIOD_SYSTEM
from .company_operating_period import _plan
from .company_store import CompanyStore, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "PERSISTENT_INERT_NONHUMAN_COPY_NOT_VENDOR_ACCOUNT_OR_DEPLOYMENT"
SYSTEMS = ("nonhuman_definition", "nonhuman_source", "nonhuman_operation", "copied_dataset")
PAYLOADS = {
    "ROTATE": {"expected_credential_version", "occurrence_id"},
    "UPDATE_CONSUMER": {"credential_version"},
    "COPY": {"principal_id", "source_id", "target_id"},
    "REVIEW": {"occurrence_id"},
    "RECONCILE": set(),
}
MAX_COMMANDS = 128
MAX_ROW_BYTES = 512 * 1024
MAX_NATIVE_BYTES = 32 * 1024 * 1024


def _code():
    names = (
        "company_nonhuman_runtime.py",
        "company_nonhuman_risk_criterion.py",
        "company_nonhuman_identity_activity.py",
        "company_backup_runtime.py",
        "company_lifecycle_activity.py",
        "company_operating_period.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
    )
    return {n: sha(Path(__file__).with_name(n).read_bytes()) for n in names}


def _recipe(raw):
    require(isinstance(raw, dict), "Exact prior recipe required")
    return NonhumanIdentityRecipe(
        **{
            **raw,
            "branch_ids": tuple(raw["branch_ids"]),
            "source_refs": tuple(LifecycleSourceRef(**r) for r in raw["source_refs"]),
        }
    )


def _expected_seed(recipe, originals, pin, native, assignment, times, branch):
    start, rotation, checkpoint, correction, review, end = times
    dataset_row, dataset = native["source_dataset"]
    dataset_id = dataset["dataset_id"]
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    source_refs = [
        {k: r[k] for k in FIELDS}
        | {
            "source_store_id": recipe.source_store_id,
            "purpose": "DIRECT_DATA_INPUT"
            if r["system"] in {"source_dataset", "inventory"}
            else "HISTORICAL_MOTIVATION_NOT_NEW_IDENTITY_ACTIVITY",
        }
        for r in originals
    ]
    common = {
        "classification": seed.QUALIFICATION,
        "identity_id": recipe.identity_id,
        "workload_id": recipe.workload_id,
        "owner_id": owner,
        "operating_reviewer_id": reviewer,
        "control_ids": [seed.CONTROL],
        "boundary_id": "corporate",
        "source_records": source_refs,
        "source_versions_sha256": pin,
        "source_store_id": recipe.source_store_id,
        "period_start": _time(recipe.period_start),
        "period_end_exclusive": _time(recipe.period_end_exclusive),
        "site_references_only": dataset["sites"],
        "service_id": dataset["service_id"],
        "service_status": "DESIGN_REFERENCE_NOT_DEPLOYMENT",
        "data_scope": dataset["data_scope"],
        "identity_origin": "NEW_LOCAL_FICTIONAL_SERVICE_IDENTITY_NOT_ORIGINAL_HUMAN_PRINCIPAL",
        "authority_status": "PROPOSED_SCOPED_CONTACTS_AND_EXPLICIT_LOCAL_RULES",
        "credential_kind": "INERT_LOCAL_VERSION_NUMBER_NOT_USABLE_EXTERNAL_SECRET",
        "scope_limit": (
            "One workload; one credential change and quarter-end checkpoint; "
            "no ownership change or enterprise census"
        ),
    }
    permissions = [
        {"operation": "READ_SOURCE", "resource": dataset_id},
        {"operation": "WRITE_ISOLATED_TARGET", "resource": recipe.target_id},
    ]
    index = recipe.branch_ids.index(branch)
    expected, sequence, versions = [], [], {}

    def add(system, record, at, body=None, raw=None):
        version = versions.get((system, record), 0) + 1
        content = (
            raw
            if raw is not None
            else encoded(
                {
                    **common,
                    **body,
                    "record_id": record,
                    "recorded_at": _time(at.isoformat()),
                    "previous_events": list(sequence),
                }
            )
        )
        ref = {"system": system, "record": record, "version": version, "sha256": sha(content)}
        expected.append({**ref, "event_at": _time(at.isoformat()), "content": content})
        sequence.append(ref)
        versions[system, record] = version
        return ref

    identity = LocalCopyIdentity(recipe.identity_id, dataset_id, recipe.target_id)
    consumer_version = 1
    add(
        "identity_inventory",
        "IDENTITY",
        start,
        {
            "purpose": "Copy declared synthetic backup dataset to isolated local target",
            "permissions": permissions,
            "dependency_ids": [recipe.workload_id],
            "local_requirement_basis": recipe.local_requirement_basis,
            "created_by": owner,
            "rotation_at": _time(recipe.rotation_at),
            "quarter_review_at": _time(recipe.review_at),
            "ownership_changes_in_this_exercise": [],
        },
    )
    add(
        "credential_metadata",
        "CREDENTIAL",
        start,
        {"version": 1, "status": "CURRENT", "retired_versions": []},
    )
    add(
        "consumer_configuration",
        "CONSUMER",
        start,
        {
            "consumer_id": recipe.workload_id,
            "credential_version": 1,
            "source_id": dataset_id,
            "target_id": recipe.target_id,
        },
    )

    def attempt(record, at, consumer_version, *, identity=identity, add=add):
        result = identity.copy(
            recipe.identity_id,
            consumer_version,
            dataset_row["content"],
            dataset_id,
            recipe.target_id,
        )
        output = result.pop("output")
        ref = (
            add("copied_dataset", record + "-OUTPUT", at, raw=output)
            if output is not None
            else None
        )
        add(
            "copy_attempts",
            record,
            at,
            {
                **result,
                "configured_version": consumer_version,
                "current_credential_version": identity.current_version,
                "input_sha256": dataset_row["sha256"],
                "output_ref": ref,
                "consumer_id": recipe.workload_id,
            },
        )
        return result

    attempt("BASELINE", start + timedelta(minutes=1), consumer_version)
    rotation_state = identity.rotate()
    add(
        "credential_metadata",
        "CREDENTIAL",
        rotation,
        {
            "version": identity.current_version,
            "status": "CURRENT",
            "retired_versions": rotation_state["retired_versions"],
            "prior_version_status": "RETIRED",
        },
    )
    if index == 0:
        consumer_version = identity.current_version
        add(
            "consumer_configuration",
            "CONSUMER",
            rotation,
            {
                "consumer_id": recipe.workload_id,
                "credential_version": consumer_version,
                "source_id": dataset_id,
                "target_id": recipe.target_id,
            },
        )
    attempt("AFTER-ROTATION", rotation + timedelta(seconds=1), consumer_version)
    mismatch = consumer_version != identity.current_version
    add(
        "identity_reconciliation",
        "CHANGE-CHECK",
        checkpoint,
        {
            "declared_dependencies": [recipe.workload_id],
            "consumer_version": consumer_version,
            "active_credential_version": identity.current_version,
            "mismatched_dependency_ids": [recipe.workload_id] if mismatch else [],
            "owner_present": bool(owner),
            "permission_inventory": permissions,
        },
    )
    add(
        "identity_reviews",
        "CHANGE-REVIEW",
        checkpoint,
        {
            "reviewed_by": reviewer,
            "review_type": "CREDENTIAL_CHANGE",
            "mismatched_dependency_ids": [recipe.workload_id] if mismatch else [],
            "review_basis": (
                "Exact current credential and consumer records; no professional conclusion"
            ),
        },
    )
    add(
        "dependency_remediation",
        "FOLLOWUP",
        checkpoint,
        {
            "requested_dependency_updates": [recipe.workload_id] if mismatch else [],
            "assigned_to": owner,
            "source_record": "CHANGE-CHECK",
        },
    )
    prior = consumer_version
    if mismatch:
        consumer_version = identity.current_version
        add(
            "consumer_configuration",
            "CONSUMER",
            correction,
            {
                "consumer_id": recipe.workload_id,
                "credential_version": consumer_version,
                "source_id": dataset_id,
                "target_id": recipe.target_id,
            },
        )
    add(
        "dependency_remediation",
        "FOLLOWUP-ACTION",
        correction,
        {
            "previous_consumer_version": prior,
            "current_consumer_version": consumer_version,
            "update_performed": prior != consumer_version,
        },
    )
    attempt("AFTER-CORRECTION", correction, consumer_version)
    add(
        "copy_attempts",
        "RETIRED-VERSION-PROBE",
        correction,
        {
            "credential_version": 1,
            "operation": "READ_SOURCE",
            "resource": dataset_id,
            "authorization": "ALLOW"
            if identity.authorize(recipe.identity_id, 1, "READ_SOURCE", dataset_id)
            else "DENY",
            "output_ref": None,
        },
    )
    add(
        "copy_attempts",
        "UNDECLARED-OPERATION-PROBE",
        correction,
        {
            "credential_version": identity.current_version,
            "operation": "DELETE_SOURCE",
            "resource": dataset_id,
            "authorization": "ALLOW"
            if identity.authorize(
                recipe.identity_id, identity.current_version, "DELETE_SOURCE", dataset_id
            )
            else "DENY",
            "output_ref": None,
        },
    )
    add(
        "identity_reviews",
        "QUARTER-END-REVIEW",
        review,
        {
            "reviewed_by": reviewer,
            "review_type": "ONE_QUARTER_END_CHECKPOINT",
            "declared_identity_ids": [recipe.identity_id],
            "owner_by_identity": {recipe.identity_id: owner},
            "permissions": permissions,
            "consumer_version": consumer_version,
            "active_credential_version": identity.current_version,
            "mismatched_dependency_ids": [recipe.workload_id]
            if consumer_version != identity.current_version
            else [],
            "retired_versions": list(identity.retired_versions),
            "ownership_changes": [],
            "review_status": "LOCAL_RECONCILIATION_RECORDED_NOT_PROFESSIONAL_ASSESSMENT",
        },
    )
    return expected, dataset_row["content"], dataset_id


def _sources(prior_root, recipe, branch, refs, backup_root, at, historical_assignment=None):
    require(
        isinstance(recipe, NonhumanIdentityRecipe) and branch in recipe.branch_ids,
        "Typed original recipe and selected branch required",
    )
    originals, backup_digest = read_inputs(backup_root, recipe.source_refs)
    for row in originals:
        require(isinstance(decode(row["content"]), dict), "Strict original backup JSON required")
    if historical_assignment is None:
        prepared = seed._prepare(Path(__file__).resolve().parents[2], backup_root, recipe)
        original_rows, digest, indexed, assignment, _, times = prepared
    else:
        # Initial replay pinned these historical scoped actors. Current governance edits
        # cannot silently substitute another author for the original Q2 operations.
        original_rows, digest = originals, backup_digest
        assignment = historical_assignment
        indexed = {r["system"]: (r, decode(r["content"])) for r in originals}

        times = tuple(
            datetime.fromisoformat(_time(getattr(recipe, key)))
            for key in (
                "period_start",
                "rotation_at",
                "reconcile_at",
                "correction_at",
                "review_at",
                "period_end_exclusive",
            )
        )
    require(
        backup_digest == digest == recipe.source_versions_sha256,
        "Original backup changed during validation",
    )
    expected, raw, dataset_id = _expected_seed(
        recipe, original_rows, digest, indexed, assignment, times, branch
    )
    require(
        isinstance(refs, list) and len(refs) == len(expected) and len(refs) <= 32,
        "Complete bounded prior branch refs required",
    )
    for ref in refs:
        exact_pin(ref)
    require(
        len({tuple(r[k] for k in FIELDS[:-1]) for r in refs}) == len(refs),
        "Duplicate prior native identity",
    )
    with database(prior_root) as db:
        size = db.execute(
            "SELECT count(*),coalesce(max(length(content)+length(CAST(provenance AS BLOB))),0),"
            "coalesce(sum(length(content)+length(CAST(provenance AS BLOB))),0) "
            "FROM versions WHERE company=? AND branch=?",
            (recipe.company_id, branch),
        ).fetchone()
        require(
            size[0] == len(refs) and size[1] <= MAX_ROW_BYTES and size[2] <= 4 * 1024 * 1024,
            "Bounded exact prior native inventory required",
        )
        expression = " + ".join(
            f"COALESCE(length(CAST({field} AS BLOB)),0)"
            for field in (
                "company",
                "branch",
                "system",
                "record",
                "version",
                "event_at",
                "available_at",
                "imported_at",
                "origin",
                "provenance",
                "sha256",
                "command_id",
                "input_digest",
            )
        )
        metadata_sizes = db.execute(
            f"SELECT COALESCE(MAX({expression}),0),COALESCE(SUM({expression}),0) "
            "FROM versions WHERE company=? AND branch=?",
            (recipe.company_id, branch),
        ).fetchone()
        require(
            metadata_sizes[0] <= 128 * 1024 and metadata_sizes[1] <= 4 * 1024 * 1024,
            "Bounded prior native metadata required",
        )
        require(
            db.execute(
                "SELECT count(*) FROM versions WHERE company=? AND branch=? "
                "AND (typeof(version)!='integer' OR version<1)",
                (recipe.company_id, branch),
            ).fetchone()[0]
            == 0,
            "Typed prior native version required",
        )
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? "
                "ORDER BY company,branch,system,record,version",
                (recipe.company_id, branch),
            )
        ]
    by = {(r["system"], r["record"], r["version"]): r for r in rows}
    recipe_sha = sha(encoded(asdict(recipe)))
    for item in expected:
        row = by.get((item["system"], item["record"], item["version"]))
        require(
            row is not None and type(row["version"]) is int,
            "Typed complete prior native sequence required",
        )
        expected_pin = {k: row[k] for k in FIELDS}
        require(
            expected_pin in refs
            and row["content"] == item["content"]
            and row["sha256"] == item["sha256"],
            "Prior native sequence does not reperform",
        )
        provenance = decode(row["provenance"])
        require(
            isinstance(provenance, dict) and isinstance(provenance.get("source_sha256"), dict),
            "Prior provenance required",
        )
        source_pins = provenance["source_sha256"]
        require(
            1 <= len(source_pins) <= 64
            and all(
                isinstance(k, str)
                and isinstance(v, str)
                and len(v) == 64
                and set(v) <= set("0123456789abcdef")
                for k, v in source_pins.items()
            ),
            "Historical source pins required",
        )
        expected_provenance = {
            "name": row["record"] + ".json",
            "source_reference": row["record"],
            "classification": seed.QUALIFICATION,
            "control_ids": [seed.CONTROL],
            "operational_fact_status": "COMPUTED_LOCAL_REFERENCE_ONLY",
            "source_sha256": source_pins,
            "recipe_sha256": recipe_sha,
            "source_store_id": recipe.source_store_id,
            "upstream_versions_sha256": digest,
            "new_identity_id": recipe.identity_id,
            "original_payload_unchanged": row["system"] == "copied_dataset",
        }
        key = [row[k] for k in FIELDS[:4]]
        event = item["event_at"]
        command = sha(encoded([recipe_sha, branch, row["system"], row["record"], row["version"]]))
        require(
            encoded(provenance) == encoded(expected_provenance)
            and row["origin"] == "AUTHORED_TRAINING_SOURCE"
            and row["event_at"] == row["available_at"] == event
            and event <= at
            and row["command_id"] == command
            and row["input_digest"]
            == sha(
                _json(
                    [
                        key,
                        row["version"] - 1,
                        event,
                        event,
                        row["origin"],
                        provenance,
                        row["sha256"],
                    ]
                ).encode()
            ),
            "Prior native provenance, command identity or chronology differs",
        )
    metadata = [
        {k: r[k] for k in (*FIELDS, "event_at", "available_at", "origin", "provenance")}
        for r in rows
    ]
    imported = []
    for row in rows:
        require(
            isinstance(row["imported_at"], str) and _time(row["imported_at"]) == row["imported_at"],
            "Canonical prior actual import time required",
        )
        imported.append({**{k: row[k] for k in FIELDS}, "imported_at": row["imported_at"]})
    with database(backup_root) as db:
        for ref in recipe.source_refs:
            identity = tuple(getattr(ref, k) for k in FIELDS[:-1])
            predicate = "company=? AND branch=? AND system=? AND record=? AND version=?"
            size = db.execute(
                "SELECT length(CAST(imported_at AS BLOB)) FROM versions WHERE " + predicate,
                identity,
            ).fetchone()
            require(
                size is not None and size[0] is not None and size[0] <= 128,
                "Bounded backup import metadata required",
            )
            stamp = db.execute(
                "SELECT imported_at FROM versions WHERE " + predicate, identity
            ).fetchone()[0]
            require(
                isinstance(stamp, str) and _time(stamp) == stamp,
                "Canonical backup import time required",
            )
            imported.append({**asdict(ref), "imported_at": stamp})
    return sha(encoded(metadata)), raw, dataset_id, assignment, sha(encoded(imported))


def _declaration_native(root, ref, at):
    exact_pin(ref)
    fields = (
        "company",
        "branch",
        "system",
        "record",
        "version",
        "event_at",
        "available_at",
        "imported_at",
        "origin",
        "provenance",
        "sha256",
        "command_id",
        "input_digest",
    )
    expression = " + ".join(f"COALESCE(length(CAST({k} AS BLOB)),0)" for k in fields)
    predicate = "company=? AND branch=? AND system=? AND record=? AND version=?"
    identity = tuple(ref[k] for k in FIELDS[:-1])
    with database(root) as db:
        size = db.execute(
            f"SELECT length(content),{expression} FROM versions WHERE " + predicate, identity
        ).fetchone()
        require(
            size is not None and size[0] <= MAX_ROW_BYTES and size[1] <= 16384,
            "Bounded declaration bytes and metadata required",
        )
        row = dict(native(db, ref, at))
    require(
        type(row["version"]) is int
        and isinstance(row["imported_at"], str)
        and _time(row["imported_at"]) == row["imported_at"],
        "Typed declaration import metadata required",
    )
    return row


def _declaration(root, ref, at):
    exact_pin(ref)
    require(ref["system"] == PERIOD_SYSTEM, "Independent period declaration required")
    row = _declaration_native(root, ref, at)
    body = decode(row["content"])
    require(
        isinstance(body, dict) and body.get("kind") == "PERIOD_DECLARATION",
        "Native declaration required",
    )
    plan = _plan(body["plan"])
    provenance = {"source_reference": plan["period_id"], "qualification": PERIOD_QUALIFICATION}
    actual_provenance = decode(row["provenance"])
    if "name" in actual_provenance or "content_type" in actual_provenance:
        provenance.update(name=plan["period_id"] + ".json", content_type="application/json")
    key = [row[k] for k in FIELDS[:4]]
    require(
        body.get("qualification") == PERIOD_QUALIFICATION
        and encoded(decode(row["provenance"])) == encoded(provenance)
        and row["command_id"] == "period-" + sha(encoded(plan))[:48]
        and row["input_digest"]
        == sha(
            _json(
                [
                    key,
                    0,
                    row["event_at"],
                    row["available_at"],
                    row["origin"],
                    provenance,
                    row["sha256"],
                ]
            ).encode()
        ),
        "Declaration native provenance or command binding differs",
    )
    require(
        row["origin"] == "AUTHORED_TRAINING_SOURCE"
        and row["event_at"] == plan["declared_at"] <= row["available_at"] <= at,
        "Declaration chronology differs",
    )
    require(
        plan["control_ids"] == [seed.CONTROL]
        and (ref["company"], ref["branch"], ref["record"], ref["version"])
        == (plan["company_id"], plan["branch_id"], plan["period_id"], 1),
        "Exact IAM006 declaration required",
    )
    require(
        all(x["id"].startswith(("ROTATION-", "REVIEW-")) for x in plan["schedule"]),
        "Typed ROTATION-/REVIEW- occurrence identifiers required",
    )
    start, end = [datetime.fromisoformat(plan[k]) for k in ("period_start", "period_end_exclusive")]
    require(
        start.month in (1, 4, 7, 10)
        and start.day == 1
        and (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0),
        "Explicit full calendar quarters required",
    )
    quarter = start
    count = 0
    while quarter < end and count < 4:
        month = quarter.month + 3
        next_quarter = quarter.replace(year=quarter.year + (month > 12), month=(month - 1) % 12 + 1)
        reviews = [
            x
            for x in plan["schedule"]
            if x["id"].startswith("REVIEW-")
            and quarter <= datetime.fromisoformat(x["due_at"]) < next_quarter
        ]
        require(len(reviews) == 1, "Exactly one independent review due slot per declared quarter")
        quarter = next_quarter
        count += 1
    require(quarter == end and 1 <= count <= 4, "One to four complete declared quarters required")
    return plan


def _provenance(cfg):
    return {
        "classification": QUALIFICATION,
        "control_ids": [seed.CONTROL],
        "runtime_sha256": sha(encoded(cfg)),
        "declaration": cfg["declaration_pin"],
        "prior_native_refs": cfg["prior_refs"],
        "prior_metadata_sha256": cfg["prior_metadata_sha256"],
        "authority": "EXPLICIT_LOCAL_INERT_IDENTITY_OPERATIONS_NOT_VENDOR_ACCOUNT_APPROVAL",
    }


def _metadata(cfg, system, record, raw, at, command, imported_at):
    require(
        isinstance(imported_at, str) and _time(imported_at) == imported_at,
        "Exact actual import time required",
    )
    key = [cfg["plan"]["company_id"], cfg["plan"]["branch_id"], system, _id(record)]
    provenance = _provenance(cfg)
    digest = sha(raw)
    return {
        **dict(zip(FIELDS[:4], key, strict=True)),
        "version": 1,
        "event_at": at,
        "available_at": at,
        "imported_at": imported_at,
        "origin": "AUTHORED_TRAINING_SOURCE",
        "provenance": _json(provenance),
        "sha256": digest,
        "command_id": command,
        "input_digest": sha(
            _json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()
        ),
    }


def _verify_native(row, cfg, system, record, raw, at, command, imported_at):
    expected = _metadata(cfg, system, record, raw, at, command, imported_at)
    require(
        row is not None
        and encoded({k: row[k] for k in expected}) == encoded(expected)
        and row["content"] == raw,
        "Native bytes or metadata differ",
    )


def _insert(db, cfg, system, record, raw, at, command, imported_at):
    metadata = _metadata(cfg, system, record, raw, at, command, imported_at)
    require(
        len(raw) <= MAX_ROW_BYTES
        and sum(len(str(value).encode("utf-8")) for value in metadata.values()) <= 16384,
        "Native writer quota exceeded",
    )
    require(
        db.execute("SELECT coalesce(sum(length(content)),0) FROM versions").fetchone()[0] + len(raw)
        <= MAX_NATIVE_BYTES,
        "Native aggregate quota exceeded",
    )
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        tuple(metadata[k] for k in FIELDS[:4])
        + (
            1,
            at,
            at,
            metadata["imported_at"],
            metadata["origin"],
            metadata["provenance"],
            raw,
            metadata["sha256"],
            command,
            metadata["input_digest"],
        ),
    )
    return {k: metadata[k] for k in FIELDS}


def _opening():
    return {
        "credential_version": 2,
        "retired_versions": [1],
        "consumer_version": 2,
        "completed_occurrences": {},
        "copy_attempts": [],
        "latest_copy_sha256": None,
    }


def initialize(
    destination,
    *,
    repository,
    prior_root,
    prior_recipe,
    prior_branch,
    prior_refs,
    expected_prior_metadata_sha256,
    backup_source_root,
    declaration_root,
    declaration_pin,
    as_of,
    local_risk_criterion=None,
):
    destination = Path(destination)
    repository = Path(repository)
    require(
        repository.resolve() == Path(__file__).resolve().parents[2],
        "Repository must match maintained implementation checkout",
    )
    roots = [private(Path(p), True) for p in (prior_root, backup_source_root, declaration_root)]
    prior_root, backup_source_root, declaration_root = roots
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists()
        and all(
            not destination.is_relative_to(p) and not p.is_relative_to(destination) for p in roots
        ),
        "New separate private runtime required",
    )
    require(isinstance(prior_recipe, NonhumanIdentityRecipe), "Typed original recipe required")
    at = _time(as_of)
    prior_refs = decode(encoded(prior_refs))
    declaration_pin = decode(encoded(declaration_pin))
    digest, raw, dataset_id, seed_assignment, imported_digest = _sources(
        prior_root, prior_recipe, prior_branch, prior_refs, backup_source_root, at
    )
    require(digest == expected_prior_metadata_sha256, "Exact prior metadata pin required")
    plan = _declaration(declaration_root, declaration_pin, at)
    require(
        plan["declared_at"] <= at <= plan["period_start"]
        and plan["period_start"] == _time(prior_recipe.period_end_exclusive),
        "Initialize before immediately adjacent declared period",
    )
    require(
        plan["company_id"] == prior_recipe.company_id
        and plan["branch_id"] != prior_branch
        and {x["id"] for x in plan["inventory"]} == {prior_recipe.identity_id},
        "One original identity/new branch declaration required",
    )
    org = snapshot(repository, as_of=at[:10])
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == seed.CONTROL)
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    require(
        owner and reviewer and owner != reviewer and plan["owner_id"] == owner,
        "Distinct scoped owner/reviewer required",
    )
    pins = {
        **org["source_sha256"],
        "enterprise/audit_suite/company_nonhuman_runtime.py": sha(Path(__file__).read_bytes()),
    }
    cfg = {
        "format": "PERSISTENT_NONHUMAN_RUNTIME_V1",
        "plan": plan,
        "initialized_at": at,
        "initialized_imported_at": _now(),
        "prior_root": str(prior_root),
        "prior_recipe": asdict(prior_recipe),
        "prior_branch": prior_branch,
        "prior_refs": prior_refs,
        "prior_metadata_sha256": digest,
        "seed_assignment": seed_assignment,
        "source_imported_at_sha256": imported_digest,
        "backup_source_root": str(backup_source_root),
        "declaration_root": str(declaration_root),
        "declaration_pin": declaration_pin,
        "declaration_metadata_sha256": sha(
            encoded(
                {
                    k: v
                    for k, v in _declaration_native(declaration_root, declaration_pin, at).items()
                    if k != "content"
                }
            )
        ),
        "identity_id": prior_recipe.identity_id,
        "workload_id": prior_recipe.workload_id,
        "target_id": prior_recipe.target_id,
        "dataset_id": dataset_id,
        "dataset_sha256": sha(raw),
        "operator_id": owner,
        "reviewer_id": reviewer,
        "code_sha256": _code(),
        "source_sha256": pins,
        "qualification": QUALIFICATION,
    }
    if local_risk_criterion is not None:
        cfg["local_risk_criterion"] = resolve_local_risk_criterion(
            decode(encoded(local_risk_criterion)),
            scope={k: cfg[k] for k in ["identity_id", "workload_id", "dataset_id", "target_id"]},
            plan=plan,
            author=owner,
            reviewer=reviewer,
            as_of=at,
        )
    if "local_risk_criterion" in cfg:
        criterion_root = Path(cfg["local_risk_criterion"]["dependency"]["root"])
        require(
            not destination.is_relative_to(criterion_root)
            and not criterion_root.is_relative_to(destination),
            "Criterion and runtime must be separate roots",
        )
    encoded_cfg = encoded(cfg)
    require(
        len(encoded_cfg) <= MAX_ROW_BYTES and len(raw) <= MAX_ROW_BYTES,
        "Definition/dataset writer quota exceeded",
    )
    with tempfile.TemporaryDirectory(prefix=".nonhuman-runtime-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(
                plan["company_id"],
                plan["branch_id"],
                system,
                reviewer if system == "nonhuman_operation" else owner,
            )
        with (stage / "RUNTIME.json").open("xb") as f:
            os.chmod(stage / "RUNTIME.json", 0o600)
            f.write(encoded_cfg)
            f.flush()
            os.fsync(f.fileno())
        with database(stage, True) as db:
            db.executescript("""CREATE TABLE nonhuman_state(
                    revision INTEGER,last_event_at TEXT,state TEXT);
                CREATE TABLE nonhuman_commands(
                    command_id TEXT PRIMARY KEY,input_digest TEXT,receipt TEXT);
                CREATE TRIGGER nonhuman_no_update BEFORE UPDATE ON nonhuman_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;
                CREATE TRIGGER nonhuman_no_delete BEFORE DELETE ON nonhuman_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;""")
            db.execute("INSERT INTO nonhuman_state VALUES(?,?,?)", (0, at, _json(_opening())))
            _insert(
                db,
                cfg,
                "nonhuman_definition",
                plan["period_id"],
                encoded_cfg,
                at,
                "definition",
                cfg["initialized_imported_at"],
            )
            _insert(
                db,
                cfg,
                "nonhuman_source",
                dataset_id,
                raw,
                at,
                "source",
                cfg["initialized_imported_at"],
            )
        _source_check(cfg, at)
        require(
            all(sha((repository / k).read_bytes()) == v for k, v in pins.items())
            and cfg["code_sha256"] == _code(),
            "Implementation/scoped sources changed before publication",
        )
        publish(stage, destination)
    return {
        "runtime_sha256": sha(encoded_cfg),
        "revision": 0,
        "state_sha256": sha(encoded(_opening())),
        "native_versions": 2,
        "qualification": QUALIFICATION,
        "grants_created": False,
    }


def _config(root, expected):
    raw = checked_bytes(Path(root) / "RUNTIME.json", MAX_ROW_BYTES)
    require(sha(raw) == expected, "Runtime definition pin differs")
    cfg = decode(raw)
    require(
        cfg.get("format") == "PERSISTENT_NONHUMAN_RUNTIME_V1"
        and cfg.get("code_sha256") == _code()
        and cfg["source_sha256"].get("enterprise/audit_suite/company_nonhuman_runtime.py")
        == cfg["code_sha256"]["company_nonhuman_runtime.py"],
        "Retained implementation differs",
    )
    return cfg


def _source_check(cfg, at):
    if "local_risk_criterion" in cfg:
        retained = cfg["local_risk_criterion"]
        current = resolve_local_risk_criterion(
            retained["dependency"],
            scope={k: cfg[k] for k in ["identity_id", "workload_id", "dataset_id", "target_id"]},
            plan=cfg["plan"],
            author=cfg["operator_id"],
            reviewer=cfg["reviewer_id"],
            as_of=at,
        )
        require(encoded(current) == encoded(retained), "Retained local risk criterion changed")
    digest, raw, dataset_id, _, imported_digest = _sources(
        Path(cfg["prior_root"]),
        _recipe(cfg["prior_recipe"]),
        cfg["prior_branch"],
        cfg["prior_refs"],
        Path(cfg["backup_source_root"]),
        at,
        cfg["seed_assignment"],
    )
    require(
        digest == cfg["prior_metadata_sha256"]
        and imported_digest == cfg["source_imported_at_sha256"]
        and sha(raw) == cfg["dataset_sha256"]
        and dataset_id == cfg["dataset_id"]
        and encoded(_declaration(Path(cfg["declaration_root"]), cfg["declaration_pin"], at))
        == encoded(cfg["plan"])
        and sha(
            encoded(
                {
                    k: v
                    for k, v in _declaration_native(
                        Path(cfg["declaration_root"]), cfg["declaration_pin"], at
                    ).items()
                    if k != "content"
                }
            )
        )
        == cfg["declaration_metadata_sha256"],
        "Original source/declaration changed",
    )


def _reconciliation(cfg, state, at):
    due = sorted(x["id"] for x in cfg["plan"]["schedule"] if x["due_at"] <= at)
    return {
        "declared_due_ids": due,
        "missing_due_ids": sorted(set(due) - set(state["completed_occurrences"])),
        "credential_version": state["credential_version"],
        "consumer_version": state["consumer_version"],
        "dependency_current": state["consumer_version"] == state["credential_version"],
        "professional_review": "NOT_PERFORMED",
        "enterprise_population_completeness": "NOT_ESTABLISHED",
    }


def _apply(cfg, state, action, payload, actor, at, raw):
    require(
        isinstance(action, str)
        and action in PAYLOADS
        and isinstance(payload, dict)
        and set(payload) == PAYLOADS[action],
        "Exact supported action payload required",
    )
    require(
        actor == (cfg["reviewer_id"] if action == "REVIEW" else cfg["operator_id"]),
        "Scoped action actor required",
    )
    require(
        cfg["plan"]["period_start"] <= at < cfg["plan"]["period_end_exclusive"],
        "Operation outside declared period",
    )
    s = deepcopy(state)
    identity = LocalCopyIdentity(cfg["identity_id"], cfg["dataset_id"], cfg["target_id"])
    identity.current_version = s["credential_version"]
    identity.retired_versions = list(s["retired_versions"])
    observation = {}
    if action in {"ROTATE", "REVIEW"}:
        occurrence = payload["occurrence_id"]
        _id(occurrence)
        slot = next((x for x in cfg["plan"]["schedule"] if x["id"] == occurrence), None)
        require(
            slot is not None
            and occurrence.startswith("ROTATION-" if action == "ROTATE" else "REVIEW-")
            and slot["window_start"] <= at < slot["window_end_exclusive"]
            and occurrence not in s["completed_occurrences"],
            "Exact unperformed declared occurrence required",
        )
        require(
            all(x in s["completed_occurrences"] for x in slot["depends_on"]),
            "Occurrence predecessor missing",
        )
        s["completed_occurrences"][occurrence] = {"at": at, "action": action, "actor_id": actor}
    if action == "ROTATE":
        require(
            type(payload["expected_credential_version"]) is int
            and payload["expected_credential_version"] == s["credential_version"],
            "Exact current credential version required",
        )
        observation = identity.rotate()
        s["credential_version"] = identity.current_version
        s["retired_versions"] = identity.retired_versions
    elif action == "UPDATE_CONSUMER":
        require(
            type(payload["credential_version"]) is int
            and payload["credential_version"] == s["credential_version"],
            "Update must select exact active credential version",
        )
        observation = {
            "previous_version": s["consumer_version"],
            "current_version": payload["credential_version"],
        }
        s["consumer_version"] = payload["credential_version"]
    elif action == "COPY":
        for value in payload.values():
            _id(value)
        result = identity.copy(
            payload["principal_id"],
            s["consumer_version"],
            raw,
            payload["source_id"],
            payload["target_id"],
        )
        output = result.pop("output")
        observation = {
            **result,
            "consumer_version": s["consumer_version"],
            "active_credential_version": s["credential_version"],
        }
        if output is not None:
            require(output == raw, "Exact local bytes required")
            s["latest_copy_sha256"] = sha(output)
        s["copy_attempts"].append({"at": at, **observation})
    elif action == "REVIEW":
        observation = {
            "identity_id": cfg["identity_id"],
            "owner_id": cfg["operator_id"],
            "workload_id": cfg["workload_id"],
            "consumer_version": s["consumer_version"],
            "active_credential_version": s["credential_version"],
            "mismatched_dependency_ids": []
            if s["consumer_version"] == s["credential_version"]
            else [cfg["workload_id"]],
            "retired_versions": list(s["retired_versions"]),
            "review_status": "LOCAL_COMPUTED_RECONCILIATION_NOT_PROFESSIONAL_ASSESSMENT",
        }
    else:
        observation = _reconciliation(cfg, s, at)
    return s, observation


def _objects(db, cfg):
    plan = cfg["plan"]
    rows = db.execute(
        "SELECT * FROM versions WHERE system IN ('nonhuman_definition','nonhuman_source')"
    ).fetchall()
    require(len(rows) == 2, "Exact definition/object inventory required")
    by = {r["system"]: r for r in rows}
    for system, record, expected in (
        ("nonhuman_definition", plan["period_id"], sha(encoded(cfg))),
        ("nonhuman_source", cfg["dataset_id"], cfg["dataset_sha256"]),
    ):
        r = by.get(system)
        require(
            r is not None
            and (r["company"], r["branch"], r["record"], r["version"])
            == (plan["company_id"], plan["branch_id"], record, 1)
            and sha(r["content"]) == r["sha256"] == expected,
            "Native definition or protected bytes differ",
        )
        _verify_native(
            r,
            cfg,
            system,
            record,
            bytes(r["content"]),
            cfg["initialized_at"],
            "definition" if system == "nonhuman_definition" else "source",
            cfg["initialized_imported_at"],
        )
    return bytes(by["nonhuman_source"]["content"])


def _history(db, cfg):
    # SQL length checks precede every original, command or current-state materialization.
    for table, expression, count_limit, row_limit, total_limit in (
        (
            "versions",
            "length(CAST(content AS BLOB))",
            MAX_COMMANDS * 2 + 2,
            MAX_ROW_BYTES,
            MAX_NATIVE_BYTES,
        ),
        (
            "versions",
            " + ".join(
                f"COALESCE(length(CAST({field} AS BLOB)),0)"
                for field in (
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "event_at",
                    "available_at",
                    "imported_at",
                    "origin",
                    "provenance",
                    "sha256",
                    "command_id",
                    "input_digest",
                )
            ),
            MAX_COMMANDS * 2 + 2,
            16 * 1024,
            (MAX_COMMANDS * 2 + 2) * 16 * 1024,
        ),
        (
            "nonhuman_commands",
            "length(CAST(receipt AS BLOB))",
            MAX_COMMANDS,
            MAX_ROW_BYTES,
            MAX_NATIVE_BYTES,
        ),
        ("nonhuman_state", "length(CAST(state AS BLOB))", 1, MAX_ROW_BYTES, MAX_ROW_BYTES),
        (
            "nonhuman_commands",
            "COALESCE(length(CAST(command_id AS BLOB)),0) "
            "+ COALESCE(length(CAST(input_digest AS BLOB)),0)",
            MAX_COMMANDS,
            4096,
            MAX_COMMANDS * 4096,
        ),
        ("nonhuman_state", "length(CAST(last_event_at AS BLOB))", 1, 128, 128),
    ):
        sizes = db.execute(
            f"SELECT COUNT(*),COALESCE(MAX({expression}),0),"
            f"COALESCE(SUM({expression}),0) FROM {table}"
        ).fetchone()
        require(
            sizes[0] <= count_limit and sizes[1] <= row_limit and sizes[2] <= total_limit,
            "Bounded native history, command receipts and current state required",
        )
    require(
        db.execute(
            "SELECT count(*) FROM versions WHERE typeof(version)!='integer' OR version<1"
        ).fetchone()[0]
        == 0,
        "Typed bounded native versions required",
    )
    require(
        db.execute(
            "SELECT count(*) FROM nonhuman_state WHERE typeof(revision)!='integer' "
            "OR revision<0 OR revision> ?",
            (MAX_COMMANDS,),
        ).fetchone()[0]
        == 0,
        "Typed bounded state revision required",
    )
    systems_size = db.execute(
        "SELECT count(*),coalesce(max(COALESCE(length(CAST(company AS BLOB)),0)"
        "+COALESCE(length(CAST(branch AS BLOB)),0)"
        "+COALESCE(length(CAST(system AS BLOB)),0)"
        "+COALESCE(length(CAST(owner AS BLOB)),0)),0) FROM systems"
    ).fetchone()
    require(
        systems_size[0] == len(SYSTEMS) and systems_size[1] <= 1024,
        "Bounded exact registered systems required",
    )
    registered = [
        dict(r)
        for r in db.execute("SELECT company,branch,system,owner FROM systems ORDER BY system")
    ]
    expected_systems = [
        {
            "company": cfg["plan"]["company_id"],
            "branch": cfg["plan"]["branch_id"],
            "system": system,
            "owner": cfg["reviewer_id"] if system == "nonhuman_operation" else cfg["operator_id"],
        }
        for system in sorted(SYSTEMS)
    ]
    require(encoded(registered) == encoded(expected_systems), "Registered system custody differs")
    raw = _objects(db, cfg)
    rows = db.execute(
        "SELECT command_id,input_digest,receipt FROM nonhuman_commands ORDER BY rowid"
    ).fetchall()
    require(len(rows) <= MAX_COMMANDS, "Command history bound exceeded")
    state, at = _opening(), cfg["initialized_at"]
    receipts = {}
    copy_count = 0
    prior_imported_at = cfg["initialized_imported_at"]
    for revision, row in enumerate(rows, 1):
        receipt = decode(row["receipt"])
        require(
            isinstance(receipt, dict)
            and set(receipt)
            == {
                "command_id",
                "revision",
                "event_at",
                "imported_at",
                "runtime_sha256",
                "operation_pin",
                "copy_pin",
                "observation",
                "qualification",
            }
            and type(receipt["revision"]) is int
            and receipt["revision"] == revision
            and receipt["command_id"] == row["command_id"]
            and receipt["runtime_sha256"] == sha(encoded(cfg))
            and receipt["qualification"] == QUALIFICATION
            and isinstance(receipt["imported_at"], str)
            and _time(receipt["imported_at"]) == receipt["imported_at"] >= prior_imported_at,
            "Command receipt envelope differs",
        )
        original = native(db, receipt["operation_pin"])
        require(
            original["system"] == "nonhuman_operation"
            and original["record"] == row["command_id"]
            and original["company"] == cfg["plan"]["company_id"]
            and original["branch"] == cfg["plan"]["branch_id"]
            and original["version"] == 1
            and original["event_at"] == original["available_at"] == receipt["event_at"],
            "Native operation identity or time differs",
        )
        _verify_native(
            original,
            cfg,
            "nonhuman_operation",
            row["command_id"],
            bytes(original["content"]),
            receipt["event_at"],
            row["command_id"],
            receipt["imported_at"],
        )
        body = decode(original["content"])
        require(
            isinstance(body, dict)
            and set(body)
            == {"command", "before_sha256", "after", "observation", "qualification", "imported_at"}
            and body["imported_at"] == receipt["imported_at"],
            "Exact native operation body required",
        )
        require(body["qualification"] == QUALIFICATION, "Native qualification differs")
        command = body["command"]
        require(
            isinstance(command, dict)
            and set(command)
            == {
                "expected_revision",
                "expected_state_sha256",
                "command_id",
                "action",
                "payload",
                "actor_id",
                "event_at",
            }
            and type(command["expected_revision"]) is int
            and command["expected_revision"] == revision - 1
            and command["command_id"] == row["command_id"]
            and command["event_at"] == receipt["event_at"]
            and command["event_at"] >= at
            and sha(encoded(command)) == row["input_digest"]
            and body["before_sha256"] == sha(encoded(state))
            and command["expected_state_sha256"] == sha(encoded(state)),
            "Operation chain differs",
        )
        state, observed = _apply(
            cfg,
            state,
            command["action"],
            command["payload"],
            command["actor_id"],
            command["event_at"],
            raw,
        )
        require(
            encoded(state) == encoded(body["after"])
            and encoded(observed) == encoded(body["observation"])
            and encoded(observed) == encoded(receipt["observation"]),
            "Retained operation does not reperform",
        )
        copied = command["action"] == "COPY" and observed["status"] == "COPIED"
        if copied:
            copy_count += 1
            copy_row = native(db, receipt["copy_pin"])
            _verify_native(
                copy_row,
                cfg,
                "copied_dataset",
                row["command_id"],
                raw,
                command["event_at"],
                sha(encoded([row["command_id"], "copy"])),
                receipt["imported_at"],
            )
        else:
            require(receipt["copy_pin"] is None, "Denied/noncopy action cannot claim copied bytes")
        at = command["event_at"]
        prior_imported_at = receipt["imported_at"]
        receipts[row["command_id"]] = (row["input_digest"], receipt)
    current = db.execute("SELECT * FROM nonhuman_state").fetchall()
    require(
        len(current) == 1
        and current[0]["revision"] == len(rows)
        and current[0]["last_event_at"] == at
        and encoded(decode(current[0]["state"])) == encoded(state),
        "Current state differs from replayed native operations",
    )
    require(
        db.execute("SELECT count(*) FROM versions").fetchone()[0] == len(rows) + copy_count + 2,
        "Native/command inventory differs",
    )
    return state, at, receipts, raw


def execute(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    expected_state_sha256,
    command_id,
    action,
    payload,
    actor_id,
    event_at,
):
    root = private(Path(runtime), True)
    cfg = _config(root, expected_runtime_sha256)
    _id(command_id)
    _id(actor_id)
    require(
        type(expected_revision) is int and 0 <= expected_revision < MAX_COMMANDS,
        "Exact bounded revision required",
    )
    at = _time(event_at)
    command = {
        "expected_revision": expected_revision,
        "expected_state_sha256": expected_state_sha256,
        "command_id": command_id,
        "action": action,
        "payload": decode(encoded(payload)),
        "actor_id": actor_id,
        "event_at": at,
    }
    digest = sha(encoded(command))
    _source_check(cfg, at)
    with database(root, True) as db:
        state, latest_at, receipts, raw = _history(db, cfg)
        if command_id in receipts:
            require(receipts[command_id][0] == digest, "Changed command replay forbidden")
            result = receipts[command_id][1]
        else:
            require(
                len(receipts) == expected_revision
                and expected_state_sha256 == sha(encoded(state))
                and at >= latest_at
                and len(receipts) < MAX_COMMANDS,
                "Stale state/revision, backwards time or quota",
            )
            after, observation = _apply(cfg, state, action, command["payload"], actor_id, at, raw)
            imported_at = _now()
            require(
                imported_at
                >= max(
                    [
                        cfg["initialized_imported_at"],
                        *[r[1]["imported_at"] for r in receipts.values()],
                    ]
                ),
                "Actual import clock moved backwards",
            )
            copy_pin = None
            if action == "COPY" and observation["status"] == "COPIED":
                # Exact byte copy becomes a native original in this same transaction.
                copy_pin = _insert(
                    db,
                    cfg,
                    "copied_dataset",
                    command_id,
                    bytes(bytearray(raw)),
                    at,
                    sha(encoded([command_id, "copy"])),
                    imported_at,
                )
            body = {
                "command": command,
                "imported_at": imported_at,
                "before_sha256": sha(encoded(state)),
                "after": after,
                "observation": observation,
                "qualification": QUALIFICATION,
            }
            operation_pin = _insert(
                db,
                cfg,
                "nonhuman_operation",
                command_id,
                encoded(body),
                at,
                command_id,
                imported_at,
            )
            result = {
                "command_id": command_id,
                "revision": expected_revision + 1,
                "event_at": at,
                "imported_at": imported_at,
                "runtime_sha256": expected_runtime_sha256,
                "operation_pin": operation_pin,
                "copy_pin": copy_pin,
                "observation": observation,
                "qualification": QUALIFICATION,
            }
            require(
                len(_json(result).encode()) <= MAX_ROW_BYTES
                and len(_json(after).encode()) <= MAX_ROW_BYTES
                and db.execute(
                    "SELECT coalesce(sum(length(CAST(receipt AS BLOB))),0) FROM nonhuman_commands"
                ).fetchone()[0]
                + len(_json(result).encode())
                <= MAX_NATIVE_BYTES,
                "Receipt/state writer quota exceeded",
            )
            db.execute(
                "INSERT INTO nonhuman_commands VALUES(?,?,?)", (command_id, digest, _json(result))
            )
            db.execute(
                "UPDATE nonhuman_state SET revision=?,last_event_at=?,state=?",
                (expected_revision + 1, at, _json(after)),
            )
        _source_check(cfg, at)
        require(
            encoded(_config(root, expected_runtime_sha256)) == encoded(cfg),
            "Runtime definition changed during operation",
        )
    return result


def inspect(runtime, *, expected_runtime_sha256, as_of):
    root = private(Path(runtime), True)
    cfg = _config(root, expected_runtime_sha256)
    at = _time(as_of)
    with database(root) as db:
        state, latest, receipts, _ = _history(db, cfg)
        require(at >= latest, "Current state requires cutoff after latest event")
        result = {
            "revision": len(receipts),
            "as_of": at,
            "state": state,
            "state_sha256": sha(encoded(state)),
            "reconciliation": _reconciliation(cfg, state, at),
            "qualification": QUALIFICATION,
        }
    _source_check(cfg, at)
    require(
        encoded(_config(root, expected_runtime_sha256)) == encoded(cfg),
        "Definition changed during inspection",
    )
    return result
