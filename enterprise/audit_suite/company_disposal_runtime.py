"""Dispose only newly created private fixture copies; never source/audit history."""

import fcntl
import os
import stat
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from .company_backup_runtime import checked_bytes, database, exact_pin, native, private, require
from .company_operating_period import _plan
from .company_store import CompanyStore, CompanyStoreError, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_FIXTURE_UNLINK_NOT_SECURE_ERASE_OR_APPROVED_LEGAL_RETENTION"
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
MAX_EVENTS = 256


NATIVE_LIMITS = {
    **dict.fromkeys(("company", "branch", "system", "record", "command_id", "origin"), 128),
    **dict.fromkeys(("event_at", "available_at", "imported_at", "sha256", "input_digest"), 64),
    "version": 16,
    "content": 256 * 1024,
    "provenance": 16 * 1024,
}


def _preflight(db, table, limits, count, total=16 * 1024 * 1024, *, where="", params=()):
    # Table/column/filter values are internal constants only, never caller SQL.
    lengths = [f"COALESCE(length(CAST({column} AS BLOB)),0)" for column in limits]
    maxima = [f"COALESCE(MAX({expr}),0)" for expr in lengths]
    row_sum = "+".join(lengths)
    result = db.execute(
        "SELECT COUNT(*),COALESCE(SUM("
        + row_sum
        + "),0),"
        + ",".join(maxima)
        + " FROM "
        + table
        + " "
        + where,
        params,
    ).fetchone()
    require(
        result[0] <= count
        and result[1] <= total
        and all(size <= limit for size, limit in zip(result[2:], limits.values(), strict=True)),
        "Bounded retained table metadata and row count required: " + table,
    )


def _copy_status(outcome):
    return "UNLINKED" if outcome == "UNLINKED_VERIFIED_OWNED_INODE" else "MISSING_UNATTRIBUTED"


def _completion(pending):
    return {
        "status": (
            "COMPLETED_WITH_UNATTRIBUTED_MISSING_COPY"
            if "MISSING_AFTER_RETAINED_INTENT" in pending["completed"].values()
            else "SELECTED_LOCAL_COPIES_UNLINKED"
        ),
        "copies": pending["completed"],
        "secure_erasure": "NOT_ASSERTED",
        "qualification": QUALIFICATION,
    }


def _code():
    names = (
        "company_disposal_runtime.py",
        "company_backup_runtime.py",
        "company_operating_period.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
    )
    return {name: sha(Path(__file__).with_name(name).read_bytes()) for name in names}


def _text(v):
    require(
        isinstance(v, str) and 1 <= len(v.strip()) <= 2000, "Bounded explicit rationale required"
    )


def _file_info(fd):
    info = os.fstat(fd)
    require(
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == os.getuid()
        and not info.st_mode & 0o077
        and 0 < info.st_size <= 65536,
        "Owned bounded private fixture file required",
    )
    raw = os.read(fd, 65537)
    final = os.fstat(fd)
    require(len(raw) == info.st_size, "Incomplete bounded fixture read")
    require(
        (info.st_dev, info.st_ino, info.st_size, info.st_ctime_ns, info.st_mode)
        == (final.st_dev, final.st_ino, final.st_size, final.st_ctime_ns, final.st_mode),
        "Fixture changed during read",
    )
    return {"device": info.st_dev, "inode": info.st_ino, "sha256": sha(raw), "bytes": len(raw)}


def _declaration(root, ref, at, *, with_metadata=False):
    exact_pin(ref)
    with database(root) as db:
        _preflight(
            db,
            "versions",
            NATIVE_LIMITS,
            1,
            where="WHERE company=? AND branch=? AND system=? AND record=? AND version=?",
            params=tuple(ref[k] for k in FIELDS[:-1]),
        )
        row = native(db, ref, at)
    body = decode(row["content"])
    require(
        ref["system"] == "operating_period_ledger"
        and body.get("kind") == "PERIOD_DECLARATION"
        and row["origin"] == "AUTHORED_TRAINING_SOURCE",
        "Explicit native declaration required",
    )
    p = _plan(body["plan"])
    require(
        p["control_ids"] == ["SH-REC-004"]
        and ref["version"] == 1
        and (ref["company"], ref["branch"], ref["record"])
        == (p["company_id"], p["branch_id"], p["period_id"]),
        "Declaration routing differs",
    )
    metadata = sha(
        encoded({k: row[k] for k in (*FIELDS, "event_at", "available_at", "origin", "provenance")})
    )
    return (p, metadata) if with_metadata else p


def _provenance(cfg):
    return {
        "control_ids": ["SH-REC-004"],
        "classification": QUALIFICATION,
        "runtime_sha256": sha(encoded(cfg)),
        "declaration": cfg["declaration_pin"],
        "content_retention": "METADATA_ONLY_NO_DISPOSED_BYTES",
    }


def _validate_native(row, cfg, system, record, raw, at):
    key = [cfg["plan"]["company_id"], cfg["plan"]["branch_id"], system, record]
    provenance = _provenance(cfg)
    digest = sha(raw)
    require(
        row is not None
        and [row[k] for k in FIELDS[:4]] == key
        and type(row["version"]) is int
        and row["version"] == 1
        and row["event_at"] == row["available_at"] == at
        and row["origin"] == "AUTHORED_TRAINING_SOURCE"
        and encoded(decode(row["provenance"])) == encoded(provenance)
        and row["content"] == raw
        and row["sha256"] == digest
        and row["command_id"] == record
        and row["input_digest"]
        == sha(_json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()),
        "Exact native identity, metadata, bytes and command binding required",
    )


def _insert(db, cfg, record, body, at):
    raw = encoded(body)
    require(len(raw) <= 256 * 1024, "Native metadata bound exceeded")
    require(
        db.execute("SELECT COALESCE(SUM(length(content)),0) FROM versions").fetchone()[0] + len(raw)
        <= 16 * 1024 * 1024,
        "Native aggregate byte limit exceeded",
    )
    system = "disposal_definition" if record == "DEFINITION" else "disposal_operation"
    key = [cfg["plan"]["company_id"], cfg["plan"]["branch_id"], system, record]
    provenance = _provenance(cfg)
    digest = sha(raw)
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
            record,
            sha(_json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, digest]).encode()),
        ),
    )
    _preflight(db, "versions", NATIVE_LIMITS, MAX_EVENTS + 1)
    return dict(zip(FIELDS, (*key, 1, digest), strict=True))


def initialize(destination, *, repository, declaration_root, declaration_pin, copies, as_of):
    """Create only new disposable copies. Payload bytes never enter native records."""
    destination, original = Path(destination), private(Path(declaration_root), True)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists()
        and not destination.is_relative_to(original)
        and not original.is_relative_to(destination),
        "New separate canonical private runtime required",
    )
    at = _time(as_of)
    ref = decode(encoded(declaration_pin))
    p, declaration_metadata = _declaration(original, ref, at, with_metadata=True)
    require(p["declared_at"] <= at <= p["period_start"], "Initialize before declared period")
    require(
        isinstance(copies, list) and 1 <= len(copies) <= 32,
        "One to32 declared fixture copies required",
    )
    admitted = []
    for c in copies:
        require(
            isinstance(c, dict) and set(c) == {"id", "kind", "content", "not_before", "holds"},
            "Exact copy declaration required",
        )
        _id(c["id"])
        require(
            isinstance(c["kind"], str)
            and c["kind"] in {"ACTIVE", "BACKUP"}
            and isinstance(c["content"], bytes)
            and 0 < len(c["content"]) <= 65536,
            "Bounded nonpersonal fixture bytes required",
        )
        require(
            isinstance(c["holds"], list)
            and len(c["holds"]) <= 16
            and all(isinstance(x, str) for x in c["holds"])
            and len(set(c["holds"])) == len(c["holds"]),
            "Explicit distinct local holds required",
        )
        for hold in c["holds"]:
            _id(hold)
        admitted.append({**c, "not_before": _time(c["not_before"]), "holds": list(c["holds"])})
    require(
        len({c["id"] for c in admitted}) == len(admitted)
        and {c["id"] for c in admitted} == {i["id"] for i in p["inventory"]},
        "Copy inventory must exactly match independent declaration",
    )
    org = snapshot(repository, as_of=at[:10])
    owner = next(
        a["primary_person_id"]
        for a in org["control_assignments"]
        if a["control_id"] == "SH-REC-004"
    )
    require(owner == p["owner_id"], "Scoped local disposal operator differs")
    code_pins = _code()
    code_pin = code_pins["company_disposal_runtime.py"]
    with tempfile.TemporaryDirectory(prefix="disposal-stage-", dir=destination.parent) as tmp:
        stage = Path(tmp)
        store = CompanyStore(stage)
        for system in ["disposal_definition", "disposal_operation"]:
            store.register_system(p["company_id"], p["branch_id"], system, owner)
        directory = stage / "copies"
        directory.mkdir(mode=0o700)
        inventory = {}
        for c in admitted:
            name = sha(c["id"].encode()) + ".bin"
            path = directory / name
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                require(os.write(fd, c["content"]) == len(c["content"]), "Incomplete fixture write")
                os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                inventory[c["id"]] = {k: v for k, v in c.items() if k != "content"} | {
                    "file": name,
                    "identity": _file_info(fd),
                }
            finally:
                os.close(fd)
        dir_info = directory.stat()
        cfg = {
            "format": "LOCAL_DISPOSAL_RUNTIME_V1",
            "plan": p,
            "declaration_root": str(original),
            "declaration_pin": ref,
            "declaration_metadata_sha256": declaration_metadata,
            "operator_id": owner,
            "initialized_at": at,
            "copies": inventory,
            "copy_directory_identity": [dir_info.st_dev, dir_info.st_ino],
            "qualification": QUALIFICATION,
            "code_sha256": code_pin,
            "implementation_sha256": code_pins,
            "implementation_pin_scope": "MAINTAINED_FILES_NOT_LOADED_BINARY_ATTESTATION",
            "authority": "EXPLICIT_LOCAL_EXERCISE_NOT_LEGAL_HOLD_RELEASE_OR_CORPORATE_RETENTION",
        }
        raw = encoded(cfg)
        with (stage / "RUNTIME.json").open("xb") as f:
            os.chmod(stage / "RUNTIME.json", 0o600)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        with database(stage, True) as db:
            db.executescript("""CREATE TABLE disposal_state(
                    revision INTEGER,last_at TEXT,state TEXT);
                CREATE TABLE disposal_events(seq INTEGER PRIMARY KEY,kind TEXT,
                    command_id TEXT,body TEXT,sha256 TEXT,native_pin TEXT);
                CREATE TRIGGER disposal_immutable_update BEFORE UPDATE ON disposal_events
                    BEGIN SELECT RAISE(ABORT,'Immutable event'); END;
                CREATE TRIGGER disposal_immutable_delete BEFORE DELETE ON disposal_events
                    BEGIN SELECT RAISE(ABORT,'Immutable event'); END;""")
            initial = {
                "copies": {
                    k: {"status": "PRESENT", "holds": v["holds"]} for k, v in inventory.items()
                },
                "authorizations": {},
                "pending": None,
            }
            db.execute("INSERT INTO disposal_state VALUES(?,?,?)", (0, at, _json(initial)))
            _insert(db, cfg, "DEFINITION", cfg, at)
        require(
            _declaration(original, ref, at, with_metadata=True) == (p, declaration_metadata)
            and _code() == code_pins,
            "Declaration or code changed before publication",
        )
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        publish(stage, destination)
    return {
        "runtime_sha256": sha(raw),
        "revision": 0,
        "copy_count": len(inventory),
        "qualification": QUALIFICATION,
    }


def _config(root, expected):
    raw = checked_bytes(root / "RUNTIME.json", 2 * 1024 * 1024)
    require(sha(raw) == expected, "Runtime definition changed")
    cfg = decode(raw)
    require(cfg.get("format") == "LOCAL_DISPOSAL_RUNTIME_V1", "Disposal runtime required")
    require(
        cfg["implementation_sha256"] == _code()
        and cfg["code_sha256"] == cfg["implementation_sha256"]["company_disposal_runtime.py"],
        "Pinned runtime code changed",
    )
    require(
        isinstance(cfg.get("copies"), dict) and 1 <= len(cfg["copies"]) <= 32,
        "Bounded initialized copy inventory required",
    )
    for ident, item in cfg["copies"].items():
        _id(ident)
        require(
            isinstance(item, dict)
            and item.get("id") == ident
            and item.get("file") == sha(ident.encode()) + ".bin",
            "Only generated internal copy names are permitted",
        )
        identity = item.get("identity")
        require(
            isinstance(identity, dict)
            and set(identity) == {"device", "inode", "bytes", "sha256"}
            and all(
                type(identity[k]) is int and identity[k] > 0 for k in ("device", "inode", "bytes")
            )
            and identity["bytes"] <= 65536
            and isinstance(identity["sha256"], str)
            and len(identity["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in identity["sha256"]),
            "Exact initialized private copy identity required",
        )
    return cfg


@contextmanager
def _locked(root, expected):
    root = private(Path(root), True)
    path = private(root / "company.sqlite3")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cfg = _config(root, expected)
        yield root, cfg
    except BlockingIOError as exc:
        raise CompanyStoreError("Disposal runtime busy") from exc
    finally:
        os.close(fd)


@contextmanager
def _directory(root, cfg):
    directory = private(root / "copies", True)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(
            [info.st_dev, info.st_ino] == cfg["copy_directory_identity"],
            "Copy directory identity changed",
        )
        yield fd
        final = private(root / "copies", True).stat()
        require(
            (final.st_dev, final.st_ino) == (info.st_dev, info.st_ino), "Copy directory replaced"
        )
    finally:
        os.close(fd)


def _read_file(fd, name):
    try:
        file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    except FileNotFoundError:
        return None
    try:
        return _file_info(file)
    finally:
        os.close(file)


def _fresh_command(db, command):
    require(
        db.execute(
            "SELECT 1 FROM disposal_events WHERE command_id=? AND kind IN ('CONTROL','INTENT')",
            (command,),
        ).fetchone()
        is None,
        "Command identity already used; explicit pending retry required",
    )


def _transition(cfg, state, body, revision):
    """Recompute metadata transitions; never infer that a filesystem unlink occurred."""
    at, kind, request = body["event_at"], body["kind"], body["input"]
    _id(body["command_id"])
    require(_time(at) == at and isinstance(request, dict), "Typed event time and input required")
    after = deepcopy(state)
    if kind == "CONTROL":
        require(
            set(request) == {"action", "payload", "operator_id", "event_at", "expected_revision"}
            and request["operator_id"] == cfg["operator_id"]
            and request["event_at"] == at
            and type(request["expected_revision"]) is int
            and request["expected_revision"] == revision,
            "Control authority/CAS differs",
        )
        after = _control_state(cfg, state, request["action"], request["payload"], at)
        observation = {
            "status": "LOCAL_CONTROL_RECORDED",
            "action": request["action"],
            "qualification": QUALIFICATION,
        }
    elif kind == "INTENT":
        require(
            set(request)
            == {"expected_revision", "operator_id", "authorization_id", "copy_ids", "event_at"}
            and request["operator_id"] == cfg["operator_id"]
            and request["event_at"] == at
            and type(request["expected_revision"]) is int
            and request["expected_revision"] == revision
            and state["pending"] is None,
            "Exact intent authority/CAS required",
        )
        ids = request["copy_ids"]
        require(
            isinstance(ids, list)
            and 1 <= len(ids) <= 32
            and all(isinstance(x, str) for x in ids)
            and len(set(ids)) == len(ids)
            and set(ids) <= set(cfg["copies"]),
            "Exact intent inventory required",
        )
        _id(request["authorization_id"])
        for ident in ids:
            require(
                state["copies"][ident]["status"] == "PRESENT", "Disposed copy cannot be adopted"
            )
            _eligible(cfg, state, request["authorization_id"], ident, at)
        pending = {
            "command_id": body["command_id"],
            "request": request,
            "expected": {i: cfg["copies"][i]["identity"] for i in ids},
            "completed": {},
        }
        pending["intent_sha256"] = sha(encoded(pending))
        after["pending"] = pending
        observation = {"status": "PENDING_EXPLICIT_LOCAL_UNLINK"}
    else:
        pending = state["pending"]
        require(
            pending is not None and body["command_id"] == pending["command_id"],
            "Current frozen intent required",
        )
        remaining = [i for i in pending["request"]["copy_ids"] if i not in pending["completed"]]
        if kind == "PROGRESS":
            require(
                set(request) == {"copy_id", "intent_sha256"}
                and remaining
                and request["copy_id"] == remaining[0]
                and request["intent_sha256"] == pending["intent_sha256"],
                "Ordered exact pending copy required",
            )
            observation = body["observation"]
            require(
                isinstance(observation, dict)
                and set(observation) == {"copy_id", "outcome"}
                and observation["copy_id"] == remaining[0]
                and observation["outcome"]
                in {"UNLINKED_VERIFIED_OWNED_INODE", "MISSING_AFTER_RETAINED_INTENT"},
                "Exact factual copy observation required",
            )
            if observation["outcome"] == "UNLINKED_VERIFIED_OWNED_INODE":
                _eligible(cfg, state, pending["request"]["authorization_id"], remaining[0], at)
            after["copies"][remaining[0]]["status"] = _copy_status(observation["outcome"])
            after["pending"]["completed"][remaining[0]] = observation["outcome"]
        elif kind == "FAILURE":
            require(
                request == {"intent_sha256": pending["intent_sha256"]},
                "Exact failed intent required",
            )
            observation = body["observation"]
            require(
                isinstance(observation, dict)
                and set(observation) == {"status", "error_type", "filesystem_rollback"}
                and observation["status"] == "FAILED_OR_BLOCKED_EXPLICIT_RETRY_REQUIRED"
                and observation["filesystem_rollback"] == "NOT_ASSUMED"
                and isinstance(observation["error_type"], str)
                and len(observation["error_type"]) <= 128,
                "Exact failure observation required",
            )
        else:
            require(
                kind == "FINISH"
                and not remaining
                and encoded(request) == encoded(pending["request"]),
                "Only completed frozen intent may finish",
            )
            after["pending"] = None
            observation = _completion(pending)
    require(
        encoded(after) == encoded(body["after"])
        and encoded(observation) == encoded(body["observation"]),
        "Recorded transition differs from exact retained authority/intent",
    )
    return after


def _load(db, cfg):
    _preflight(db, "systems", dict.fromkeys(("company", "branch", "system", "owner"), 128), 2)
    _preflight(db, "versions", NATIVE_LIMITS, MAX_EVENTS + 1)
    _preflight(
        db,
        "disposal_events",
        {
            "seq": 16,
            "kind": 32,
            "command_id": 128,
            "body": 256 * 1024,
            "sha256": 64,
            "native_pin": 1024,
        },
        MAX_EVENTS,
    )
    _preflight(db, "disposal_state", {"revision": 16, "last_at": 64, "state": 256 * 1024}, 1)
    systems = db.execute("SELECT company,branch,system,owner FROM systems").fetchall()
    require(
        {tuple(r) for r in systems}
        == {
            (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], name, cfg["operator_id"])
            for name in ("disposal_definition", "disposal_operation")
        },
        "Exact registered runtime owner systems required",
    )
    initial = {
        "copies": {k: {"status": "PRESENT", "holds": v["holds"]} for k, v in cfg["copies"].items()},
        "authorizations": {},
        "pending": None,
    }
    rows = db.execute("SELECT * FROM disposal_events ORDER BY seq").fetchall()
    require(len(rows) <= MAX_EVENTS, "Disposal event quota exceeded")
    state, previous, at = initial, None, cfg["initialized_at"]
    receipts = {}
    command_ids = set()
    definition = db.execute("SELECT * FROM versions WHERE system='disposal_definition'").fetchall()
    require(len(definition) == 1, "Exact native definition required")
    _validate_native(
        definition[0], cfg, "disposal_definition", "DEFINITION", encoded(cfg), cfg["initialized_at"]
    )
    for index, row in enumerate(rows, 1):
        body = decode(row["body"])
        require(
            isinstance(body, dict)
            and set(body)
            == {
                "kind",
                "command_id",
                "event_at",
                "previous_sha256",
                "before_sha256",
                "after",
                "input",
                "observation",
                "qualification",
            }
            and body["qualification"] == QUALIFICATION
            and body["kind"] in {"CONTROL", "INTENT", "PROGRESS", "FAILURE", "FINISH"},
            "Typed disposal event required",
        )
        require(
            row["seq"] == index
            and sha(encoded(body)) == row["sha256"]
            and body["previous_sha256"] == previous
            and body["before_sha256"] == sha(encoded(state))
            and body["event_at"] >= at
            and body["kind"] == row["kind"]
            and body["command_id"] == row["command_id"],
            "Disposal journal chain differs",
        )
        original = native(db, decode(row["native_pin"]))
        require(original["content"] == encoded(body), "Retained event differs from native original")
        _validate_native(
            original, cfg, "disposal_operation", f"EVENT-{index}", encoded(body), body["event_at"]
        )
        if body["kind"] in {"CONTROL", "INTENT"}:
            require(body["command_id"] not in command_ids, "Duplicate command identity")
            command_ids.add(body["command_id"])
        state = _transition(cfg, state, body, index - 1)
        require(
            set(state) == {"copies", "authorizations", "pending"}
            and set(state["copies"]) == set(cfg["copies"]),
            "Disposal state inventory differs",
        )
        previous, at = row["sha256"], body["event_at"]
        if row["kind"] in {"CONTROL", "FINISH"}:
            receipts[row["command_id"]] = body
    current = db.execute("SELECT * FROM disposal_state").fetchall()
    require(
        len(current) == 1
        and current[0]["revision"] == len(rows)
        and current[0]["last_at"] == at
        and encoded(decode(current[0]["state"])) == encoded(state),
        "Local state differs from retained events",
    )
    require(
        db.execute("SELECT count(*) FROM versions").fetchone()[0] == len(rows) + 1,
        "Native/event counts differ",
    )
    return state, len(rows), at, previous, receipts


def _append(db, cfg, state, revision, previous, kind, command, at, after, input_value, observation):
    require(revision < MAX_EVENTS, "Disposal event quota exceeded")
    if state["pending"] is not None and kind in {"CONTROL", "FAILURE"}:
        remaining = len(state["pending"]["expected"]) - len(state["pending"]["completed"])
        require(revision + remaining + 2 < MAX_EVENTS, "Reserve pending completion capacity")
    body = {
        "kind": kind,
        "command_id": command,
        "event_at": at,
        "previous_sha256": previous,
        "before_sha256": sha(encoded(state)),
        "after": after,
        "input": input_value,
        "observation": observation,
        "qualification": QUALIFICATION,
    }
    _transition(cfg, state, body, revision)
    ref = _insert(db, cfg, f"EVENT-{revision + 1}", body, at)
    db.execute(
        "INSERT INTO disposal_events VALUES(?,?,?,?,?,?)",
        (revision + 1, kind, command, _json(body), sha(encoded(body)), _json(ref)),
    )
    db.execute(
        "UPDATE disposal_state SET revision=?,last_at=?,state=?", (revision + 1, at, _json(after))
    )
    _preflight(
        db,
        "disposal_events",
        {
            "seq": 16,
            "kind": 32,
            "command_id": 128,
            "body": 256 * 1024,
            "sha256": 64,
            "native_pin": 1024,
        },
        MAX_EVENTS,
    )
    _preflight(db, "disposal_state", {"revision": 16, "last_at": 64, "state": 256 * 1024}, 1)
    return {
        "revision": revision + 1,
        "event_sha256": sha(encoded(body)),
        "native_pin": ref,
        "observation": observation,
    }


def _current(root, cfg, expected, at):
    require(
        _config(root, expected) == cfg
        and _declaration(
            Path(cfg["declaration_root"]), cfg["declaration_pin"], at, with_metadata=True
        )
        == (cfg["plan"], cfg["declaration_metadata_sha256"]),
        "Definition/declaration changed",
    )


def _control_state(cfg, state, action, payload, at):
    require(isinstance(payload, dict), "Typed control payload required")
    after = deepcopy(state)
    if action == "HOLD":
        require(
            set(payload) == {"copy_id", "hold_id", "active", "rationale"}
            and type(payload["active"]) is bool,
            "Exact local hold fields required",
        )
        _text(payload["rationale"])
        _id(payload["hold_id"])
        require(payload["copy_id"] in after["copies"], "Declared copy required")
        holds = set(after["copies"][payload["copy_id"]]["holds"])
        if payload["active"]:
            holds.add(payload["hold_id"])
        else:
            holds.discard(payload["hold_id"])
        require(len(holds) <= 16, "Local hold limit exceeded")
        after["copies"][payload["copy_id"]]["holds"] = sorted(holds)
    elif action == "AUTHORIZE":
        require(
            set(payload) == {"authorization_id", "copy_ids", "expires_at", "rationale"},
            "Exact local authorization fields required",
        )
        _id(payload["authorization_id"])
        _text(payload["rationale"])
        selected = payload["copy_ids"]
        require(
            isinstance(selected, list)
            and 1 <= len(selected) <= 32
            and all(isinstance(x, str) for x in selected)
            and len(set(selected)) == len(selected)
            and set(selected) <= set(cfg["copies"]),
            "Exact distinct declared copy selection required",
        )
        end = _time(payload["expires_at"])
        require(
            at < end and payload["authorization_id"] not in after["authorizations"],
            "Fresh future local authorization required",
        )
        after["authorizations"][payload["authorization_id"]] = {
            "copy_ids": selected,
            "expires_at": end,
            "issued_at": at,
            "rationale": payload["rationale"],
        }
    elif action == "ABORT_PENDING":
        require(
            set(payload) == {"rationale"} and after["pending"] is not None,
            "Existing pending operation required",
        )
        _text(payload["rationale"])
        after["pending"] = None
    else:
        raise CompanyStoreError("Unsupported disposal control action")
    return after


def control(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    operator_id,
    action,
    payload,
    event_at,
):
    """Explicit local holds/authorization; holds can change while disposal is pending."""
    _id(command_id)
    _id(operator_id)
    require(type(expected_revision) is int and expected_revision >= 0, "Exact revision required")
    at = _time(event_at)
    payload = decode(encoded(payload))
    request = {
        "action": action,
        "payload": payload,
        "operator_id": operator_id,
        "event_at": at,
        "expected_revision": expected_revision,
    }
    with _locked(runtime, expected_runtime_sha256) as (root, cfg):
        require(operator_id == cfg["operator_id"], "Scoped local operator required")
        with database(root, True) as db:
            state, rev, last, prev, receipts = _load(db, cfg)
            if command_id in receipts:
                require(
                    encoded(receipts[command_id]["input"]) == encoded(request),
                    "Changed control replay",
                )
                _current(root, cfg, expected_runtime_sha256, at)
                return receipts[command_id]["observation"]
            _fresh_command(db, command_id)
            require(rev == expected_revision and at >= last, "Stale revision or backwards time")
            after = _control_state(cfg, state, action, payload, at)
            observation = {
                "status": "LOCAL_CONTROL_RECORDED",
                "action": action,
                "qualification": QUALIFICATION,
            }
            result = _append(
                db, cfg, state, rev, prev, "CONTROL", command_id, at, after, request, observation
            )
            _current(root, cfg, expected_runtime_sha256, at)
        return result["observation"]


def _eligible(cfg, state, authorization, copy_id, at):
    auth = state["authorizations"].get(authorization)
    require(
        auth is not None
        and copy_id in auth["copy_ids"]
        and auth["issued_at"] <= at < auth["expires_at"],
        "Current explicit local authorization required",
    )
    require(
        not state["copies"][copy_id]["holds"] and at >= cfg["copies"][copy_id]["not_before"],
        "Current hold or local retention date blocks disposal",
    )


def _unlink_owned(fd, name, quarantine, expected):
    """Only a verified original inode is unlinked; a replacement is never adopted."""
    staged = _read_file(fd, quarantine)
    present = _read_file(fd, name)
    if staged is None and present is None:
        return "MISSING_AFTER_RETAINED_INTENT"
    require(staged is None or present is None, "Replacement copy exists beside staged original")
    if staged is None:
        require(present == expected, "Owned copy identity or bytes changed")
        os.rename(name, quarantine, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
        staged = _read_file(fd, quarantine)
    require(staged == expected, "Staged copy differs; preserved for inspection")
    require(_read_file(fd, name) is None, "Replacement copy blocks pending unlink")
    os.unlink(quarantine, dir_fd=fd)
    os.fsync(fd)
    return "UNLINKED_VERIFIED_OWNED_INODE"


def dispose(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    operator_id,
    authorization_id,
    copy_ids,
    event_at,
):
    """Freeze exact identities durably before any unlink; errors leave a pending intent."""
    _id(command_id)
    _id(operator_id)
    _id(authorization_id)
    require(
        type(expected_revision) is int and expected_revision >= 0,
        "Exact expected revision required",
    )
    require(
        isinstance(copy_ids, list)
        and all(isinstance(x, str) for x in copy_ids)
        and 1 <= len(copy_ids) <= 32
        and len(set(copy_ids)) == len(copy_ids),
        "Distinct exact copy selection required",
    )
    at = _time(event_at)
    request = {
        "expected_revision": expected_revision,
        "operator_id": operator_id,
        "authorization_id": authorization_id,
        "copy_ids": list(copy_ids),
        "event_at": at,
    }
    with _locked(runtime, expected_runtime_sha256) as (root, cfg):
        require(operator_id == cfg["operator_id"], "Explicit scoped local operator required")
        with database(root, True) as db:
            state, rev, last, prev, receipts = _load(db, cfg)
            if command_id in receipts:
                require(
                    encoded(receipts[command_id]["input"]) == encoded(request),
                    "Changed completed disposal replay",
                )
                _current(root, cfg, expected_runtime_sha256, at)
                return receipts[command_id]["observation"]
            _fresh_command(db, command_id)
            require(rev + len(copy_ids) + 3 <= MAX_EVENTS, "Reserve disposal completion capacity")
            require(
                state["pending"] is None and rev == expected_revision and at >= last,
                "Pending disposal, stale revision or backwards time",
            )
            expected = {}
            with _directory(root, cfg) as fd:
                for copy_id in copy_ids:
                    require(
                        copy_id in cfg["copies"]
                        and state["copies"][copy_id]["status"] == "PRESENT",
                        "Existing undisposed declared copy required",
                    )
                    _eligible(cfg, state, authorization_id, copy_id, at)
                    info = _read_file(fd, cfg["copies"][copy_id]["file"])
                    require(
                        info == cfg["copies"][copy_id]["identity"],
                        "Exact original fixture inode required",
                    )
                    expected[copy_id] = info
            pending = {
                "command_id": command_id,
                "request": request,
                "expected": expected,
                "completed": {},
            }
            pending["intent_sha256"] = sha(encoded(pending))
            after = deepcopy(state)
            after["pending"] = pending
            _append(
                db,
                cfg,
                state,
                rev,
                prev,
                "INTENT",
                command_id,
                at,
                after,
                request,
                {"status": "PENDING_EXPLICIT_LOCAL_UNLINK"},
            )
            _current(root, cfg, expected_runtime_sha256, at)
        return _continue(root, cfg, expected_runtime_sha256, at)


def _continue(root, cfg, expected_runtime_sha256, at):
    try:
        return _continue_inner(root, cfg, expected_runtime_sha256, at)
    except (CompanyStoreError, OSError) as exc:
        with database(root, True) as db:
            state, rev, last, prev, _ = _load(db, cfg)
            if state["pending"] is not None and at >= last and rev < MAX_EVENTS:
                pending = state["pending"]
                _append(
                    db,
                    cfg,
                    state,
                    rev,
                    prev,
                    "FAILURE",
                    pending["command_id"],
                    at,
                    state,
                    {"intent_sha256": pending["intent_sha256"]},
                    {
                        "status": "FAILED_OR_BLOCKED_EXPLICIT_RETRY_REQUIRED",
                        "error_type": type(exc).__name__,
                        "filesystem_rollback": "NOT_ASSUMED",
                    },
                )
        raise


def _continue_inner(root, cfg, expected_runtime_sha256, at):
    while True:
        with database(root, True) as db:
            state, rev, last, prev, _ = _load(db, cfg)
            pending = state["pending"]
            require(
                pending is not None and at >= last,
                "Exact pending disposal and current time required",
            )
            frozen = {k: v for k, v in pending.items() if k not in {"intent_sha256", "completed"}}
            frozen["completed"] = {}
            require(
                sha(encoded(frozen)) == pending["intent_sha256"], "Frozen intent identity differs"
            )
            remaining = [x for x in pending["request"]["copy_ids"] if x not in pending["completed"]]
            _current(root, cfg, expected_runtime_sha256, at)
            if not remaining:
                after = deepcopy(state)
                after["pending"] = None
                result = _completion(pending)
                _append(
                    db,
                    cfg,
                    state,
                    rev,
                    prev,
                    "FINISH",
                    pending["command_id"],
                    at,
                    after,
                    pending["request"],
                    result,
                )
                _current(root, cfg, expected_runtime_sha256, at)
                return result
            copy_id = remaining[0]
            require(
                pending["expected"][copy_id] == cfg["copies"][copy_id]["identity"],
                "Intent cannot adopt replacement copy",
            )
            # Unlink cannot roll back with SQLite. INTENT is already durable.
            with _directory(root, cfg) as fd:
                name = cfg["copies"][copy_id]["file"]
                quarantine = (
                    "pending-" + sha((pending["intent_sha256"] + copy_id).encode()) + ".bin"
                )
                if _read_file(fd, name) is not None or _read_file(fd, quarantine) is not None:
                    _eligible(cfg, state, pending["request"]["authorization_id"], copy_id, at)
                outcome = _unlink_owned(fd, name, quarantine, pending["expected"][copy_id])
            after = deepcopy(state)
            after["copies"][copy_id]["status"] = _copy_status(outcome)
            after["pending"]["completed"][copy_id] = outcome
            _append(
                db,
                cfg,
                state,
                rev,
                prev,
                "PROGRESS",
                pending["command_id"],
                at,
                after,
                {"copy_id": copy_id, "intent_sha256": pending["intent_sha256"]},
                {"copy_id": copy_id, "outcome": outcome},
            )
            _current(root, cfg, expected_runtime_sha256, at)


def retry_pending(
    runtime, *, expected_runtime_sha256, expected_revision, intent_sha256, operator_id, retry_at
):
    """No new selection. Current hold, authorization expiry and inode rechecked per copy."""
    require(type(expected_revision) is int and expected_revision >= 0, "Exact revision required")
    at = _time(retry_at)
    with _locked(runtime, expected_runtime_sha256) as (root, cfg):
        require(operator_id == cfg["operator_id"], "Explicit local operator required")
        with database(root) as db:
            state, rev, last, _, _ = _load(db, cfg)
            require(
                rev == expected_revision
                and state["pending"] is not None
                and state["pending"]["intent_sha256"] == intent_sha256
                and at > last,
                "Exact current pending intent and fresh retry time required",
            )
        return _continue(root, cfg, expected_runtime_sha256, at)


def inspect(runtime, *, expected_runtime_sha256, as_of):
    at = _time(as_of)
    with _locked(runtime, expected_runtime_sha256) as (root, cfg):
        with database(root) as db:
            state, rev, last, _, _ = _load(db, cfg)
        require(at >= last, "Current or later inspection cutoff required")
        inventory = []
        with _directory(root, cfg) as fd:
            for copy_id, entry in cfg["copies"].items():
                actual = _read_file(fd, entry["file"])
                inventory.append(
                    {
                        "id": copy_id,
                        "kind": entry["kind"],
                        "recorded_status": state["copies"][copy_id]["status"],
                        "path_present": actual is not None,
                        "matches_initial_identity": actual == entry["identity"],
                        "holds": state["copies"][copy_id]["holds"],
                        "not_before": entry["not_before"],
                    }
                )
            actual_names = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    require(len(actual_names) < 128, "Bounded owned directory inventory required")
                    actual_names.append(entry.name)
            actual_names.sort()
        _current(root, cfg, expected_runtime_sha256, at)
        return {
            "revision": rev,
            "pending": state["pending"],
            "inventory": inventory,
            "declared_inventory_count": len(inventory),
            "present_declared_paths": sum(x["path_present"] for x in inventory),
            "recorded_unattributed_missing_count": sum(
                x["recorded_status"] == "MISSING_UNATTRIBUTED" for x in inventory
            ),
            "recorded_unlinked_count": sum(x["recorded_status"] == "UNLINKED" for x in inventory),
            "retained_internal_files": actual_names,
            "qualification": QUALIFICATION,
            "secure_erasure": "NOT_ASSERTED",
            "enterprise_copy_completeness": "NOT_ESTABLISHED",
        }
