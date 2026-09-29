"""Bounded fictional identity transitions from explicitly pinned source references."""

import json
import sqlite3
import tempfile
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROLS = ["SH-IAM-001", "SH-IAM-002", "SH-IAM-004"]
QUALIFICATION = "FICTIONAL_LOCAL_WORKER_LIFECYCLE_NOT_EMPLOYMENT_OR_VENDOR_DEPLOYMENT"
VENDOR_SOURCE = "docs/controls/CCF_ENTERPRISE_SECURITY_VENDOR_DECISIONS_2026-09-11.md"
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
CHANNELS = (
    "directory_account",
    "application_account",
    "application_session",
    "api_token",
    "remote_session",
    "physical_badge",
)
MAX_INPUT = 4 * 1024 * 1024


@dataclass(frozen=True)
class LifecycleSourceRef:
    company: str
    branch: str
    system: str
    record: str
    version: int
    sha256: str


@dataclass(frozen=True)
class LifecycleRecipe:
    company_id: str
    source_store_id: str
    source_refs: tuple[LifecycleSourceRef, ...]
    source_versions_sha256: str
    branch_ids: tuple[str, str]
    exercise_subject_id: str
    sponsor_person_id: str
    request_at: str
    start_at: str
    expires_at: str
    reconcile_at: str
    correction_at: str
    local_requirement_basis: str


def _source_stamp(path):
    if (
        not path.is_file()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or path.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (path, *path.parents))
    ):
        raise CompanyStoreError("Existing private original source required")
    info = path.stat()
    parent = path.parent.stat()
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_ctime_ns,
        parent.st_dev,
        parent.st_ino,
        parent.st_mode,
    )


def read_inputs(source_root, refs):
    """Read ONLY declared exact rows in one bounded read transaction, never initialize."""
    path = Path(source_root).absolute() / "company.sqlite3"
    initial_stamp = _source_stamp(path)
    if not isinstance(refs, tuple) or not 2 <= len(refs) <= 8:
        raise CompanyStoreError("Two to eight explicit original references required")
    identities = []
    for ref in refs:
        if not isinstance(ref, LifecycleSourceRef):
            raise CompanyStoreError("Typed exact original references required")
        for value in (ref.company, ref.branch, ref.system, ref.record):
            _id(value)
        if (
            type(ref.version) is not int
            or ref.version < 1
            or (
                not isinstance(ref.sha256, str)
                or len(ref.sha256) != 64
                or any(c not in "0123456789abcdef" for c in ref.sha256)
            )
        ):
            raise CompanyStoreError("Exact positive version and SHA required")
        identity = tuple(getattr(ref, k) for k in FIELDS[:-1])
        if identity in identities:
            raise CompanyStoreError("Duplicate original reference")
        identities.append(identity)
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows, total = [], 0
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        for ref, identity in zip(refs, identities, strict=True):
            predicate = "company=? AND branch=? AND system=? AND record=? AND version=?"
            sizes = db.execute(
                "SELECT length(content),length(CAST(provenance AS BLOB)) FROM versions WHERE "
                + predicate,
                identity,
            ).fetchall()
            if len(sizes) != 1 or any(type(v) is not int or v < 0 for v in sizes[0]):
                raise CompanyStoreError("Exact original unavailable")
            total += sum(sizes[0])
            if total > MAX_INPUT:
                raise CompanyStoreError("Original input quota exceeded")
            row = dict(
                db.execute(
                    "SELECT company,branch,system,record,version,sha256,content,"
                    "event_at,available_at,origin,provenance FROM versions WHERE " + predicate,
                    identity,
                ).fetchone()
            )
            if sha(row["content"]) != ref.sha256 or row["sha256"] != ref.sha256:
                raise CompanyStoreError("Original content pin mismatch")
            rows.append(row)
    finally:
        db.close()
    if _source_stamp(path) != initial_stamp:
        raise CompanyStoreError("Original source file identity or privacy changed during read")
    if sum(len(r["content"]) + len(r["provenance"].encode("utf-8")) for r in rows) > MAX_INPUT:
        raise CompanyStoreError("Original input quota exceeded")
    rows.sort(key=lambda r: tuple(r[k] for k in FIELDS[:-1]))
    return rows, sha(encoded([{k: v for k, v in row.items() if k != "content"} for row in rows]))


class LocalIdentity:
    """Data-only account/handle state; no host accounts, tokens, network or vendor APIs."""

    def __init__(self):
        self.subject = None
        self.rights = set()
        self.handles = {channel: False for channel in CHANNELS}

    def create(self, request):
        if (
            self.subject is not None
            or request.get("approved") is not True
            or not request.get("request_id")
            or not request.get("sponsor_person_id")
            or not str(request.get("subject_id", "")).startswith("EXERCISE-")
            or request.get("proofing_check") != "LOCAL_CORRELATION_ONLY"
        ):
            raise CompanyStoreError("Approved uniquely correlated local worker request required")
        self.subject = request["subject_id"]
        self.handles["directory_account"] = True

    def provision(self, approval):
        granted = approval.get("rights")
        if (
            self.subject is None
            or approval.get("subject_id") != self.subject
            or approval.get("approved") is not True
            or not approval.get("business_need")
            or approval.get("reviewer_id") == approval.get("provisioner_id")
            or not approval.get("reviewer_id")
            or not approval.get("provisioner_id")
            or not isinstance(granted, list)
            or granted != ["local.records.read"]
            or approval.get("conflict_check") != "NO_CONFLICT_IN_DECLARED_CATALOG"
        ):
            raise CompanyStoreError(
                "Distinct approval and explicit least-privilege rights required"
            )
        before = sorted(self.rights)
        self.rights = set(granted)
        for channel in CHANNELS:
            self.handles[channel] = True
        return {
            "before": before,
            "after": sorted(self.rights),
            "added": sorted(self.rights - set(before)),
            "removed": [],
        }

    def revoke(self, channels):
        if not isinstance(channels, (tuple, list)) or any(c not in CHANNELS for c in channels):
            raise CompanyStoreError("Only declared local channels may be revoked")
        before = deepcopy(self.handles)
        for channel in channels:
            self.handles[channel] = False
        if not self.handles["application_account"]:
            self.rights.clear()
        return {
            "before": before,
            "after": deepcopy(self.handles),
            "revoked_channels": list(channels),
        }

    def probe(self):
        # This local app caches sessions independently; directory disable is not session revocation.
        return {channel: "ALLOW" if active else "DENY" for channel, active in self.handles.items()}


def generate_pair(destination, *, repository, source_root, recipe: LifecycleRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or any(p.is_symlink() for p in (destination, *destination.parents))
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or destination.resolve().is_relative_to(Path(source_root).resolve())
    ):
        raise CompanyStoreError("New private lifecycle output outside original source required")
    for value in (
        recipe.company_id,
        recipe.source_store_id,
        recipe.exercise_subject_id,
        recipe.sponsor_person_id,
    ):
        _id(value)
    if (
        not isinstance(recipe.branch_ids, tuple)
        or len(recipe.branch_ids) != 2
        or len(set(recipe.branch_ids)) != 2
    ):
        raise CompanyStoreError("Two distinct explicit branches required")
    for branch in recipe.branch_ids:
        _id(branch)
    if (
        not recipe.exercise_subject_id.startswith("EXERCISE-")
        or not isinstance(recipe.local_requirement_basis, str)
        or not 1 <= len(recipe.local_requirement_basis.strip()) <= 2000
    ):
        raise CompanyStoreError("Explicit fictional worker and bounded local requirements required")
    times = [
        datetime.fromisoformat(_time(getattr(recipe, k)))
        for k in ("request_at", "start_at", "expires_at", "reconcile_at", "correction_at")
    ]
    request_at, start, expiry, checkpoint, correction = times
    if not (
        request_at + timedelta(hours=1)
        <= start
        < expiry
        < checkpoint
        < correction
        <= expiry + timedelta(days=7)
        and correction - request_at <= timedelta(days=93)
    ):
        raise CompanyStoreError("Ordered bounded lifecycle dates required")
    originals, pin = read_inputs(source_root, recipe.source_refs)
    if pin != recipe.source_versions_sha256:
        raise CompanyStoreError("Selected original metadata changed")
    if len({(r["company"], r["branch"]) for r in originals}) != 1:
        raise CompanyStoreError("One explicit original company/branch required")
    bodies = {}
    for row in originals:
        try:
            body = json.loads(row["content"])
        except (ValueError, UnicodeError) as error:
            raise CompanyStoreError("Original identity JSON required") from error
        if (
            row["company"] != recipe.company_id
            or row["event_at"] is None
            or datetime.fromisoformat(_time(row["event_at"])) > request_at
            or datetime.fromisoformat(_time(row["available_at"])) > request_at
            or row["origin"] != "AUTHORED_TRAINING_SOURCE"
            or not isinstance(body, dict)
            or body.get("origin") != "FICTIONAL_OPERATIONAL_SCENARIO_NOT_CANON_PERSONNEL_CHANGE"
            or body.get("person_id") != recipe.sponsor_person_id
            or row["system"] not in {"hr", "directory", "application"}
            or row["system"] in bodies
        ):
            raise CompanyStoreError("Available exact sponsor reference records required")
        bodies[row["system"]] = body
    if (
        not {"hr", "directory"} <= set(bodies)
        or bodies["directory"].get("account_status") != "ENABLED"
    ):
        raise CompanyStoreError("Active local sponsor directory and personnel correlation required")
    org = snapshot(repository, as_of=request_at.date().isoformat())
    people = {p["person_id"]: p for p in org["canonical_people"] + org["proposed_people"]}
    if recipe.sponsor_person_id not in people or recipe.exercise_subject_id in people:
        raise CompanyStoreError("Known sponsor and separate fictional worker required")
    assignments = {
        a["control_id"]: a for a in org["control_assignments"] if a["control_id"] in CONTROLS
    }
    owner = assignments["SH-IAM-001"]["primary_person_id"]
    reviewer = assignments["SH-IAM-002"]["operating_reviewer_person_id"]
    custodian = assignments["SH-IAM-004"]["custodian_person_id"]
    if len({owner, reviewer, custodian, recipe.sponsor_person_id}) != 4:
        raise CompanyStoreError(
            "Distinct scoped local custody, review, operator and sponsor required"
        )
    pins = dict(org["source_sha256"])
    for name in [
        VENDOR_SOURCE,
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_lifecycle_activity.py",
    ]:
        pins[name] = sha((repository / name).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    source_refs = [
        {k: row[k] for k in FIELDS} | {"source_store_id": recipe.source_store_id}
        for row in originals
    ]
    common = {
        "classification": QUALIFICATION,
        "subject_id": recipe.exercise_subject_id,
        "sponsor_person_id": recipe.sponsor_person_id,
        "source_records": source_refs,
        "source_versions_sha256": pin,
        "source_store_id": recipe.source_store_id,
        "boundary_id": "corporate",
        "employment_status": "FICTIONAL_WORKER_NOT_CANON_EMPLOYMENT",
        "policy_status": "EXPLICIT_LOCAL_RULE_NOT_ACCEPTED_CORPORATE_POLICY",
        "custody_status": "PROPOSED_SCOPED_CONTACTS_FOR_LOCAL_EXERCISE",
        "vendor_direction": {
            "hr": "SAP SuccessFactors",
            "identity": "Okta",
            "governance": "IBM Security Verify",
        },
        "deployment_status": "LOCAL_DATA_ONLY_NOT_VENDOR_EXPORT_OR_DEPLOYMENT",
        "limits": [
            "One fictional worker and six declared channels only.",
            "Proofing checks local request correlation, not real identity documents.",
            "Sponsor source correlation does not establish hiring authority.",
            "No IAM005 or IAM006 procedure is exercised.",
        ],
    }
    request = {
        "request_id": "LOCAL-WORKER-REQUEST",
        "subject_id": recipe.exercise_subject_id,
        "sponsor_person_id": recipe.sponsor_person_id,
        "approved": True,
        "approved_by": custodian,
        "proofing_check": "LOCAL_CORRELATION_ONLY",
        "start_at": _time(recipe.start_at),
        "expires_at": _time(recipe.expires_at),
        "request_kind": "FICTIONAL_FIXED_TERM_TEST_WORKER",
    }
    approval = {
        "subject_id": recipe.exercise_subject_id,
        "approved": True,
        "business_need": "Read synthetic local exercise records during declared term",
        "rights": ["local.records.read"],
        "reviewer_id": reviewer,
        "provisioner_id": owner,
        "conflict_check": "NO_CONFLICT_IN_DECLARED_CATALOG",
        "request_id": request["request_id"],
        "boundary_id": "corporate",
        "start_at": _time(recipe.start_at),
        "expires_at": _time(recipe.expires_at),
    }
    recipe_outputs = []
    with tempfile.TemporaryDirectory(prefix=".lifecycle-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        upstream = stage / "upstream"
        upstream.mkdir(mode=0o700)
        for i, row in enumerate(originals):
            file = upstream / f"{i:02d}.json"
            file.write_bytes(row["content"])
            file.chmod(0o600)
        for branch_index, branch in enumerate(recipe.branch_ids):
            for system, person in [
                ("worker_requests", custodian),
                ("access_approvals", reviewer),
                ("identity_events", owner),
                ("revocation_events", owner),
                ("access_reconciliation", reviewer),
            ]:
                store.register_system(recipe.company_id, branch, system, person)
            sequence = []

            def add(system, record, at, payload, controls, *, sequence=sequence, branch=branch):
                body = {
                    **common,
                    **payload,
                    "record_id": record,
                    "recorded_at": _time(at.isoformat()),
                    "control_ids": controls,
                    "previous_events": list(sequence),
                }
                result = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=sha(encoded([recipe_pin, branch, system, record])),
                    event_at=body["recorded_at"],
                    available_at=body["recorded_at"],
                    content=encoded(body),
                    provenance={
                        "name": record + ".json",
                        "source_reference": record,
                        "control_ids": controls,
                        "classification": QUALIFICATION,
                        "operational_fact_status": "COMPUTED_LOCAL_REFERENCE_ONLY",
                        "source_sha256": pins,
                        "recipe_sha256": recipe_pin,
                        "upstream_versions_sha256": pin,
                        "source_store_id": recipe.source_store_id,
                    },
                )
                sequence.append({k: result[k] for k in ("system", "record", "version", "sha256")})
                recipe_outputs.append(result)

            add("worker_requests", "REQUEST", request_at, request, ["SH-IAM-001"])
            add(
                "access_approvals",
                "LOCAL-CATALOG",
                request_at,
                {
                    "local_requirement_basis": recipe.local_requirement_basis,
                    "role_rights": {"local.reader": ["local.records.read"]},
                    "conflicting_rights": [["local.records.read", "local.records.admin"]],
                    "channels": list(CHANNELS),
                    "revocation_rule": "All declared channels DENY at expiry",
                    "session_semantics": (
                        "Application sessions remain valid until explicitly revoked"
                    ),
                },
                ["SH-IAM-002", "SH-IAM-004"],
            )
            add(
                "access_approvals",
                "APPROVAL",
                request_at + timedelta(minutes=1),
                approval,
                ["SH-IAM-002"],
            )
            identity = LocalIdentity()
            identity.create(request)
            add(
                "identity_events",
                "CREATE",
                start,
                {
                    "request_id": request["request_id"],
                    "created_identity": identity.subject,
                    "handles": deepcopy(identity.handles),
                },
                ["SH-IAM-001"],
            )
            diff = identity.provision(approval)
            add(
                "identity_events",
                "PROVISION",
                start,
                {
                    "entitlement_diff": diff,
                    "approval_id": "APPROVAL",
                    "handles": deepcopy(identity.handles),
                },
                ["SH-IAM-002"],
            )
            add(
                "identity_events",
                "INITIAL-PROBES",
                start,
                {"probes": identity.probe()},
                ["SH-IAM-002"],
            )
            add(
                "worker_requests",
                "CONTRACT-EXPIRED",
                expiry,
                {
                    "request_id": request["request_id"],
                    "authority": "EXPLICIT_FICTIONAL_CONTRACT_EXPIRY_NOT_EMPLOYEE_TERMINATION",
                },
                ["SH-IAM-004"],
            )
            channels = [
                c for c in CHANNELS if not (branch_index == 1 and c == "application_session")
            ]
            revoked = identity.revoke(channels)
            add("revocation_events", "EXPIRY-REVOCATION", expiry, revoked, ["SH-IAM-004"])
            observed = identity.probe()
            add(
                "access_reconciliation",
                "CHECKPOINT",
                checkpoint,
                {
                    "probes": observed,
                    "active_channels": [c for c, v in observed.items() if v == "ALLOW"],
                    "expected_channels": list(CHANNELS),
                    "expiry_event_id": "CONTRACT-EXPIRED",
                },
                ["SH-IAM-004"],
            )
            pending = [c for c, v in observed.items() if v == "ALLOW"]
            add(
                "revocation_events",
                "FOLLOWUP",
                checkpoint,
                {
                    "requested_revocations": pending,
                    "basis_record": "CHECKPOINT",
                    "assigned_to": owner,
                },
                ["SH-IAM-004"],
            )
            changed = identity.revoke(pending)
            add("revocation_events", "FOLLOWUP-ACTION", correction, changed, ["SH-IAM-004"])
            add(
                "access_reconciliation",
                "FINAL-PROBES",
                correction,
                {
                    "probes": identity.probe(),
                    "active_channels": [c for c, v in identity.probe().items() if v == "ALLOW"],
                    "original_checkpoint_preserved": True,
                },
                ["SH-IAM-004"],
            )
        if read_inputs(source_root, recipe.source_refs)[1] != pin:
            raise CompanyStoreError("Declared source changed during lifecycle computation")
        result = {
            "status": "LOCAL_LIFECYCLE_CREATED",
            "qualification": QUALIFICATION,
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_sha256": pins,
            "source_versions_sha256": pin,
            "source_records": source_refs,
            "source_metadata": [
                {k: v for k, v in row.items() if k != "content"} for row in originals
            ],
            "upstream_files": {
                f"upstream/{i:02d}.json": row["sha256"] for i, row in enumerate(originals)
            },
            "records": recipe_outputs,
            "assignments": assignments,
            "audit_created": False,
            "grants_created": False,
        }
        file = stage / "SOURCE_RECEIPT.json"
        file.write_bytes(encoded(result))
        file.chmod(0o600)
        publish(stage, destination)
    return result
