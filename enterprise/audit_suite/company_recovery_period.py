"""Durable explicit local recovery-period commands; no audit or arbitrary dispatch."""

import fcntl
import os
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

from . import company_backup_admission as admission
from . import company_backup_monitor as monitor
from . import company_backup_runtime as backup
from . import company_configuration_export as export
from . import company_configuration_runtime as configuration
from .company_store import _id, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .private_publication import publish

FORMAT = "LOCAL_RECOVERY_PERIOD_PLAN_V1"
MAX_TOTAL = 16 * 1024 * 1024
COMMON = {"expected_revision", "command_id"}
PARAMS = {
    "APPLY": COMMON
    | {"expected_current_sha256", "expected_target_sha256", "operator_id", "event_at", "rationale"},
    "EXPORT": COMMON | {"expected_current_sha256", "operator_id", "event_at", "rationale"},
    "ADMIT": COMMON
    | {"dataset_id", "operator_id", "event_at", "source_pin", "previous_pin", "metadata_capture"},
    "LEASE": COMMON
    | {"operation", "enabled", "valid_from", "expires_at", "event_at", "previous_pin"},
    "BACKUP": COMMON
    | {
        "occurrence_id",
        "source_pin",
        "lease_pin",
        "attempted_at",
        "rationale",
        "prior_attempt_pin",
    },
    "RESTORE": COMMON
    | {
        "occurrence_id",
        "backup_pin",
        "comparison_source_pin",
        "lease_pin",
        "attempted_at",
        "rationale",
        "prior_attempt_pin",
    },
    "MONITOR": COMMON | {"as_of", "recorded_at", "operator_id", "rationale", "jobs_capture"},
}
OUTPUTS = {
    "APPLY": {"native_pin"},
    "EXPORT": {"native_pin"},
    "ADMIT": {"source_pin"},
    "LEASE": {"lease_pin"},
    "BACKUP": {"job_pin", "object_pin"},
    "RESTORE": {"job_pin", "object_pin"},
    "MONITOR": {"scan_pin"},
}
PIN_PARAMS = {
    "source_pin",
    "previous_pin",
    "lease_pin",
    "backup_pin",
    "comparison_source_pin",
    "prior_attempt_pin",
}


def _fields(value, names):
    backup.require(
        isinstance(value, dict) and set(value) == set(names),
        "Exact recovery-period fields required",
    )


def _code():
    modules = [
        Path(__file__),
        Path(admission.__file__),
        Path(backup.__file__),
        Path(configuration.__file__),
        Path(export.__file__),
        Path(monitor.__file__),
    ]
    return {p.name: sha(p.read_bytes()) for p in modules}


def _which(kind):
    return "configuration" if kind in {"APPLY", "EXPORT"} else "backup"


def _plan(value):
    plan = decode(encoded(value))
    backup.require(len(encoded(plan)) <= 512 * 1024, "Bounded period plan required")
    _fields(plan, {"format", "id", "period_id", "bindings", "omissions", "steps"})
    backup.require(plan["format"] == FORMAT, "Recovery-period format differs")
    _id(plan["id"])
    _id(plan["period_id"])
    _fields(plan["bindings"], {"configuration", "backup"})
    for role, binding in plan["bindings"].items():
        fields = {"root", "runtime_sha256", "revision"}
        if role == "configuration":
            fields |= {"current_sha256", "definition_pin"}
        _fields(binding, fields)
        backup.private(Path(binding["root"]), True)
        admission._hash(binding["runtime_sha256"])
        backup.require(
            type(binding["revision"]) is int and binding["revision"] >= 0,
            "Exact opening revision required",
        )
        if role == "configuration":
            admission._hash(binding["current_sha256"])
            backup.exact_pin(binding["definition_pin"])
            backup.require(
                binding["definition_pin"]["sha256"] == binding["runtime_sha256"],
                "Definition pin differs",
            )
    roots = [Path(v["root"]) for v in plan["bindings"].values()]
    backup.require(
        not roots[0].is_relative_to(roots[1]) and not roots[1].is_relative_to(roots[0]),
        "Disjoint runtime roots required",
    )
    backup.require(
        isinstance(plan["steps"], list) and 1 <= len(plan["steps"]) <= 64,
        "One to 64 explicit steps required",
    )
    seen, commands = {}, set()
    revisions = {k: v["revision"] for k, v in plan["bindings"].items()}
    for step in plan["steps"]:
        _fields(step, {"id", "kind", "parameters", "refs", "expected_pins"})
        _id(step["id"])
        backup.require(
            step["id"] not in seen and isinstance(step["kind"], str) and step["kind"] in PARAMS,
            "Unique supported step required",
        )
        kind = step["kind"]
        parameters = step["parameters"]
        backup.require(
            isinstance(parameters, dict) and isinstance(step["refs"], dict),
            "Typed parameters and refs required",
        )
        backup.require(
            not set(parameters) & set(step["refs"])
            and set(parameters) | set(step["refs"]) == PARAMS[kind],
            "Exact operation parameter fields required",
        )
        role = _which(kind)
        backup.require(
            type(parameters.get("expected_revision")) is int
            and parameters["expected_revision"] == revisions[role],
            "Explicit consecutive runtime revisions required",
        )
        revisions[role] += 1
        command = _id(parameters.get("command_id"))
        backup.require((role, command) not in commands, "Duplicate runtime command ID")
        commands.add((role, command))
        for parameter, ref in step["refs"].items():
            backup.require(parameter in PIN_PARAMS, "Only typed native pin references supported")
            backup.require(isinstance(ref, dict), "Typed native reference required")
            capture = "sha256_policy" in ref
            _fields(
                ref,
                {"step_id", "field", "expected_identity", "sha256_policy"}
                if capture
                else {"step_id", "field", "expected_pin"},
            )
            backup.require(
                isinstance(ref["step_id"], str)
                and isinstance(ref["field"], str)
                and ref["step_id"] in seen
                and ref["field"] in OUTPUTS[seen[ref["step_id"]]],
                "Exact prior step native output required",
            )
            if capture:
                backup.require(
                    ref["field"] == "job_pin"
                    and ref["sha256_policy"] == "CAPTURE_FROM_VERIFIED_PRODUCER_RESULT",
                    "Only measured job output hash capture supported",
                )
                _fields(ref["expected_identity"], backup.FIELDS[:-1])
                backup.exact_pin({**ref["expected_identity"], "sha256": "0" * 64})
            else:
                backup.exact_pin(ref["expected_pin"])
        backup.require(
            isinstance(step["expected_pins"], dict) and set(step["expected_pins"]) <= OUTPUTS[kind],
            "Supported expected native outputs required",
        )
        for pin in step["expected_pins"].values():
            backup.exact_pin(pin)
        if kind in {"EXPORT", "ADMIT"}:
            backup.require(
                set(step["expected_pins"]) == OUTPUTS[kind],
                "Explicit producer/consumer output pin required",
            )
        if kind == "ADMIT":
            backup.require(
                parameters.get("metadata_capture") == "CAPTURE_EXACT_ONCE",
                "Explicit metadata capture policy required",
            )
        if kind == "MONITOR":
            backup.require(
                parameters.get("jobs_capture") == "CAPTURE_EXACT_ONCE",
                "Explicit job inventory capture policy required",
            )
        for key in ("event_at", "attempted_at", "recorded_at", "as_of", "valid_from", "expires_at"):
            if key in parameters:
                _time(parameters[key])
        for key in ("operator_id", "dataset_id", "occurrence_id"):
            if key in parameters:
                _id(parameters[key])
        for key in ("expected_current_sha256", "expected_target_sha256"):
            if key in parameters:
                admission._hash(parameters[key])
        if "rationale" in parameters:
            backup.require(
                isinstance(parameters["rationale"], str)
                and 0 < len(parameters["rationale"].strip()) <= 2000,
                "Bounded authored rationale required",
            )
        if kind == "LEASE":
            backup.require(
                type(parameters["enabled"]) is bool
                and parameters["operation"] in {"BACKUP_WRITE", "RESTORE_READ"}
                and _time(parameters["valid_from"]) < _time(parameters["expires_at"]),
                "Typed lease and positive window required",
            )
        for key in PIN_PARAMS & set(parameters):
            if parameters[key] is not None:
                backup.exact_pin(parameters[key])
        seen[step["id"]] = kind
    omissions = plan["omissions"]
    backup.require(
        isinstance(omissions, list) and len(omissions) <= 512, "Explicit omissions required"
    )
    omitted = []
    for omission in omissions:
        _fields(omission, {"occurrence_id", "reason"})
        omitted.append(_id(omission["occurrence_id"]))
        backup.require(
            isinstance(omission["reason"], str) and 0 < len(omission["reason"].strip()) <= 2000,
            "Authored omission reason required",
        )
    backup.require(len(set(omitted)) == len(omitted), "Duplicate omission")
    cfg = backup._config(
        Path(plan["bindings"]["backup"]["root"]), plan["bindings"]["backup"]["runtime_sha256"]
    )
    backup.require(
        cfg["plan"]["period_id"] == plan["period_id"], "Independent period declaration differs"
    )
    occurrences = {
        s["parameters"]["occurrence_id"]
        for s in plan["steps"]
        if s["kind"] in {"BACKUP", "RESTORE"}
    }
    backup.require(
        not occurrences & set(omitted) and occurrences | set(omitted) == set(cfg["bindings"]),
        "Every declared occurrence needs an operation or explicit omission",
    )
    for step in plan["steps"]:
        p = step["parameters"]
        moment = _time(p.get("event_at", p.get("attempted_at", p.get("recorded_at"))))
        if step["kind"] != "MONITOR":
            backup.require(
                _time(cfg["plan"]["period_start"])
                <= moment
                < _time(cfg["plan"]["period_end_exclusive"]),
                "Operation outside declared local period",
            )
        else:
            backup.require(_time(p["as_of"]) <= moment, "Monitor cutoff after recording")
    return plan


def _opening(plan):
    c = plan["bindings"]["configuration"]
    actual = configuration.inspect(Path(c["root"]), expected_runtime_sha256=c["runtime_sha256"])
    backup.require(
        actual["revision"] == c["revision"] and actual["current_sha256"] == c["current_sha256"],
        "Configuration opening state differs",
    )
    b = plan["bindings"]["backup"]
    with backup.database(Path(b["root"])) as db:
        cfg = backup._config(Path(b["root"]), b["runtime_sha256"])
        backup._bound_config(db, cfg, b["runtime_sha256"])
        backup.require(
            db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0] == b["revision"],
            "Backup opening revision differs",
        )


def create(destination, *, plan):
    destination = Path(destination)
    backup.private(destination.parent, True)
    backup.require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New private runner destination required",
    )
    plan = _plan(plan)
    for binding in plan["bindings"].values():
        source = Path(binding["root"])
        backup.require(
            not destination.is_relative_to(source) and not source.is_relative_to(destination),
            "Runner must be outside runtimes",
        )
    _opening(plan)
    body = {
        "plan": plan,
        "plan_sha256": sha(encoded(plan)),
        "code_sha256": _code(),
        "qualification": "LOCAL_DECLARED_PERIOD_NOT_FULL_YEAR_OR_ASSURANCE",
    }
    raw = encoded(body)
    with tempfile.TemporaryDirectory(prefix=".period-runner-", dir=destination.parent) as folder:
        stage = Path(folder)
        (stage / "PLAN.json").write_bytes(raw)
        (stage / "PLAN.json").chmod(0o600)
        with closing(sqlite3.connect(stage / "runner.sqlite3")) as db:
            db.execute(
                "CREATE TABLE journal(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,"
                "content TEXT NOT NULL,sha256 TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TRIGGER no_journal_update BEFORE UPDATE ON journal "
                "BEGIN SELECT RAISE(ABORT,'Immutable journal'); END"
            )
            db.execute(
                "CREATE TRIGGER no_journal_delete BEFORE DELETE ON journal "
                "BEGIN SELECT RAISE(ABORT,'Immutable journal'); END"
            )
        (stage / "runner.sqlite3").chmod(0o600)
        backup.require(_code() == body["code_sha256"], "Runner source changed")
        publish(stage, destination)
    return {"runner_sha256": sha(raw), "revision": 0, "status": "READY"}


@contextmanager
def _locked(root):
    root = backup.private(Path(root), True)
    file = backup.private(root / "runner.sqlite3")
    before, parent = file.stat(), root.stat()
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)

    def unchanged():
        info, directory = backup.private(file).stat(), backup.private(root, True).stat()
        backup.require(
            (info.st_dev, info.st_ino, directory.st_dev, directory.st_ino)
            == (before.st_dev, before.st_ino, parent.st_dev, parent.st_ino),
            "Runner path identity changed",
        )

    try:
        backup.require(
            (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == (before.st_dev, before.st_ino),
            "Runner file changed",
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            backup.require(False, "Recovery runner busy")
        with closing(sqlite3.connect(file.as_uri() + "?mode=rw", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            unchanged()
            yield db
            unchanged()
    finally:
        os.close(fd)


def _load(root, expected, db):
    raw = backup.checked_bytes(Path(root) / "PLAN.json", 1024 * 1024)
    backup.require(sha(raw) == expected, "Runner definition pin differs")
    body = decode(raw)
    backup.require(
        sha(encoded(body["plan"])) == body["plan_sha256"] and _code() == body["code_sha256"],
        "Plan or implementation pin changed",
    )
    backup.require(
        db.execute("SELECT COALESCE(SUM(length(content)),0),count(*) FROM journal").fetchone()[0]
        <= MAX_TOTAL,
        "Journal byte limit",
    )
    backup.require(
        db.execute("SELECT count(*) FROM journal").fetchone()[0] <= 128, "Journal event limit"
    )
    rows = db.execute("SELECT * FROM journal ORDER BY seq").fetchall()
    backup.require(len(rows) <= 128, "Journal event limit")
    completed, pending, prior = [], None, "0" * 64
    for i, row in enumerate(rows, 1):
        value = decode(row["content"])
        backup.require(row["kind"] in {"INTENT", "RESULT"}, "Unknown journal kind")
        _fields(
            value,
            {"step_id", "kind", "previous_sha256", "parameters", "captured"}
            if row["kind"] == "INTENT"
            else {"step_id", "intent_sha256", "result", "previous_sha256"},
        )
        backup.require(
            row["seq"] == i
            and sha(encoded(value)) == row["sha256"]
            and value["previous_sha256"] == prior,
            "Journal chain differs",
        )
        backup.require(
            len(completed) < len(body["plan"]["steps"]), "Unexpected extra journal event"
        )
        step = body["plan"]["steps"][len(completed)]
        backup.require(value["step_id"] == step["id"], "Journal step order differs")
        if row["kind"] == "INTENT":
            backup.require(
                pending is None and value["kind"] == step["kind"], "Unexpected pending intent"
            )
            _validate_frozen(body["plan"], step, completed, value)
            pending = {**value, "sha256": row["sha256"]}
        else:
            backup.require(
                row["kind"] == "RESULT"
                and pending is not None
                and value["intent_sha256"] == pending["sha256"],
                "Result intent differs",
            )
            _verify_result(body["plan"], step, pending["parameters"], value["result"])
            completed.append(value)
            pending = None
        prior = row["sha256"]
    return body, completed, pending, len(rows), prior


def _append(db, kind, value, seq):
    raw = encoded(value)
    backup.require(
        len(raw) <= 1024 * 1024
        and db.execute("SELECT COALESCE(SUM(length(content)),0) FROM journal").fetchone()[0]
        + len(raw)
        <= MAX_TOTAL,
        "Journal byte limit",
    )
    db.execute("INSERT INTO journal VALUES(?,?,?,?)", (seq, kind, raw.decode(), sha(raw)))
    db.commit()  # durable intent precedes every external runtime call
    return sha(raw)


def inspect(root, *, expected_runner_sha256):
    root = backup.private(Path(root), True)
    path = backup.private(root / "runner.sqlite3")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        body, completed, pending, revision, _ = _load(root, expected_runner_sha256, db)
    return {
        "revision": revision,
        "qualification": body["qualification"],
        "due_occurrence_completeness": "NOT_INFERRED_FROM_RUNNER_STATUS",
        "completed_steps": [r["step_id"] for r in completed],
        "pending": pending,
        "omissions": body["plan"]["omissions"],
        "status": "PENDING_EXPLICIT_RETRY"
        if pending
        else "COMPLETE"
        if len(completed) == len(body["plan"]["steps"])
        else "READY",
    }


def _validate_frozen(plan, step, completed, value):
    """Reconstruct plan-authorized envelope without recapturing mutable inputs."""
    parameters = decode(encoded(step["parameters"]))
    previous = {r["step_id"]: r["result"] for r in completed}
    captured_refs = {}
    for key, ref in step["refs"].items():
        pin = previous[ref["step_id"]].get(ref["field"])
        backup.exact_pin(pin)
        if "sha256_policy" in ref:
            backup.require(
                encoded({k: pin[k] for k in backup.FIELDS[:-1]})
                == encoded(ref["expected_identity"]),
                "Frozen producer identity differs",
            )
            captured_refs[key] = {"policy": ref["sha256_policy"], "pin": pin}
        else:
            backup.require(
                encoded(pin) == encoded(ref["expected_pin"]), "Frozen producer pin differs"
            )
        parameters[key] = pin
    _fields(value["captured"], {"native_refs", "metadata"})
    backup.require(
        encoded(value["captured"]["native_refs"]) == encoded(captured_refs),
        "Frozen reference capture differs",
    )
    binding = plan["bindings"][_which(step["kind"])]
    parameters["expected_runtime_sha256"] = binding["runtime_sha256"]
    metadata = value["captured"]["metadata"]
    if step["kind"] == "ADMIT":
        parameters.pop("metadata_capture")
        _fields(metadata, {"policy", "selected"})
        backup.require(
            metadata["policy"] == "CAPTURED_AFTER_OPERATION_NOT_PREDECLARED",
            "Frozen admission policy differs",
        )
        selected = metadata["selected"]
        _fields(
            selected,
            {
                "source_store_id",
                "source_location_sha256",
                "source_definition_pin",
                "source_pin",
                "metadata",
                "definition_metadata",
                "metadata_sha256",
                "identity_basis",
            },
        )
        c = plan["bindings"]["configuration"]
        location = sha(c["root"].encode())
        source_id = "SOURCE-" + sha(
            encoded({"location_sha256": location, "definition": c["definition_pin"]})
        )
        backup.require(
            selected["source_store_id"] == source_id
            and selected["source_location_sha256"] == location
            and encoded(selected["source_definition_pin"]) == encoded(c["definition_pin"])
            and encoded(selected["source_pin"]) == encoded(parameters["source_pin"])
            and selected["identity_basis"] == "LOCAL_ROUTING_IDENTITY_NOT_PRODUCER_AUTHENTICATION",
            "Frozen source binding differs",
        )
        for member, expected_pin in (
            ("metadata", parameters["source_pin"]),
            ("definition_metadata", c["definition_pin"]),
        ):
            _fields(
                selected[member],
                {*backup.FIELDS, "event_at", "available_at", "origin", "provenance"},
            )
            backup.require(
                encoded({k: selected[member][k] for k in backup.FIELDS}) == encoded(expected_pin),
                "Frozen metadata native pin differs",
            )
        backup.require(
            selected["metadata_sha256"]
            == sha(
                encoded(
                    {
                        "original": selected["metadata"],
                        "definition": selected["definition_metadata"],
                    }
                )
            ),
            "Frozen source metadata digest differs",
        )
        parameters.update(
            source_root=c["root"],
            source_definition_pin=c["definition_pin"],
            source_store_id=source_id,
            expected_source_metadata_sha256=selected["metadata_sha256"],
        )
    elif step["kind"] == "MONITOR":
        parameters.pop("jobs_capture")
        _fields(metadata, {"policy", "jobs_sha256"})
        backup.require(
            metadata["policy"] == "CAPTURED_ONCE_AT_INTENT_NOT_PREDECLARED",
            "Frozen monitor policy differs",
        )
        admission._hash(metadata["jobs_sha256"])
        parameters["expected_jobs_sha256"] = metadata["jobs_sha256"]
    else:
        backup.require(metadata == {}, "Unexpected metadata capture")
    backup.require(
        encoded(value["parameters"]) == encoded(parameters),
        "Frozen intent differs from immutable plan",
    )


def _resolve(plan, step, completed):
    parameters = decode(encoded(step["parameters"]))
    previous = {r["step_id"]: r["result"] for r in completed}
    captured_refs = {}
    for key, ref in step["refs"].items():
        pin = previous[ref["step_id"]].get(ref["field"])
        backup.exact_pin(pin)
        producer = next(s for s in plan["steps"] if s["id"] == ref["step_id"])
        source = plan["bindings"][_which(producer["kind"])]
        with backup.database(Path(source["root"])) as db:
            backup.native(db, pin)
        if "sha256_policy" in ref:
            backup.require(
                encoded({k: pin[k] for k in backup.FIELDS[:-1]})
                == encoded(ref["expected_identity"]),
                "Captured job identity differs",
            )
            captured_refs[key] = {"policy": ref["sha256_policy"], "pin": pin}
        else:
            backup.require(
                encoded(pin) == encoded(ref["expected_pin"]), "Dependency output pin differs"
            )
        parameters[key] = pin
    role = _which(step["kind"])
    binding = plan["bindings"][role]
    parameters["expected_runtime_sha256"] = binding["runtime_sha256"]
    captured = {}
    if step["kind"] == "ADMIT":
        parameters.pop("metadata_capture")
        c = plan["bindings"]["configuration"]
        selected = admission.inspect_source(
            Path(c["root"]),
            source_pin=parameters["source_pin"],
            source_definition_pin=c["definition_pin"],
        )
        parameters.update(
            source_root=c["root"],
            source_definition_pin=c["definition_pin"],
            source_store_id=selected["source_store_id"],
            expected_source_metadata_sha256=selected["metadata_sha256"],
        )
        captured = {"policy": "CAPTURED_AFTER_OPERATION_NOT_PREDECLARED", "selected": selected}
    if step["kind"] == "MONITOR":
        parameters.pop("jobs_capture")
        inventory = monitor.inspect(
            Path(binding["root"]),
            expected_runtime_sha256=binding["runtime_sha256"],
            as_of=parameters["as_of"],
        )
        backup.require(
            inventory["runtime_revision"] == parameters["expected_revision"],
            "Monitor capture revision differs",
        )
        parameters["expected_jobs_sha256"] = inventory["jobs_sha256"]
        captured = {
            "policy": "CAPTURED_ONCE_AT_INTENT_NOT_PREDECLARED",
            "jobs_sha256": inventory["jobs_sha256"],
        }
    return {
        "parameters": parameters,
        "captured": {"native_refs": captured_refs, "metadata": captured},
    }


def _invoke(plan, kind, parameters):
    root = Path(plan["bindings"][_which(kind)]["root"])
    if kind == "APPLY":
        return configuration.execute(root, operation="APPLY", **parameters)
    if kind == "EXPORT":
        return export.export_current(root, **parameters)
    if kind == "ADMIT":
        return admission.admit_dataset(root, **parameters)
    if kind == "LEASE":
        return backup.record_lease(root, **parameters)
    if kind == "BACKUP":
        return backup.run_backup(root, **parameters)
    if kind == "RESTORE":
        return backup.run_restore(root, **parameters)
    if kind == "MONITOR":
        return monitor.scan(root, **parameters)
    backup.require(False, "Unsupported operation")


def _verify_result(plan, step, parameters, result):
    backup.require(
        isinstance(result, dict)
        and type(result.get("revision")) is int
        and result["revision"] == parameters["expected_revision"] + 1,
        "Operation receipt revision differs",
    )
    root = Path(plan["bindings"][_which(step["kind"])]["root"])
    moment = _time(
        parameters.get("event_at", parameters.get("attempted_at", parameters.get("recorded_at")))
    )
    with backup.database(root) as db:
        if _which(step["kind"]) == "configuration":
            retained = db.execute(
                "SELECT result FROM configuration_commands WHERE command=?",
                (parameters["command_id"],),
            ).fetchone()
        else:
            retained = db.execute(
                "SELECT receipt FROM backup_runtime_commands WHERE command_id=?",
                (parameters["command_id"],),
            ).fetchone()
        backup.require(
            retained is not None and encoded(decode(retained[0])) == encoded(result),
            "Exact native command receipt differs",
        )
        for field in OUTPUTS[step["kind"]]:
            pin = result.get(field)
            if pin is None and field == "object_pin":
                backup.require(result.get("status") == "FAILED", "Missing completed copy original")
                continue
            row = backup.native(db, pin, at=moment)
            backup.require(row["event_at"] == moment, "Operation original time differs")
            if field in step["expected_pins"]:
                backup.require(
                    encoded(pin) == encoded(step["expected_pins"][field]),
                    "Expected operation original differs",
                )


def _finish(root, expected, db, body, completed, pending, revision, prior):
    step = body["plan"]["steps"][len(completed)]
    result = _invoke(body["plan"], step["kind"], pending["parameters"])
    _verify_result(body["plan"], step, pending["parameters"], result)
    backup.require(
        sha(backup.checked_bytes(Path(root) / "PLAN.json", 1024 * 1024)) == expected
        and _code() == body["code_sha256"],
        "Runner changed after operation; intent remains pending",
    )
    record = {
        "step_id": step["id"],
        "intent_sha256": pending["sha256"],
        "result": result,
        "previous_sha256": prior,
    }
    _append(db, "RESULT", record, revision + 1)
    return {"revision": revision + 1, "step_id": step["id"], "result": result}


def execute_next(root, *, expected_runner_sha256, expected_revision, step_id):
    with _locked(root) as db:
        body, completed, pending, revision, prior = _load(root, expected_runner_sha256, db)
        backup.require(
            type(expected_revision) is int and revision == expected_revision and pending is None,
            "Stale runner or pending explicit retry",
        )
        backup.require(len(completed) < len(body["plan"]["steps"]), "Period plan complete")
        step = body["plan"]["steps"][len(completed)]
        backup.require(step_id == step["id"], "Expected next step differs")
        if not completed:
            _opening(body["plan"])
        value = {
            "step_id": step_id,
            "kind": step["kind"],
            "previous_sha256": prior,
            **_resolve(body["plan"], step, completed),
        }
        intent_sha = _append(db, "INTENT", value, revision + 1)
        return _finish(
            root,
            expected_runner_sha256,
            db,
            body,
            completed,
            {**value, "sha256": intent_sha},
            revision + 1,
            intent_sha,
        )


def retry_pending(root, *, expected_runner_sha256, expected_revision, intent_sha256):
    with _locked(root) as db:
        body, completed, pending, revision, prior = _load(root, expected_runner_sha256, db)
        backup.require(
            type(expected_revision) is int
            and revision == expected_revision
            and pending is not None
            and pending["sha256"] == intent_sha256,
            "Exact inspected pending intent required",
        )
        return _finish(root, expected_runner_sha256, db, body, completed, pending, revision, prior)
