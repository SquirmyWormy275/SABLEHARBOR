"""One fictional workload's credential rotation, dependency update and actual byte copies."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_lifecycle_activity import FIELDS, VENDOR_SOURCE, read_inputs
from .company_lifecycle_activity import LifecycleSourceRef as NonhumanSourceRef
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-IAM-006"
QUALIFICATION = "FICTIONAL_NONHUMAN_IDENTITY_NOT_VENDOR_ACCOUNT_OR_DEPLOYMENT"
SOURCE_QUALIFICATION = "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT"


@dataclass(frozen=True)
class NonhumanIdentityRecipe:
    company_id: str
    source_store_id: str
    source_refs: tuple[NonhumanSourceRef, ...]
    source_versions_sha256: str
    branch_ids: tuple[str, str]
    identity_id: str
    workload_id: str
    target_id: str
    period_start: str
    rotation_at: str
    reconcile_at: str
    correction_at: str
    review_at: str
    period_end_exclusive: str
    local_requirement_basis: str


class LocalCopyIdentity:
    """Credential versions are inert numbers, not passwords/keys or real account credentials."""

    def __init__(self, identity_id, source_id, target_id):
        for value in (identity_id, source_id, target_id):
            _id(value)
        self.identity_id = identity_id
        self.source_id = source_id
        self.target_id = target_id
        self.current_version = 1
        self.retired_versions = []

    def authorize(self, identity_id, version, operation, resource):
        return (
            identity_id == self.identity_id
            and type(version) is int
            and version == self.current_version
            and (operation, resource)
            in {("READ_SOURCE", self.source_id), ("WRITE_ISOLATED_TARGET", self.target_id)}
        )

    def rotate(self):
        self.retired_versions.append(self.current_version)
        self.current_version += 1
        return {
            "current_version": self.current_version,
            "retired_versions": list(self.retired_versions),
        }

    def copy(self, identity_id, version, raw, source_id, target_id):
        permitted = self.authorize(
            identity_id, version, "READ_SOURCE", source_id
        ) and self.authorize(identity_id, version, "WRITE_ISOLATED_TARGET", target_id)
        if not permitted:
            return {
                "status": "AUTHORIZATION_DENIED",
                "copied_bytes": 0,
                "output_sha256": None,
                "output": None,
            }
        if not isinstance(raw, bytes) or len(raw) > 1024 * 1024:
            raise CompanyStoreError("Bounded native dataset bytes required")
        output = bytes(bytearray(raw))
        return {
            "status": "COPIED",
            "copied_bytes": len(output),
            "output_sha256": sha(output),
            "output": output,
        }


def _prepare(repository, source_root, recipe):
    for value in (
        recipe.company_id,
        recipe.source_store_id,
        recipe.identity_id,
        recipe.workload_id,
        recipe.target_id,
    ):
        _id(value)
    if (
        not recipe.identity_id.startswith("EXERCISE-SVC-")
        or not isinstance(recipe.branch_ids, tuple)
        or len(recipe.branch_ids) != 2
        or len(set(recipe.branch_ids)) != 2
        or not isinstance(recipe.local_requirement_basis, str)
        or not 1 <= len(recipe.local_requirement_basis.strip()) <= 2000
    ):
        raise CompanyStoreError(
            "Separate fictional identity, two branches and local requirements required"
        )
    for branch in recipe.branch_ids:
        _id(branch)
    start, rotation, checkpoint, correction, review, end = [
        datetime.fromisoformat(_time(getattr(recipe, key)))
        for key in (
            "period_start",
            "rotation_at",
            "reconcile_at",
            "correction_at",
            "review_at",
            "period_end_exclusive",
        )
    ]
    next_month = start.month + 3
    expected_end = (
        start.replace(year=start.year + (next_month > 12), month=((next_month - 1) % 12) + 1)
        if start.day == 1
        else None
    )
    if (
        start.month not in (1, 4, 7, 10)
        or start.day != 1
        or start.hour
        or start.minute
        or start.second
        or start.microsecond
        or expected_end != end
        or not start + timedelta(days=1)
        < rotation + timedelta(seconds=1)
        < checkpoint
        < correction
        < review
        < end
        or review.date() != (end - timedelta(days=1)).date()
    ):
        raise CompanyStoreError(
            "One explicit UTC calendar quarter and ordered change/review times required"
        )
    originals, pin = read_inputs(source_root, recipe.source_refs)
    if pin != recipe.source_versions_sha256 or len(originals) != 4:
        raise CompanyStoreError("Four exact original selected metadata pins required")
    if len({(r["company"], r["branch"]) for r in originals}) != 1:
        raise CompanyStoreError("One explicit original company and branch required")
    native = {}
    for row in originals:
        try:
            body = json.loads(row["content"])
        except (ValueError, UnicodeError) as error:
            raise CompanyStoreError("Original backup JSON required") from error
        if (
            row["company"] != recipe.company_id
            or row["origin"] != "AUTHORED_TRAINING_SOURCE"
            or row["event_at"] is None
            or datetime.fromisoformat(_time(row["event_at"])) > start
            or datetime.fromisoformat(_time(row["available_at"])) > start
            or not isinstance(body, dict)
            or body.get("classification") != SOURCE_QUALIFICATION
            or row["system"] in native
        ):
            raise CompanyStoreError("Available original local backup records required")
        native[row["system"]] = (row, body)
    if set(native) != {"inventory", "source_dataset", "credential_event", "backup_job"}:
        raise CompanyStoreError(
            "Exact dataset/inventory and historical credential/job records required"
        )
    if len({b.get("exercise_id") for _, b in native.values()}) != 1:
        raise CompanyStoreError("Original backup reference exercise differs")
    dataset_row, dataset = native["source_dataset"]
    if (
        not isinstance(dataset.get("dataset_id"), str)
        or len(dataset_row["content"]) > 1024 * 1024
        or dataset["dataset_id"]
        not in {d.get("dataset_id") for d in native["inventory"][1].get("datasets", [])}
        or native["backup_job"][1].get("source_sha256") != dataset_row["sha256"]
        or native["credential_event"][1].get("principal") == recipe.identity_id
    ):
        raise CompanyStoreError("Correlated original dataset and distinct new identity required")
    # Resolve selected dataset/credential refs only; other historical links remain historical.
    for system in ("source_dataset", "credential_event"):
        row = native[system][0]
        if not any(
            all(link.get(k) == row[k] for k in ("system", "record", "version", "sha256"))
            for link in native["backup_job"][1].get("source_refs", [])
        ):
            raise CompanyStoreError("Historical job must reference the exact selected originals")
    org = snapshot(repository, as_of=start.date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    if owner == reviewer or recipe.identity_id in {
        p["person_id"] for p in org["canonical_people"] + org["proposed_people"]
    }:
        raise CompanyStoreError("Distinct local identity and scoped review contacts required")
    pins = dict(org["source_sha256"])
    for name in [
        VENDOR_SOURCE,
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_lifecycle_activity.py",
        "enterprise/audit_suite/company_nonhuman_identity_activity.py",
    ]:
        pins[name] = sha((repository / name).read_bytes())
    return (
        originals,
        pin,
        native,
        assignment,
        pins,
        (start, rotation, checkpoint, correction, review, end),
    )


def generate_pair(destination, *, repository, source_root, recipe: NonhumanIdentityRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
        or destination.resolve().is_relative_to(Path(source_root).resolve())
    ):
        raise CompanyStoreError("New private output outside original source required")
    originals, pin, native, assignment, pins, times = _prepare(repository, source_root, recipe)
    start, rotation, checkpoint, correction, review, end = times
    dataset_row, dataset = native["source_dataset"]
    dataset_id = dataset["dataset_id"]
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    recipe_pin = sha(encoded(asdict(recipe)))
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
        "classification": QUALIFICATION,
        "identity_id": recipe.identity_id,
        "workload_id": recipe.workload_id,
        "owner_id": owner,
        "operating_reviewer_id": reviewer,
        "control_ids": [CONTROL],
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
    records = []
    with tempfile.TemporaryDirectory(prefix=".nonhuman-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        upstream = stage / "upstream"
        upstream.mkdir(mode=0o700)
        for i, row in enumerate(originals):
            p = upstream / f"{i:02d}.json"
            p.write_bytes(row["content"])
            p.chmod(0o600)
        for index, branch in enumerate(recipe.branch_ids):
            systems = [
                "identity_inventory",
                "credential_metadata",
                "consumer_configuration",
                "copy_attempts",
                "copied_dataset",
                "identity_reconciliation",
                "dependency_remediation",
                "identity_reviews",
            ]
            for system in systems:
                store.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer
                    if system in {"identity_reviews", "identity_reconciliation"}
                    else owner,
                )
            sequence = []
            versions = {}

            def add(
                system,
                record,
                at,
                body=None,
                raw=None,
                *,
                branch=branch,
                sequence=sequence,
                versions=versions,
            ):
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
                result = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    record,
                    expected_version=version - 1,
                    command_id=sha(encoded([recipe_pin, branch, system, record, version])),
                    event_at=_time(at.isoformat()),
                    available_at=_time(at.isoformat()),
                    content=content,
                    provenance={
                        "name": record + ".json",
                        "source_reference": record,
                        "classification": QUALIFICATION,
                        "control_ids": [CONTROL],
                        "operational_fact_status": "COMPUTED_LOCAL_REFERENCE_ONLY",
                        "source_sha256": pins,
                        "recipe_sha256": recipe_pin,
                        "source_store_id": recipe.source_store_id,
                        "upstream_versions_sha256": pin,
                        "new_identity_id": recipe.identity_id,
                        "original_payload_unchanged": raw is not None,
                    },
                )
                versions[system, record] = version
                ref = {k: result[k] for k in ("system", "record", "version", "sha256")}
                sequence.append(ref)
                records.append(result)
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
        if read_inputs(source_root, recipe.source_refs)[1] != pin:
            raise CompanyStoreError("Selected backup inputs changed during generation")
        result = {
            "status": "LOCAL_NONHUMAN_IDENTITY_CREATED",
            "qualification": QUALIFICATION,
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_records": source_refs,
            "source_metadata": [{k: v for k, v in r.items() if k != "content"} for r in originals],
            "source_versions_sha256": pin,
            "source_sha256": pins,
            "assignment": assignment,
            "upstream_files": {
                f"upstream/{i:02d}.json": r["sha256"] for i, r in enumerate(originals)
            },
            "records": records,
            "audit_created": False,
            "grants_created": False,
        }
        p = stage / "SOURCE_RECEIPT.json"
        p.write_bytes(encoded(result))
        p.chmod(0o600)
        publish(stage, destination)
    return result
