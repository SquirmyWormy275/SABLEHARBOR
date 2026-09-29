"""Private, data-only privileged sessions; no host accounts or corporate approvals."""

import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .company_backup_runtime import checked_bytes, database, exact_pin, native, private, require
from .company_lifecycle_activity import LifecycleSourceRef, read_inputs
from .company_operating_period import SYSTEM as PERIOD_SYSTEM
from .company_operating_period import _plan
from .company_store import CompanyStore, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_PROTECTED_READ_SESSION_NOT_PRODUCTION_PRIVILEGE_OR_MANAGER_APPROVAL"
SYSTEMS = ("privileged_definition", "privileged_object", "privileged_operation")
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
PAYLOADS = {
    "ISSUE_LEASE": {"lease_id", "principal_id", "object_id", "right", "purpose", "expires_at"},
    "OPEN_SESSION": {"session_id", "lease_id", "principal_id"},
    "READ_OBJECT": {"session_id", "principal_id", "object_id"},
    "REVOKE_LEASE": {"lease_id", "reason"},
    "EXPIRE": set(),
    "RECONCILE": {"occurrence_id"},
}
MAX_COMMANDS = 256
MAX_NATIVE_BYTES = 32 * 1024 * 1024
MAX_ROW_BYTES = 512 * 1024


def _code():
    names = (
        "company_privileged_runtime.py",
        "company_backup_runtime.py",
        "company_lifecycle_activity.py",
        "company_operating_period.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
    )
    paths = {name: Path(__file__).with_name(name) for name in names}
    require(all(path.is_file() for path in paths.values()), "Maintained implementation missing")
    return {name: sha(path.read_bytes()) for name, path in paths.items()}


def _text(value):
    require(isinstance(value, str) and 1 <= len(value.strip()) <= 2000, "Bounded text required")


def _sources(root, refs, at, *, current=True):
    private(root, True)
    require(
        isinstance(refs, dict) and set(refs) == {"hr", "directory", "application"},
        "Exact three eligibility sources required",
    )
    for system, ref in refs.items():
        exact_pin(ref)
        require(ref["system"] == system, "Eligibility source system differs")
    require(
        len({(r["company"], r["branch"]) for r in refs.values()}) == 1,
        "Eligibility sources must share native company and branch",
    )
    rows, digest = read_inputs(root, tuple(LifecycleSourceRef(**refs[k]) for k in sorted(refs)))
    indexed = {r["system"]: r for r in rows}
    bodies = {k: decode(r["content"]) for k, r in indexed.items()}
    require(
        all(isinstance(b, dict) for b in bodies.values()), "Typed eligibility originals required"
    )
    require(
        all(
            r["origin"] == "AUTHORED_TRAINING_SOURCE"
            and r["event_at"] is not None
            and r["event_at"] <= r["available_at"] <= at
            for r in rows
        ),
        "Eligibility sources must be available before local use",
    )
    require(
        all(
            b.get("origin") == "FICTIONAL_OPERATIONAL_SCENARIO_NOT_CANON_PERSONNEL_CHANGE"
            for b in bodies.values()
        ),
        "Supported fictional identity source contract required",
    )
    subject = bodies["hr"].get("person_id")
    _id(subject)
    require(
        all(
            b.get("person_id") == subject and b.get("cause_id") == bodies["hr"].get("cause_id")
            for b in bodies.values()
        ),
        "Correlated subject and causal identity required",
    )
    auth = bodies["hr"].get("transfer_authorization")
    require(isinstance(auth, dict), "Existing explicit source authorization required")
    for k in ("approval_id", "approved_by", "requested_by", "add_right"):
        _id(auth.get(k))
    require(
        bodies["hr"].get("employment_status") == "ACTIVE"
        and _time(auth.get("approved_at"))
        <= _time(auth.get("effective_at"))
        <= indexed["hr"]["event_at"],
        "Source eligibility timing or state differs",
    )
    for system, field in (("directory", "groups"), ("application", "rights")):
        b = bodies[system]
        require(
            b.get("account_status") == "ENABLED"
            and b.get("authorization_id") == auth["approval_id"]
            and isinstance(b.get(field), list)
            and all(isinstance(x, str) for x in b[field])
            and auth["add_right"] in b[field]
            and b.get("performed_by") != auth["approved_by"]
            and indexed["hr"]["available_at"] <= indexed[system]["event_at"],
            "Actual right, approval correlation and distinct source operator required",
        )
    # Do not admit a superseded version of the selected record as current eligibility.
    with database(root) as db:
        owners = {
            r["system"]: r["owner"]
            for r in db.execute(
                "SELECT system,owner FROM systems WHERE company=? AND branch=?",
                (refs["hr"]["company"], refs["hr"]["branch"]),
            )
        }
        require(
            owners.get("hr") == auth["requested_by"]
            and owners.get("access_review") == auth["approved_by"],
            "Native source approval ownership differs",
        )
        for name in ("directory", "application"):
            _id(bodies[name].get("performed_by"))
            require(
                owners.get(name) == bodies[name]["performed_by"],
                "Native provisioning owner differs",
            )
        for ref in refs.values():
            latest = db.execute(
                "SELECT MAX(version) FROM versions WHERE company=? AND branch=? "
                "AND system=? AND record=? AND available_at<=?",
                (*[ref[k] for k in FIELDS[:4]], at),
            ).fetchone()[0]
            require(
                not current or latest == ref["version"],
                "Selected eligibility record was superseded",
            )
    return digest, subject, auth["add_right"]


def _declaration(root, ref, at):
    require(ref["system"] == PERIOD_SYSTEM, "Operating-period declaration required")
    with database(root) as db:
        row = native(db, ref, at)
    body = decode(row["content"])
    require(
        isinstance(body, dict) and body.get("kind") == "PERIOD_DECLARATION",
        "Native period declaration required",
    )
    plan = _plan(body["plan"])
    require(
        row["origin"] == "AUTHORED_TRAINING_SOURCE"
        and row["event_at"] == plan["declared_at"] <= row["available_at"] <= at,
        "Declaration origin or chronology differs",
    )
    require(
        plan["control_ids"] == ["SH-IAM-005"]
        and (ref["company"], ref["branch"], ref["record"], ref["version"])
        == (plan["company_id"], plan["branch_id"], plan["period_id"], 1),
        "Exact local IAM005 declaration identity required",
    )
    return plan


def _provenance(cfg):
    return {
        "classification": QUALIFICATION,
        "control_ids": ["SH-IAM-005"],
        "runtime_sha256": sha(encoded(cfg)),
        "declaration": cfg["declaration_pin"],
        "eligibility_pins": cfg["source_pins"],
        "source_metadata_sha256": cfg["source_metadata_sha256"],
        "authority": "EXPLICIT_LOCAL_OPERATOR_EXERCISE_NOT_MANAGER_APPROVAL",
    }


def _metadata(cfg, system, record, raw, at, command):
    key = [cfg["plan"]["company_id"], cfg["plan"]["branch_id"], system, _id(record)]
    provenance = _provenance(cfg)
    digest = sha(raw)
    return {
        **dict(zip(FIELDS[:4], key, strict=True)),
        "version": 1,
        "event_at": at,
        "available_at": at,
        "origin": "AUTHORED_TRAINING_SOURCE",
        "provenance": _json(provenance),
        "sha256": digest,
        "command_id": command,
        "input_digest": sha(
            _json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()
        ),
    }


def _verify_native(row, cfg, system, record, raw, at, command):
    expected = _metadata(cfg, system, record, raw, at, command)
    require(
        row is not None
        and encoded({k: row[k] for k in expected}) == encoded(expected)
        and row["content"] == raw,
        "Native original metadata or bytes differ",
    )


def _insert(db, cfg, system, record, raw, at, command):
    require(len(raw) <= MAX_ROW_BYTES, "Native record byte bound exceeded")
    require(
        db.execute("SELECT COALESCE(SUM(length(content)),0) FROM versions").fetchone()[0] + len(raw)
        <= MAX_NATIVE_BYTES,
        "Native aggregate byte quota exceeded",
    )
    metadata = _metadata(cfg, system, record, raw, at, command)
    key = [metadata[k] for k in FIELDS[:4]]
    provenance = _provenance(cfg)
    digest, fingerprint = metadata["sha256"], metadata["input_digest"]
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            *key,
            1,
            at,
            at,
            _now(),
            "AUTHORED_TRAINING_SOURCE",
            _json(provenance),
            raw,
            digest,
            command,
            fingerprint,
        ),
    )
    return dict(zip(FIELDS, (*key, 1, digest), strict=True))


def _opening():
    return {"leases": {}, "sessions": {}, "reconciled_occurrences": []}


def initialize(
    destination,
    *,
    repository,
    source_root,
    source_pins,
    expected_source_metadata_sha256,
    declaration_root,
    declaration_pin,
    object_id,
    object_bytes,
    max_lease_seconds,
    local_rule_basis,
    as_of,
):
    """Admit existing eligibility and independent schedule, never manufacture approval."""
    destination = Path(destination)
    source_root, declaration_root = (
        private(Path(source_root), True),
        private(Path(declaration_root), True),
    )
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New canonical private runtime required",
    )
    for original in (source_root, declaration_root):
        require(
            not destination.is_relative_to(original) and not original.is_relative_to(destination),
            "Runtime and originals must be separate",
        )
    at = _time(as_of)
    source_pins, declaration_pin = decode(encoded(source_pins)), decode(encoded(declaration_pin))
    exact_pin(declaration_pin)
    source_digest, subject, right = _sources(source_root, source_pins, at)
    require(
        source_digest == expected_source_metadata_sha256, "Exact eligibility metadata pin required"
    )
    plan = _declaration(declaration_root, declaration_pin, at)
    require(plan["declared_at"] <= at <= plan["period_start"], "Initialize before declared period")
    _id(object_id)
    require(
        subject != object_id and {subject, object_id} == {x["id"] for x in plan["inventory"]},
        "Exactly one distinct subject and local object must be declared",
    )
    require(
        isinstance(object_bytes, bytes) and 0 < len(object_bytes) <= 65536,
        "Bounded nonpersonal local fixture bytes required",
    )
    require(
        type(max_lease_seconds) is int and 1 <= max_lease_seconds <= 86400,
        "Explicit bounded local lease rule required",
    )
    _text(local_rule_basis)
    org = snapshot(repository, as_of=at[:10])
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == "SH-IAM-005")
    require(plan["owner_id"] == assignment["primary_person_id"], "Scoped local owner differs")
    pins = {
        **org["source_sha256"],
        "enterprise/audit_suite/company_privileged_runtime.py": sha(Path(__file__).read_bytes()),
    }
    cfg = {
        "format": "LOCAL_PRIVILEGED_RUNTIME_V1",
        "plan": plan,
        "initialized_at": at,
        "source_root": str(source_root),
        "source_location_sha256": sha(str(source_root).encode()),
        "source_pins": source_pins,
        "source_metadata_sha256": source_digest,
        "declaration_root": str(declaration_root),
        "declaration_pin": declaration_pin,
        "subject_id": subject,
        "eligible_right": right,
        "object_id": object_id,
        "object_sha256": sha(object_bytes),
        "max_lease_seconds": max_lease_seconds,
        "local_rule_basis": local_rule_basis,
        "operator_id": plan["owner_id"],
        "source_sha256": pins,
        "code_sha256": _code(),
        "qualification": QUALIFICATION,
        "eligibility_limit": "EXACT_SELECTED_SOURCE_RECORDS_NOT_ALL_ENTERPRISE_ACCOUNTS",
    }
    raw = encoded(cfg)
    with tempfile.TemporaryDirectory(prefix="privileged-stage-", dir=destination.parent) as tmp:
        stage = Path(tmp)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(plan["company_id"], plan["branch_id"], system, cfg["operator_id"])
        with (stage / "RUNTIME.json").open("xb") as stream:
            os.chmod(stage / "RUNTIME.json", 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        with database(stage, True) as db:
            db.executescript("""CREATE TABLE privileged_state(
                    revision INTEGER,last_event_at TEXT,state TEXT);
                CREATE TABLE privileged_commands(
                    command_id TEXT PRIMARY KEY,input_digest TEXT,receipt TEXT);
                CREATE TRIGGER privileged_no_update BEFORE UPDATE ON privileged_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;
                CREATE TRIGGER privileged_no_delete BEFORE DELETE ON privileged_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;""")
            db.execute("INSERT INTO privileged_state VALUES(?,?,?)", (0, at, _json(_opening())))
            _insert(db, cfg, "privileged_definition", plan["period_id"], raw, at, "definition")
            _insert(db, cfg, "privileged_object", object_id, object_bytes, at, "object")
        require(
            _sources(source_root, source_pins, at)[0] == source_digest
            and _declaration(declaration_root, declaration_pin, at) == plan,
            "Originals changed before publication",
        )
        require(
            all(sha((Path(repository) / k).read_bytes()) == v for k, v in pins.items())
            and cfg["code_sha256"] == _code(),
            "Pinned source/code changed before publication",
        )
        publish(stage, destination)
    return {
        "runtime_sha256": sha(raw),
        "native_versions": 2,
        "revision": 0,
        "qualification": QUALIFICATION,
        "grants_created": False,
    }


def _config(root, expected):
    raw = checked_bytes(Path(root) / "RUNTIME.json", 2 * 1024 * 1024)
    require(sha(raw) == expected, "Runtime definition pin differs")
    cfg = decode(raw)
    require(cfg.get("format") == "LOCAL_PRIVILEGED_RUNTIME_V1", "Runtime definition format differs")
    require(
        cfg.get("code_sha256") == _code()
        and cfg["source_sha256"].get("enterprise/audit_suite/company_privileged_runtime.py")
        == cfg["code_sha256"]["company_privileged_runtime.py"],
        "Retained implementation pin differs; explicit successor required",
    )
    return cfg


def _source_check(cfg, at, *, current=True):
    require(
        sha(cfg["source_root"].encode()) == cfg["source_location_sha256"], "Source routing differs"
    )
    require(
        _sources(Path(cfg["source_root"]), cfg["source_pins"], at, current=current)[0]
        == cfg["source_metadata_sha256"]
        and _declaration(Path(cfg["declaration_root"]), cfg["declaration_pin"], at) == cfg["plan"],
        "Current original eligibility/declaration differs",
    )


def _objects(db, cfg):
    plan = cfg["plan"]
    rows = db.execute(
        "SELECT * FROM versions WHERE system IN ('privileged_definition','privileged_object')"
    ).fetchall()
    require(len(rows) == 2, "Exact definition/object inventory required")
    by = {r["system"]: r for r in rows}
    for system, record, expected in (
        ("privileged_definition", plan["period_id"], sha(encoded(cfg))),
        ("privileged_object", cfg["object_id"], cfg["object_sha256"]),
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
            "definition" if system == "privileged_definition" else "object",
        )
    return bytes(by["privileged_object"]["content"])


def _apply(cfg, state, action, payload, actor, at, raw):
    require(
        isinstance(action, str)
        and action in PAYLOADS
        and isinstance(payload, dict)
        and set(payload) == PAYLOADS[action],
        "Exact supported operation payload required",
    )
    s = deepcopy(state)
    for key, value in payload.items():
        if key not in {"purpose", "reason", "expires_at"}:
            _id(value)
    if action not in {"OPEN_SESSION", "READ_OBJECT"}:
        require(actor == cfg["operator_id"], "Explicit scoped local operator required")
    else:
        require(actor == payload["principal_id"], "Recorded actor must match session principal")
    if action not in {"EXPIRE", "RECONCILE"}:
        require(
            cfg["plan"]["period_start"] <= at < cfg["plan"]["period_end_exclusive"],
            "Operation outside declared local period",
        )
    observation = {"status": "RECORDED"}
    if action == "ISSUE_LEASE":
        _text(payload["purpose"])
        end = _time(payload["expires_at"])
        require(
            payload["lease_id"] not in s["leases"]
            and payload["principal_id"] == cfg["subject_id"]
            and payload["object_id"] == cfg["object_id"]
            and payload["right"] == cfg["eligible_right"],
            "New lease must match exact eligible principal/right/object",
        )
        require(
            at < end <= cfg["plan"]["period_end_exclusive"]
            and (datetime.fromisoformat(end) - datetime.fromisoformat(at)).total_seconds()
            <= cfg["max_lease_seconds"],
            "Explicit local duration exceeded",
        )
        s["leases"][payload["lease_id"]] = {
            **payload,
            "expires_at": end,
            "issued_at": at,
            "status": "ISSUED",
        }
    elif action in {"OPEN_SESSION", "READ_OBJECT"}:
        if action == "OPEN_SESSION":
            require(payload["session_id"] not in s["sessions"], "Session ID already used")
            lease = s["leases"].get(payload["lease_id"])
            session = None
        else:
            session = s["sessions"].get(payload["session_id"])
            lease = s["leases"].get(session["lease_id"]) if session else None
        permitted = bool(
            lease
            and lease["status"] == "ISSUED"
            and lease["issued_at"] <= at < lease["expires_at"]
            and lease["principal_id"] == payload["principal_id"]
            and (
                action == "OPEN_SESSION"
                or (
                    session["status"] == "OPEN"
                    and session["principal_id"] == payload["principal_id"]
                    and payload["object_id"] == lease["object_id"]
                )
            )
        )
        observation = {
            "status": "AUTHORIZED" if permitted else "DENIED",
            "denial_basis": None if permitted else "NO_MATCHING_EFFECTIVE_LEASE_AND_SESSION",
        }
        if permitted and action == "OPEN_SESSION":
            s["sessions"][payload["session_id"]] = {
                "lease_id": payload["lease_id"],
                "principal_id": payload["principal_id"],
                "opened_at": at,
                "status": "OPEN",
            }
        elif permitted:
            observation.update(
                read_sha256=sha(raw), read_bytes=len(raw), object_id=cfg["object_id"]
            )
    elif action == "REVOKE_LEASE":
        _text(payload["reason"])
        require(payload["lease_id"] in s["leases"], "Existing lease required")
        s["leases"][payload["lease_id"]]["status"] = "REVOKED"
        for session in s["sessions"].values():
            if session["lease_id"] == payload["lease_id"]:
                session.update(status="REVOKED", closed_at=at)
    elif action == "EXPIRE":
        expired = []
        for key, lease in s["leases"].items():
            if lease["status"] == "ISSUED" and at >= lease["expires_at"]:
                lease["status"] = "EXPIRED"
                expired.append(key)
        for session in s["sessions"].values():
            if session["lease_id"] in expired:
                session.update(status="EXPIRED", closed_at=at)
        observation["expired_leases"] = sorted(expired)
    else:
        slot = next(
            (x for x in cfg["plan"]["schedule"] if x["id"] == payload["occurrence_id"]), None
        )
        require(
            slot is not None and slot["window_start"] <= at,
            "Explicit declared reconciliation occurrence required",
        )
        require(
            payload["occurrence_id"] not in s["reconciled_occurrences"],
            "Occurrence already recorded",
        )
        observation = _reconciliation(cfg, s, at)
        observation["recorded_after_due"] = at > slot["due_at"]
        s["reconciled_occurrences"].append(payload["occurrence_id"])
    return s, observation


def _reconciliation(cfg, state, at):
    due = sorted(x["id"] for x in cfg["plan"]["schedule"] if x["due_at"] <= at)
    return {
        "status": "LOCAL_RECONCILIATION",
        "declared_due_ids": due,
        "previously_unrecorded_due_ids": sorted(set(due) - set(state["reconciled_occurrences"])),
        "expired_unclosed_session_ids": sorted(
            k
            for k, s in state["sessions"].items()
            if s["status"] == "OPEN" and state["leases"][s["lease_id"]]["expires_at"] <= at
        ),
        "lease_count": len(state["leases"]),
        "session_count": len(state["sessions"]),
        "professional_review": "NOT_PERFORMED",
        "quarterly_enterprise_completeness": "NOT_ESTABLISHED",
    }


def _history(db, cfg):
    # SQL length checks precede every original, command or current-state materialization.
    for table, expression, count_limit, row_limit, total_limit in (
        (
            "versions",
            "length(CAST(content AS BLOB))",
            MAX_COMMANDS + 2,
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
            MAX_COMMANDS + 2,
            16 * 1024,
            (MAX_COMMANDS + 2) * 16 * 1024,
        ),
        (
            "privileged_commands",
            "length(CAST(receipt AS BLOB))",
            MAX_COMMANDS,
            MAX_ROW_BYTES,
            MAX_NATIVE_BYTES,
        ),
        ("privileged_state", "length(CAST(state AS BLOB))", 1, MAX_ROW_BYTES, MAX_ROW_BYTES),
        (
            "privileged_commands",
            "COALESCE(length(CAST(command_id AS BLOB)),0) "
            "+ COALESCE(length(CAST(input_digest AS BLOB)),0)",
            MAX_COMMANDS,
            4096,
            MAX_COMMANDS * 4096,
        ),
        ("privileged_state", "length(CAST(last_event_at AS BLOB))", 1, 128, 128),
    ):
        sizes = db.execute(
            f"SELECT COUNT(*),COALESCE(MAX({expression}),0),"
            f"COALESCE(SUM({expression}),0) FROM {table}"
        ).fetchone()
        require(
            sizes[0] <= count_limit and sizes[1] <= row_limit and sizes[2] <= total_limit,
            "Bounded native history, command receipts and current state required",
        )
    raw = _objects(db, cfg)
    rows = db.execute(
        "SELECT command_id,input_digest,receipt FROM privileged_commands ORDER BY rowid"
    ).fetchall()
    require(len(rows) <= MAX_COMMANDS, "Command history bound exceeded")
    state, at = _opening(), cfg["initialized_at"]
    receipts = {}
    for revision, row in enumerate(rows, 1):
        receipt = decode(row["receipt"])
        require(
            isinstance(receipt, dict)
            and set(receipt)
            == {
                "command_id",
                "revision",
                "event_at",
                "runtime_sha256",
                "operation_pin",
                "observation",
                "qualification",
            }
            and type(receipt["revision"]) is int
            and receipt["revision"] == revision
            and receipt["command_id"] == row["command_id"]
            and receipt["runtime_sha256"] == sha(encoded(cfg))
            and receipt["qualification"] == QUALIFICATION,
            "Command receipt envelope differs",
        )
        original = native(db, receipt["operation_pin"])
        require(
            original["system"] == "privileged_operation"
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
            "privileged_operation",
            row["command_id"],
            bytes(original["content"]),
            receipt["event_at"],
            row["command_id"],
        )
        body = decode(original["content"])
        require(
            isinstance(body, dict)
            and set(body) == {"command", "before_sha256", "after", "observation", "qualification"},
            "Exact native operation body required",
        )
        require(body["qualification"] == QUALIFICATION, "Native qualification differs")
        command = body["command"]
        require(
            isinstance(command, dict)
            and set(command)
            == {"expected_revision", "command_id", "action", "payload", "actor_id", "event_at"}
            and type(command["expected_revision"]) is int
            and command["expected_revision"] == revision - 1
            and command["command_id"] == row["command_id"]
            and command["event_at"] == receipt["event_at"]
            and command["event_at"] >= at
            and sha(encoded(command)) == row["input_digest"]
            and body["before_sha256"] == sha(encoded(state)),
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
        at = command["event_at"]
        receipts[row["command_id"]] = (row["input_digest"], receipt)
    current = db.execute("SELECT * FROM privileged_state").fetchall()
    require(
        len(current) == 1
        and current[0]["revision"] == len(rows)
        and current[0]["last_event_at"] == at
        and encoded(decode(current[0]["state"])) == encoded(state),
        "Current state differs from replayed native operations",
    )
    require(
        db.execute("SELECT count(*) FROM versions").fetchone()[0] == len(rows) + 2,
        "Native/command inventory differs",
    )
    return state, at, receipts, raw


def execute(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
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
        type(expected_revision) is int and expected_revision >= 0,
        "Exact expected revision required",
    )
    at = _time(event_at)
    command = {
        "expected_revision": expected_revision,
        "command_id": command_id,
        "action": action,
        "payload": decode(encoded(payload)),
        "actor_id": actor_id,
        "event_at": at,
    }
    digest = sha(encoded(command))
    code_pin = sha(Path(__file__).read_bytes())
    require(isinstance(action, str) and action in PAYLOADS, "Supported operation required")
    current_eligibility = action in {"ISSUE_LEASE", "OPEN_SESSION", "READ_OBJECT"}
    _source_check(cfg, at, current=current_eligibility)
    with database(root, True) as db:
        state, previous_at, receipts, raw = _history(db, cfg)
        if command_id in receipts:
            require(receipts[command_id][0] == digest, "Changed command replay forbidden")
            result = receipts[command_id][1]
        else:
            require(
                len(receipts) == expected_revision
                and at >= previous_at
                and len(receipts) < MAX_COMMANDS,
                "Stale revision, backwards time or operation quota",
            )
            after, observation = _apply(cfg, state, action, command["payload"], actor_id, at, raw)
            original = {
                "command": command,
                "before_sha256": sha(encoded(state)),
                "after": after,
                "observation": observation,
                "qualification": QUALIFICATION,
            }
            ref = _insert(
                db, cfg, "privileged_operation", command_id, encoded(original), at, command_id
            )
            result = {
                "command_id": command_id,
                "revision": expected_revision + 1,
                "event_at": at,
                "runtime_sha256": expected_runtime_sha256,
                "operation_pin": ref,
                "observation": observation,
                "qualification": QUALIFICATION,
            }
            require(
                len(_json(result).encode()) <= MAX_ROW_BYTES
                and len(_json(after).encode()) <= MAX_ROW_BYTES
                and db.execute(
                    "SELECT COALESCE(SUM(length(CAST(receipt AS BLOB))),0) FROM privileged_commands"
                ).fetchone()[0]
                + len(_json(result).encode())
                <= MAX_NATIVE_BYTES,
                "Command receipt or state byte quota exceeded",
            )
            db.execute(
                "INSERT INTO privileged_commands VALUES(?,?,?)", (command_id, digest, _json(result))
            )
            db.execute(
                "UPDATE privileged_state SET revision=?,last_event_at=?,state=?",
                (expected_revision + 1, at, _json(after)),
            )
        require(
            _config(root, expected_runtime_sha256) == cfg
            and sha(Path(__file__).read_bytes()) == code_pin,
            "Runtime definition or code changed during operation",
        )
        _source_check(cfg, at, current=current_eligibility)
    return result


def inspect(runtime, *, expected_runtime_sha256, as_of):
    root = private(Path(runtime), True)
    cfg, at = _config(root, expected_runtime_sha256), _time(as_of)
    with database(root) as db:
        state, latest_at, receipts, _ = _history(db, cfg)
        require(
            at >= latest_at,
            "Historical state projection not supported; explicit current cutoff required",
        )
        result = {
            "revision": len(receipts),
            "as_of": at,
            "state": state,
            "reconciliation": _reconciliation(cfg, state, at),
            "qualification": QUALIFICATION,
        }
    _source_check(cfg, at, current=False)
    require(_config(root, expected_runtime_sha256) == cfg, "Definition changed during inspection")
    return result
