"""Persistent private data-only target; local exercise approvals are not deployment authority."""

import os
import tempfile
import time
from pathlib import Path

from .company_backup_runtime import (
    checked_bytes,
    database,
    exact_pin,
    native,
    private,
    require,
)
from .company_change_activity import QUALIFICATION as SOURCE_QUALIFICATION
from .company_change_activity import evaluate
from .company_store import CompanyStore, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .private_publication import publish

QUALIFICATION = "PERSISTENT_LOCAL_DATA_ONLY_CONFIGURATION_NOT_ENTERPRISE_DEPLOYMENT"
SLOTS = {
    "baseline": "configurations",
    "configuration": "configurations",
    "build": "builds",
    "tests": "tests",
    "review": "peer_reviews",
    "gate": "release_gate",
    "rollback_plan": "recovery",
}
SYSTEMS = ("configuration_runtime", "configuration_operation", "configuration_observation")
LIMIT = 1024 * 1024


def _link(value, row):
    require(isinstance(value, dict), "Exact upstream link required")
    require(
        set(value) == {"system_id", "record_id", "version", "sha256", "available_at"},
        "Exact upstream link fields required",
    )
    require(
        type(value["version"]) is int and value["version"] > 0,
        "Exact integer upstream version required",
    )
    require(
        all(
            value[k] == row[v]
            for k, v in (
                ("system_id", "system"),
                ("record_id", "record"),
                ("version", "version"),
                ("sha256", "sha256"),
            )
        )
        and _time(value["available_at"]) == row["available_at"],
        "Upstream relationship differs",
    )


def _sources(root, refs, at):
    require(isinstance(refs, dict) and set(refs) == set(SLOTS), "Exact source slots required")
    for name, ref in refs.items():
        exact_pin(ref)
        require(ref["system"] == SLOTS[name], "Source system differs")
    identities = {(p["company"], p["branch"]) for p in refs.values()}
    require(len(identities) == 1, "One original company and branch required")
    with database(root) as db:
        rows = {name: native(db, ref, at) for name, ref in refs.items()}
        source_owners = {
            name: db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
                (ref["company"], ref["branch"], ref["system"]),
            ).fetchone()
            for name, ref in refs.items()
        }
    bodies = {name: decode(row["content"]) for name, row in rows.items()}
    require(
        all(
            isinstance(b, dict) and b.get("classification") == SOURCE_QUALIFICATION
            for b in bodies.values()
        ),
        "Qualified original change sources required",
    )
    for body in bodies.values():
        _id(body.get("cycle_id"))
    require(
        len({b.get("cycle_id") for b in bodies.values()}) == 1, "One original change cycle required"
    )
    b, t, r, g = (bodies[k] for k in ("build", "tests", "review", "gate"))
    for value, target in (
        (b.get("source"), "configuration"),
        (t.get("artifact"), "build"),
        (r.get("artifact"), "build"),
        (g.get("artifact"), "build"),
        (g.get("tests"), "tests"),
        (g.get("peer_review"), "review"),
        (bodies["rollback_plan"].get("restore_source"), "baseline"),
    ):
        _link(value, rows[target])
    approved = bodies["configuration"]["configuration"]
    baseline = bodies["baseline"]["configuration"]
    for name, config in (("configuration", approved), ("baseline", baseline)):
        evaluate(config)
        require(
            bodies[name].get("configuration_sha256") == sha(encoded(config)),
            "Configuration content pin differs",
        )
    require(
        encoded(b.get("package"))
        == encoded({"format": "LOCAL_CONFIG_PACKAGE_V1", "configuration": approved})
        and b.get("package_sha256") == sha(encoded(b["package"])),
        "Package content differs",
    )
    require(
        t.get("passed") is True
        and t.get("test_scope") == "SCHEMA_AND_COMBINED_LIMIT"
        and t.get("omitted_checks") == []
        and evaluate(approved)["within_local_limit"],
        "Mandatory local test scope required",
    )
    require(
        r.get("decision") == "APPROVED"
        and encoded(r.get("calculation")) == encoded(evaluate(approved))
        and g.get("decision") == "ALLOWED",
        "Exact local approval and allowed gate required",
    )
    checks = t.get("tests")
    require(
        isinstance(checks, list)
        and len(checks) == 2
        and {x.get("name") for x in checks}
        == {"positive_integer_schema", "combined_retry_timeout_limit"}
        and all(x.get("passed") is True for x in checks),
        "Mandatory test records differ",
    )
    combined = next(x for x in checks if x["name"] == "combined_retry_timeout_limit")
    require(
        encoded(combined.get("calculation")) == encoded(evaluate(approved)),
        "Retained combined test calculation differs",
    )
    require(
        encoded(bodies["rollback_plan"].get("acceptance")) == encoded(evaluate(baseline)),
        "Recovery baseline acceptance differs",
    )
    owner_rows = decode(rows["gate"]["provenance"]).get("owner_assignment", [])
    owners = {a.get("primary_person_id") for a in owner_rows}
    reviewers = {a.get("operating_reviewer_person_id") for a in owner_rows}
    require(len(owners) == len(reviewers) == 1, "Exact scoped source roles required")
    owner, reviewer = owners.pop(), reviewers.pop()
    _id(owner)
    _id(reviewer)
    require(
        owner != reviewer and r.get("reviewer_id") == reviewer, "Distinct local reviewer required"
    )
    require(
        all(
            source_owners[name] is not None
            and source_owners[name]["owner"] == (reviewer if name == "review" else owner)
            for name in SLOTS
        ),
        "Registered source owners differ from local role assignments",
    )
    for earlier, later in (
        ("baseline", "rollback_plan"),
        ("configuration", "build"),
        ("build", "tests"),
        ("tests", "review"),
        ("review", "gate"),
    ):
        require(
            rows[earlier]["available_at"] <= rows[later]["event_at"],
            "Source dependency unavailable at consuming event",
        )
    return rows, baseline, approved, owner, reviewer


def _write(root, name, raw):
    """New immutable file through anchored directory descriptors, never aliases."""
    parent = private(Path(root), True)
    require("/" not in name and name not in (".", ".."), "Simple file name required")
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(out, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)
    require(checked_bytes(parent / name, LIMIT) == raw, "Persisted bytes changed")


def _insert(db, cfg, system, record, body, at, command):
    raw = encoded(body)
    require(
        len(raw) <= LIMIT and db.execute("SELECT count(*) FROM versions").fetchone()[0] < 20000,
        "Bounded runtime inventory required",
    )
    key = [cfg["company"], cfg["branch"], system, record]
    provenance = {
        "source_reference": cfg["target_id"],
        "classification": QUALIFICATION,
        "runtime_sha256": sha(encoded(cfg)),
        "control_ids": ["SH-ENG-004", "SH-CFG-002"],
    }
    digest = sha(raw)
    fingerprint = sha(
        _json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()
    )
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
    return dict(
        zip(
            ("company", "branch", "system", "record", "version", "sha256"),
            (*key, 1, digest),
            strict=True,
        )
    )


def initialize(destination, *, source_root, source_pins, as_of, target_id):
    destination, source_root = Path(destination), private(Path(source_root), True)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists(),
        "New canonical private destination required",
    )
    require(
        not destination.is_relative_to(source_root) and not source_root.is_relative_to(destination),
        "Separate original and runtime roots required",
    )
    _id(target_id)
    at = _time(as_of)
    source_pins = decode(encoded(source_pins))
    rows, baseline, approved, owner, reviewer = _sources(source_root, source_pins, at)
    cfg = {
        "format": "LOCAL_CONFIGURATION_RUNTIME_V1",
        "company": source_pins["gate"]["company"],
        "branch": source_pins["gate"]["branch"],
        "target_id": target_id,
        "initialized_at": at,
        "operator_id": owner,
        "reviewer_id": reviewer,
        "source_pins": source_pins,
        "source_metadata_sha256": sha(
            encoded([{k: v for k, v in row.items() if k != "content"} for row in rows.values()])
        ),
        "source_location_sha256": sha(str(source_root).encode()),
        "baseline_sha256": sha(encoded(baseline)),
        "approved_sha256": sha(encoded(approved)),
        "qualification": QUALIFICATION,
        "authority": "PINNED_LOCAL_EXERCISE_ONLY",
        "code_sha256": sha(Path(__file__).read_bytes()),
    }
    digest = sha(encoded(cfg))
    with tempfile.TemporaryDirectory(
        dir=destination.parent, prefix="configuration-stage-"
    ) as folder:
        stage = Path(folder)
        store = CompanyStore(stage)
        for system in SYSTEMS:
            store.register_system(cfg["company"], cfg["branch"], system, owner)
        (stage / "objects").mkdir(mode=0o700)
        (stage / "sources").mkdir(mode=0o700)
        for slot, row in rows.items():
            _write(stage / "sources", slot + ".json", row["content"])
        _write(stage, "RUNTIME.json", encoded(cfg))
        _write(stage / "objects", "initial.json", encoded(baseline))
        with database(stage, True) as db:
            db.execute(
                "CREATE TABLE configuration_state (id INTEGER PRIMARY KEY, config_sha TEXT, "
                "revision INTEGER, file TEXT, sha256 TEXT, event_at TEXT)"
            )
            db.execute(
                "CREATE TABLE configuration_commands "
                "(command TEXT PRIMARY KEY, digest TEXT, result BLOB)"
            )
            db.execute(
                "CREATE TRIGGER configuration_commands_immutable_update "
                "BEFORE UPDATE ON configuration_commands "
                'BEGIN SELECT RAISE(ABORT,"immutable command"); END'
            )
            db.execute(
                "CREATE TRIGGER configuration_commands_immutable_delete "
                "BEFORE DELETE ON configuration_commands "
                'BEGIN SELECT RAISE(ABORT,"immutable command"); END'
            )
            db.execute(
                "INSERT INTO configuration_state VALUES(1,?,0,?,?,?)",
                (digest, "initial.json", cfg["baseline_sha256"], at),
            )
            _insert(db, cfg, "configuration_runtime", target_id, cfg, at, "INITIALIZE")
        # Original native content/metadata remain fixed through publication.
        require(_sources(source_root, source_pins, at)[0] == rows, "Original source changed")
        require(
            sha(Path(__file__).read_bytes()) == cfg["code_sha256"],
            "Initialization module changed before publication",
        )
        publish(stage, destination)
    return {
        "runtime_sha256": digest,
        "revision": 0,
        "current_sha256": cfg["baseline_sha256"],
        "qualification": QUALIFICATION,
    }


def _config(root, expected):
    cfg_raw = checked_bytes(Path(root) / "RUNTIME.json", LIMIT)
    require(sha(cfg_raw) == expected, "Runtime configuration pin differs")
    cfg = decode(cfg_raw)
    require(cfg.get("format") == "LOCAL_CONFIGURATION_RUNTIME_V1", "Runtime format differs")
    for slot, ref in cfg["source_pins"].items():
        require(
            sha(checked_bytes(Path(root) / "sources" / (slot + ".json"), LIMIT)) == ref["sha256"],
            "Retained source differs",
        )
    return cfg


def _current(root, db, cfg, expected):
    state = db.execute("SELECT * FROM configuration_state WHERE id=1").fetchone()
    require(
        state is not None and state["config_sha"] == expected, "Runtime database binding differs"
    )
    definition = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? "
        "AND system='configuration_runtime' AND record=? AND version=1",
        (cfg["company"], cfg["branch"], cfg["target_id"]),
    ).fetchone()
    require(
        definition is not None
        and definition["sha256"] == expected
        and sha(definition["content"]) == expected,
        "Native runtime definition differs",
    )
    name = state["file"]
    require(
        isinstance(name, str) and name.endswith(".json") and "/" not in name and ".." not in name,
        "Unsafe current file pointer",
    )
    raw = checked_bytes(Path(root) / "objects" / name, LIMIT)
    require(sha(raw) == state["sha256"], "Current file integrity differs")
    config = decode(raw)
    evaluate(config)
    return dict(state), raw, config


def inspect(runtime, *, expected_runtime_sha256):
    cfg = _config(runtime, expected_runtime_sha256)
    with database(runtime) as db:
        state, raw, config = _current(runtime, db, cfg, expected_runtime_sha256)
    require(_config(runtime, expected_runtime_sha256) == cfg, "Runtime changed during read")
    return {
        "runtime_sha256": expected_runtime_sha256,
        "revision": state["revision"],
        "current_sha256": sha(raw),
        "configuration": config,
        "event_at": state["event_at"],
        "qualification": QUALIFICATION,
        "observation_basis": "INDEPENDENT_RETAINED_FILE_READ",
    }


def execute(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    operation,
    expected_current_sha256,
    operator_id,
    event_at,
    rationale,
    expected_target_sha256=None,
    configuration=None,
):
    """APPLY approved original, DRIFT explicit local data, ROLLBACK original, RECONCILE only."""
    require(operation in ("APPLY", "DRIFT", "ROLLBACK", "RECONCILE"), "Unknown local operation")
    require(type(expected_revision) is int and expected_revision >= 0, "Exact revision required")
    _id(command_id)
    _id(operator_id)
    require(
        isinstance(rationale, str) and 1 <= len(rationale.strip()) <= 2000,
        "Bounded rationale required",
    )
    cfg = _config(runtime, expected_runtime_sha256)
    require(operator_id == cfg["operator_id"], "Scoped local operator required")
    at = _time(event_at)
    require(
        (operation == "DRIFT") == (configuration is not None), "Explicit drift configuration only"
    )
    if configuration is not None:
        configuration = decode(encoded(configuration))
        evaluate(configuration)
    if operation in ("APPLY", "ROLLBACK"):
        require(
            expected_target_sha256
            == cfg["approved_sha256" if operation == "APPLY" else "baseline_sha256"],
            "Exact authorized target pin required",
        )
    else:
        require(expected_target_sha256 is None, "No inferred target pin")
    payload = {
        k: v
        for k, v in locals().copy().items()
        if k
        in (
            "expected_runtime_sha256",
            "expected_revision",
            "command_id",
            "operation",
            "expected_current_sha256",
            "operator_id",
            "event_at",
            "rationale",
            "expected_target_sha256",
            "configuration",
        )
    }
    payload["event_at"] = at
    digest = sha(encoded(payload))
    started = time.monotonic_ns()
    execution_code_sha256 = sha(Path(__file__).read_bytes())
    with database(runtime, True) as db:
        old = db.execute(
            "SELECT * FROM configuration_commands WHERE command=?", (command_id,)
        ).fetchone()
        state, current_raw, actual = _current(runtime, db, cfg, expected_runtime_sha256)
        if old:
            require(old["digest"] == digest, "Command replay differs")
            return decode(old["result"])
        require(state["revision"] == expected_revision, "Runtime revision conflict")
        require(state["sha256"] == expected_current_sha256, "Current target pin differs")
        require(at >= state["event_at"], "Operation precedes current runtime event")
        approved = decode(checked_bytes(Path(runtime) / "sources" / "configuration.json", LIMIT))[
            "configuration"
        ]
        target = None
        if operation == "DRIFT":
            target = configuration
        elif operation in ("APPLY", "ROLLBACK"):
            slot = "configuration" if operation == "APPLY" else "baseline"
            target = decode(checked_bytes(Path(runtime) / "sources" / (slot + ".json"), LIMIT))[
                "configuration"
            ]
        filename = state["file"]
        new_raw = current_raw
        if target is not None:
            new_raw = encoded(target)
            filename = sha(encoded([command_id, digest])) + ".json"
            _write(Path(runtime) / "objects", filename, new_raw)
        body = {
            "operation": operation,
            "operator_id": operator_id,
            "rationale": rationale,
            "authored_event_at": at,
            "real_recorded_at": _now(),
            "execution_module_sha256": execution_code_sha256,
            "elapsed_ns": time.monotonic_ns() - started,
            "prior_sha256": sha(current_raw),
            "current_sha256": sha(new_raw),
            "runtime_sha256": expected_runtime_sha256,
            "qualification": QUALIFICATION,
            "authority": "AUTHORED_LOCAL_DRIFT_NOT_APPROVAL"
            if operation == "DRIFT"
            else "PINNED_LOCAL_EXERCISE_ONLY",
            "source_pins": cfg["source_pins"],
            "field_differences": [
                {"field": k, "actual": actual[k], "approved": approved[k]}
                for k in sorted(approved)
                if encoded(actual[k]) != encoded(approved[k])
            ],
            "comparison_basis": "PRE_OPERATION_FILE_VS_PINNED_LOCAL_APPROVED_CONFIGURATION",
            "bytes_match_approved": current_raw == encoded(approved),
            "automatic_ticket_closure": False,
        }
        record = "OP-" + sha(encoded([cfg["target_id"], command_id]))
        result_pin = _insert(
            db,
            cfg,
            "configuration_observation" if operation == "RECONCILE" else "configuration_operation",
            record,
            body,
            at,
            command_id,
        )
        result = {"revision": expected_revision + 1, "native_pin": result_pin, **body}
        require(
            _config(runtime, expected_runtime_sha256) == cfg,
            "Runtime sources changed before commit",
        )
        require(
            checked_bytes(Path(runtime) / "objects" / state["file"], LIMIT) == current_raw,
            "Prior file changed before commit",
        )
        require(
            checked_bytes(Path(runtime) / "objects" / filename, LIMIT) == new_raw,
            "Target file changed before commit",
        )
        require(
            sha(Path(__file__).read_bytes()) == execution_code_sha256,
            "Execution module changed before commit",
        )
        db.execute(
            "UPDATE configuration_state SET revision=?,file=?,sha256=?,event_at=? WHERE id=1",
            (result["revision"], filename, sha(new_raw), at),
        )
        db.execute(
            "INSERT INTO configuration_commands VALUES(?,?,?)",
            (command_id, digest, encoded(result)),
        )
    return result
