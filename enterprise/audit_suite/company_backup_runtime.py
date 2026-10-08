"""Bounded local byte operations tied to one exact operating-period declaration.

Trusted local operator API, not an authorization endpoint. No network, automatic
cadence, deletion, audit work or assurance conclusions. All native rows for an
operation commit together; interrupted private files are never catalogued.
"""

import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .company_operating_period import SYSTEM as PERIOD_SYSTEM
from .company_operating_period import _plan
from .company_store import CompanyStore, CompanyStoreError, _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_BYTE_BACKUP_RUNTIME_NOT_DEPLOYMENT_OR_BIA_ACCEPTANCE"
FIELDS = ("company", "branch", "system", "record", "version", "sha256")
MAX_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
SYSTEMS = (
    "runtime_definition",
    "source_dataset",
    "credential_event",
    "backup_job",
    "backup_object",
    "restore_job",
    "restored_dataset",
    "restore_use_contract",
    "restore_use_probe",
    "failure_ticket",
)


def require(condition, message):
    if not condition:
        raise CompanyStoreError(message)


def private(path, directory=False):
    path = Path(path)
    require(
        path.is_absolute() and ".." not in path.parts and path == path.resolve(),
        "Canonical absolute private path required",
    )
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Aliases forbidden")
    info = path.stat()
    require(
        (path.is_dir() if directory else path.is_file() and info.st_nlink == 1)
        and info.st_uid == os.getuid()
        and not info.st_mode & 0o077,
        "Owned private source required",
    )
    return path


def checked_bytes(path, limit=MAX_BYTES):
    path = private(path)
    before = path.stat()
    require(before.st_size <= limit, "Local byte limit exceeded")
    raw = path.read_bytes()
    after = path.stat()
    require(
        (before.st_dev, before.st_ino, before.st_ctime_ns, before.st_size, before.st_mode)
        == (after.st_dev, after.st_ino, after.st_ctime_ns, after.st_size, after.st_mode),
        "Source changed while reading",
    )
    return raw


@contextmanager
def database(root, write=False):
    root = private(root, True)
    path = private(root / "company.sqlite3")
    db = sqlite3.connect(
        path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=10
    )
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        if not write:
            db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def pin(row):
    return {k: row[k] for k in FIELDS}


def exact_pin(value):
    require(
        isinstance(value, dict) and set(value) == set(FIELDS), "Exact native six-field pin required"
    )
    for k in FIELDS[:4]:
        _id(value[k])
    require(
        type(value["version"]) is int
        and value["version"] > 0
        and isinstance(value["sha256"], str)
        and len(value["sha256"]) == 64
        and all(c in "0123456789abcdef" for c in value["sha256"]),
        "Exact version and hash required",
    )


def native(db, ref, at=None):
    exact_pin(ref)
    row = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? AND "
        "record=? AND version=?",
        tuple(ref[k] for k in FIELDS[:-1]),
    ).fetchone()
    require(
        row is not None and row["sha256"] == ref["sha256"] and sha(row["content"]) == ref["sha256"],
        "Native source pin or bytes differ",
    )
    require(
        at is None
        or (row["event_at"] is not None and row["event_at"] <= at and row["available_at"] <= at),
        "Future or undated source unavailable",
    )
    return dict(row)


def _insert(db, config, system, record, raw, at, command_id, *, source_admission=None):
    require(
        isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES,
        "Bounded nonempty source bytes required",
    )
    require(
        db.execute("SELECT COALESCE(SUM(length(content)),0) FROM versions").fetchone()[0] + len(raw)
        <= MAX_TOTAL_BYTES,
        "Runtime native byte quota exceeded",
    )
    require(
        db.execute("SELECT count(*) FROM versions").fetchone()[0] < 20000,
        "Runtime record bound reached",
    )
    key = [config["plan"]["company_id"], config["plan"]["branch_id"], system, _id(record)]
    prior = db.execute(
        "SELECT COALESCE(MAX(version),0) FROM versions WHERE company=? AND "
        "branch=? AND system=? AND record=?",
        key,
    ).fetchone()[0]
    provenance = {
        "source_reference": config["plan"]["period_id"],
        "classification": QUALIFICATION,
        "control_ids": ["SH-BCM-002", "SH-BCM-003"],
        "declaration": config["declaration_ref"],
        "runtime_id": config["runtime_id"],
    }
    dataset_id = (
        record
        if system == "source_dataset"
        else (
            config["bindings"][record]["dataset_id"]
            if system in {"backup_object", "restored_dataset"}
            else None
        )
    )
    json_native = dataset_id is None or config["datasets"][dataset_id] == "JSON_RECORDS"
    provenance.update(
        name=record + (".json" if json_native else ".bin"),
        content_type="application/json" if json_native else "application/octet-stream",
    )
    if source_admission is not None:
        require(isinstance(source_admission, dict), "Typed source admission required")
        provenance["source_admission"] = source_admission
    content_sha = sha(raw)
    fingerprint = sha(
        _json([key, prior, at, at, "AUTHORED_TRAINING_SOURCE", provenance, content_sha]).encode()
    )
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            *key,
            prior + 1,
            at,
            at,
            _now(),
            "AUTHORED_TRAINING_SOURCE",
            _json(provenance),
            raw,
            content_sha,
            _id(command_id),
            fingerprint,
        ),
    )
    return dict(zip(FIELDS, (*key, prior + 1, content_sha), strict=True))


def _config(root, expected):
    raw = checked_bytes(Path(root) / "RUNTIME.json", 2 * 1024 * 1024)
    require(sha(raw) == expected, "Runtime definition hash differs")
    return decode(raw)


def _criterion_check(cfg, at):
    if "local_data_loss_criterion" in cfg:
        from .company_backup_criterion import check

        check(cfg, at)


def _bound_config(db, cfg, expected):
    rows = db.execute("SELECT * FROM versions WHERE system='runtime_definition'").fetchall()
    require(len(rows) == 1, "Exactly one native runtime definition required")
    row = rows[0]
    require(
        (row["company"], row["branch"], row["record"], row["version"])
        == (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], cfg["plan"]["period_id"], 1)
        and row["sha256"] == expected
        and sha(row["content"]) == expected
        and decode(row["content"]) == cfg,
        "Immutable native runtime definition differs",
    )


def initialize(
    destination,
    *,
    repository,
    declaration_root,
    declaration_ref,
    bindings,
    datasets,
    service_id="SVC-compute",
    local_data_loss_criterion=None,
):
    """Bind exactly all declaration slots; copy no authority or ledger execution assertions."""
    destination, repository = Path(destination), Path(repository)
    private(destination.parent, True)
    require(
        destination.is_absolute()
        and ".." not in destination.parts
        and not destination.exists()
        and not destination.is_symlink(),
        "New absolute private runtime required",
    )
    source = private(declaration_root, True)
    require(
        not destination.resolve().is_relative_to(source)
        and not source.is_relative_to(destination.resolve()),
        "Runtime and declaration roots must be separate",
    )
    with database(source) as db:
        row = native(db, declaration_ref)
    require(
        row["system"] == PERIOD_SYSTEM and row["version"] == 1,
        "Original operating-period declaration required",
    )
    body = decode(row["content"])
    require(body.get("kind") == "PERIOD_DECLARATION", "Exact period declaration required")
    plan = _plan(body["plan"])
    require(
        (row["company"], row["branch"], row["record"], row["event_at"], row["available_at"])
        == (
            plan["company_id"],
            plan["branch_id"],
            plan["period_id"],
            plan["declared_at"],
            plan["declared_at"],
        ),
        "Declaration identity or chronology differs",
    )
    require(
        isinstance(datasets, list) and 1 <= len(datasets) <= 64,
        "Explicit bounded dataset inventory required",
    )
    inventory = {r["id"] for r in plan["inventory"]}
    dataset_map = {}
    for item in datasets:
        require(
            isinstance(item, dict) and set(item) == {"id", "format"},
            "Exact dataset fields required",
        )
        _id(item["id"])
        require(
            item["id"] in inventory
            and item["id"] not in dataset_map
            and item["format"] in ("JSON_RECORDS", "BYTES"),
            "Dataset must match declared inventory once",
        )
        dataset_map[item["id"]] = item["format"]
    require(
        set(dataset_map) == inventory,
        "Every declared inventory item requires its explicit dataset binding",
    )
    slots = {s["id"]: s for s in plan["schedule"]}
    require(
        isinstance(bindings, list) and len(bindings) == len(slots),
        "Bind every declared occurrence explicitly",
    )
    bound = {}
    for b in bindings:
        require(
            isinstance(b, dict) and set(b) == {"occurrence_id", "dataset_id", "operation"},
            "Exact backup/restore binding required",
        )
        _id(b["occurrence_id"])
        _id(b["dataset_id"])
        require(
            b["occurrence_id"] in slots
            and b["occurrence_id"] not in bound
            and b["dataset_id"] in dataset_map
            and b["operation"] in ("BACKUP", "RESTORE"),
            "Invalid or repeated occurrence binding",
        )
        slot = slots[b["occurrence_id"]]
        require(
            slot["inventory_ids"] == [b["dataset_id"]]
            and slot["control_id"]
            == ("SH-BCM-002" if b["operation"] == "BACKUP" else "SH-BCM-003"),
            "Occurrence control and exact dataset differ",
        )
        bound[b["occurrence_id"]] = dict(b)
    services_path = repository / "enterprise/services/source/services.json"
    require(
        service_id == "SVC-compute"
        and any(r[0] == service_id for r in decode(services_path.read_bytes())["services"]),
        "Canonical reference compute service required",
    )
    org = snapshot(repository, as_of=plan["period_start"][:10])
    assignments = {r["control_id"]: r for r in org["control_assignments"]}
    operator = assignments["SH-BCM-003"]["primary_person_id"]
    reviewer = assignments["SH-BCM-003"]["operating_reviewer_person_id"]
    require(operator != reviewer, "Distinct operating restore/review contacts required")
    pins = dict(org["source_sha256"])
    for relative in (
        "enterprise/audit_suite/company_backup_runtime.py",
        "enterprise/audit_suite/company_backup_use_probe.py",
        "enterprise/audit_suite/company_store.py",
        "enterprise/audit_suite/company_operating_period.py",
        "enterprise/audit_suite/inference.py",
        "enterprise/services/source/services.json",
        "enterprise/services/source/runtime_sites_2026-09-11.json",
        "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
    ):
        pins[relative] = sha((repository / relative).read_bytes())
    config = {
        "schema": "LOCAL_BACKUP_RUNTIME_V1",
        "runtime_id": "BACKUP-" + uuid4().hex,
        "plan": plan,
        "declaration_ref": declaration_ref,
        "declaration_location_sha256": sha(str(source).encode()),
        "declaration_original_sha256": sha(row["content"]),
        "bindings": bound,
        "datasets": dataset_map,
        "service_id": service_id,
        "operator_id": operator,
        "operating_reviewer_id": reviewer,
        "source_sha256": pins,
        "qualification": QUALIFICATION,
        "targets": "NOT_SUPPLIED_NO_APPROVED_BIA_OR_RPO_RTO_ASSERTED",
        "deployment": "NOT_ESTABLISHED",
    }
    if local_data_loss_criterion is not None:
        from .company_backup_criterion import resolve

        require(
            isinstance(local_data_loss_criterion, dict)
            and isinstance(local_data_loss_criterion.get("root"), str),
            "Explicit local criterion dependency required",
        )
        criterion_root = private(Path(local_data_loss_criterion["root"]), True)
        require(
            not destination.resolve().is_relative_to(criterion_root)
            and not criterion_root.is_relative_to(destination.resolve()),
            "Runtime and criterion roots must be separate",
        )
        config["local_data_loss_criterion"] = resolve(
            local_data_loss_criterion,
            scope={"service_id": service_id, "dataset_ids": sorted(dataset_map)},
            plan=plan,
            author=operator,
            reviewer=reviewer,
            as_of=plan["declared_at"],
        )
        name = "enterprise/audit_suite/company_backup_criterion.py"
        pins[name] = sha((repository / name).read_bytes())
        name = "enterprise/audit_suite/company_backup_monitor.py"
        pins[name] = sha((repository / name).read_bytes())
        _criterion_check(config, plan["declared_at"])
    with tempfile.TemporaryDirectory(
        prefix=".backup-runtime-", dir=destination.parent
    ) as directory:
        stage = Path(directory)
        store = CompanyStore(stage)
        with store._db() as db:
            db.executescript("""CREATE TABLE backup_runtime_state(
                    revision INTEGER NOT NULL,last_event_at TEXT NOT NULL);
                CREATE TABLE backup_runtime_commands(
                    command_id TEXT PRIMARY KEY,input_digest TEXT NOT NULL,receipt TEXT NOT NULL);
                CREATE TRIGGER backup_commands_no_update BEFORE UPDATE ON backup_runtime_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;
                CREATE TRIGGER backup_commands_no_delete BEFORE DELETE ON backup_runtime_commands
                    BEGIN SELECT RAISE(ABORT,'Immutable command'); END;""")
            db.execute("INSERT INTO backup_runtime_state VALUES(0,?)", (plan["declared_at"],))
        for system in SYSTEMS:
            store.register_system(
                plan["company_id"],
                plan["branch_id"],
                system,
                reviewer if system == "runtime_definition" else operator,
            )
        raw = encoded(config)
        for name, content in (("RUNTIME.json", raw), ("DECLARATION.json", row["content"])):
            with (stage / name).open("xb") as f:
                os.chmod(stage / name, 0o600)
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        (stage / "attempts").mkdir(mode=0o700)
        with database(stage, True) as db:
            _insert(
                db,
                config,
                "runtime_definition",
                plan["period_id"],
                raw,
                plan["declared_at"],
                "backup-runtime-definition-"
                + sha(encoded([config["runtime_id"], declaration_ref])),
            )
        with database(source) as db:
            require(
                native(db, declaration_ref)["content"] == row["content"],
                "Declaration changed before publication",
            )
        require(
            all(sha((repository / key).read_bytes()) == value for key, value in pins.items()),
            "Pinned definition sources changed before publication",
        )
        _criterion_check(config, plan["declared_at"])
        publish(stage, destination)
    return {
        "runtime_sha256": sha(raw),
        "declaration_ref": declaration_ref,
        "source_versions": 1,
        "operation_execution": "NOT_STARTED",
        "audit_created": False,
    }


def _records(raw):
    value = decode(raw)
    require(
        isinstance(value, dict)
        and set(value) == {"records"}
        and isinstance(value["records"], list)
        and len(value["records"]) <= 10000,
        "Bounded records object required",
    )
    rows = value["records"]
    require(
        all(isinstance(r, dict) and isinstance(r.get("id"), str) and r["id"] for r in rows)
        and len({r["id"] for r in rows}) == len(rows),
        "Unique explicit record IDs required",
    )
    return {r["id"]: r for r in rows}


def _latest(db, cfg, system, record, at):
    row = db.execute(
        "SELECT * FROM versions WHERE company=? AND branch=? AND system=? AND "
        "record=? AND available_at<=? ORDER BY version DESC LIMIT 1",
        (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], system, record, at),
    ).fetchone()

    require(row is None or sha(row["content"]) == row["sha256"], "Native history integrity failure")
    return row


def _selected(db, cfg, ref, system, record, at, latest=False):
    row = native(db, ref, at)
    require(
        row["company"] == cfg["plan"]["company_id"]
        and row["branch"] == cfg["plan"]["branch_id"]
        and row["system"] == system
        and row["record"] == record,
        "Wrong runtime source identity",
    )
    require(
        row["origin"] == "AUTHORED_TRAINING_SOURCE"
        and decode(row["provenance"]).get("runtime_id") == cfg["runtime_id"],
        "Source belongs to a different runtime definition",
    )
    if latest:
        current = _latest(db, cfg, system, record, at)
        require(
            current is not None and pin(current) == ref,
            "Source is no longer latest at operation instant",
        )
    return row


def _previous(db, cfg, system, record, ref, at):
    if ref is not None:
        exact_pin(ref)
    current = _latest(db, cfg, system, record, at)
    require(
        (ref is None and current is None) or (current is not None and ref == pin(current)),
        "Exact previous native pin required",
    )


def _execute(root, expected_runtime_sha256, expected_revision, command_id, at, payload, perform):
    root = Path(root)
    cfg = _config(root, expected_runtime_sha256)
    _id(command_id)
    require(
        type(expected_revision) is int and expected_revision >= 0,
        "Exact expected runtime revision required",
    )
    at = _time(at)
    _criterion_check(cfg, at)
    fingerprint = sha(
        encoded(
            {
                "runtime_sha256": expected_runtime_sha256,
                "expected_revision": expected_revision,
                "event_at": at,
                "payload": payload,
            }
        )
    )
    with database(root, True) as db:
        _bound_config(db, cfg, expected_runtime_sha256)
        prior = db.execute(
            "SELECT * FROM backup_runtime_commands WHERE command_id=?", (command_id,)
        ).fetchone()
        if prior:
            require(prior["input_digest"] == fingerprint, "Changed operation replay rejected")
            _criterion_check(cfg, at)
            return decode(prior["receipt"])
        revision, previous_at = db.execute(
            "SELECT revision,last_event_at FROM backup_runtime_state"
        ).fetchone()
        require(
            revision == expected_revision and at >= previous_at,
            "Stale revision or backward business timestamp",
        )
        require(
            db.execute("SELECT count(*) FROM versions").fetchone()[0] < 20000,
            "Runtime record bound reached",
        )
        result = perform(db, cfg, at)
        require(
            _config(root, expected_runtime_sha256) == cfg,
            "Runtime definition changed during operation",
        )
        _criterion_check(cfg, at)
        receipt = {
            "command_id": command_id,
            "revision": revision + 1,
            "event_at": at,
            "runtime_sha256": expected_runtime_sha256,
            "qualification": QUALIFICATION,
            **result,
        }
        db.execute(
            "INSERT INTO backup_runtime_commands VALUES(?,?,?)",
            (command_id, fingerprint, _json(receipt)),
        )
        db.execute("UPDATE backup_runtime_state SET revision=?,last_event_at=?", (revision + 1, at))
    return receipt


def append_dataset(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    dataset_id,
    content,
    expected_sha256,
    event_at,
    previous_pin=None,
):
    _id(dataset_id)
    require(
        isinstance(content, bytes)
        and 0 < len(content) <= MAX_BYTES
        and sha(content) == expected_sha256,
        "Exact bounded dataset bytes required",
    )

    def perform(db, cfg, at):
        require(dataset_id in cfg["datasets"], "Dataset not declared")
        if cfg["datasets"][dataset_id] == "JSON_RECORDS":
            _records(content)
        _previous(db, cfg, "source_dataset", dataset_id, previous_pin, at)
        ref = _insert(
            db,
            cfg,
            "source_dataset",
            dataset_id,
            content,
            at,
            "DATA-" + sha(command_id.encode())[:48],
        )
        return {"source_pin": ref, "status": "DATASET_RECORDED"}

    return _execute(
        runtime,
        expected_runtime_sha256,
        expected_revision,
        command_id,
        event_at,
        {
            "kind": "DATASET",
            "dataset_id": dataset_id,
            "sha256": expected_sha256,
            "previous_pin": previous_pin,
        },
        perform,
    )


def record_lease(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    operation,
    enabled,
    valid_from,
    expires_at,
    event_at,
    previous_pin=None,
):
    require(
        operation in ("BACKUP_WRITE", "RESTORE_READ") and type(enabled) is bool,
        "Typed local permission required",
    )
    valid_from, expires_at = _time(valid_from), _time(expires_at)
    require(valid_from < expires_at, "Positive half-open lease required")
    body = {
        "operation": operation,
        "enabled": enabled,
        "valid_from": valid_from,
        "expires_at": expires_at,
        "authority": "LOCAL_ADAPTER_ENFORCEMENT_NOT_CLOUD_CREDENTIAL_OR_PHYSICAL_ISOLATION",
    }

    def perform(db, cfg, at):
        _previous(db, cfg, "credential_event", operation, previous_pin, at)
        ref = _insert(
            db,
            cfg,
            "credential_event",
            operation,
            encoded({**body, "principal_id": cfg["operator_id"]}),
            at,
            "LEASE-" + sha(command_id.encode())[:48],
        )
        return {"lease_pin": ref, "status": "LOCAL_LEASE_RECORDED"}

    return _execute(
        runtime,
        expected_runtime_sha256,
        expected_revision,
        command_id,
        event_at,
        {"kind": "LEASE", **body, "previous_pin": previous_pin},
        perform,
    )


def _copy(root, command_id, raw, intent):
    """Anchor all writes to verified directory FDs; never follow a copy-parent alias."""
    parent = private(Path(root) / "attempts", True)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    folder_fd = None
    folder_name = sha(command_id.encode())
    try:
        parent_info = os.fstat(parent_fd)
        current = parent.stat()
        require(
            (parent_info.st_dev, parent_info.st_ino) == (current.st_dev, current.st_ino)
            and parent_info.st_uid == os.getuid()
            and not parent_info.st_mode & 0o077,
            "Private copy parent changed",
        )
        try:
            os.mkdir(folder_name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise CompanyStoreError(
                "Interrupted attempt files exist; inspect before an explicit new command"
            ) from exc
        folder_fd = os.open(
            folder_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        info = os.fstat(folder_fd)
        require(
            info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "Private attempt directory required",
        )

        def write_file(name, content):
            fd = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder_fd
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())

        write_file(
            "INTENT.json",
            encoded(
                {
                    "status": "INTENT_ONLY_NOT_COMPLETED",
                    "command_id": command_id,
                    "copy_sha256": sha(raw),
                    "copy_bytes": len(raw),
                    **intent,
                }
            ),
        )
        start = time.monotonic_ns()
        write_file("copied.bin", raw)
        os.fsync(folder_fd)
        os.fsync(parent_fd)
        fd = os.open("copied.bin", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder_fd)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            require(
                info.st_nlink == 1
                and info.st_uid == os.getuid()
                and not info.st_mode & 0o077
                and info.st_size <= MAX_BYTES,
                "Private copied original required",
            )
            copied = handle.read(MAX_BYTES + 1)
        require(copied == raw and sha(copied) == sha(raw), "Local copy integrity failure")
        now = private(parent, True).stat()
        folder = private(parent / folder_name, True).stat()
        opened = os.fstat(folder_fd)
        require(
            (now.st_dev, now.st_ino) == (parent_info.st_dev, parent_info.st_ino)
            and (folder.st_dev, folder.st_ino) == (opened.st_dev, opened.st_ino),
            "Copy directory identity changed",
        )
        return (
            copied,
            f"attempts/{folder_name}/copied.bin",
            (time.monotonic_ns() - start) / 1_000_000_000,
        )
    finally:
        if folder_fd is not None:
            os.close(folder_fd)
        os.close(parent_fd)


def _run(
    runtime,
    *,
    operation,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    occurrence_id,
    source_pin,
    lease_pin,
    attempted_at,
    prior_attempt_pin=None,
    comparison_source_pin=None,
    rationale,
):
    _id(occurrence_id)
    require(
        isinstance(rationale, str) and 1 <= len(rationale.strip()) <= 2000,
        "Explicit bounded operation rationale required",
    )

    def perform(db, cfg, at):
        binding = cfg["bindings"].get(occurrence_id)
        require(
            binding is not None and binding["operation"] == operation,
            "Exact typed occurrence required",
        )
        slot = next(s for s in cfg["plan"]["schedule"] if s["id"] == occurrence_id)
        require(at >= slot["window_start"], "Operation precedes declared occurrence window")
        dataset = binding["dataset_id"]
        system = "backup_job" if operation == "BACKUP" else "restore_job"
        _previous(db, cfg, system, occurrence_id, prior_attempt_pin, at)
        for dependency in slot["depends_on"]:
            dep = cfg["bindings"][dependency]
            row = _latest(
                db,
                cfg,
                "backup_job" if dep["operation"] == "BACKUP" else "restore_job",
                dependency,
                at,
            )
            require(
                row is not None and decode(row["content"])["status"] == "COMPLETED",
                "Missing or failed declared dependency",
            )
        permission = "BACKUP_WRITE" if operation == "BACKUP" else "RESTORE_READ"
        lease = decode(
            _selected(db, cfg, lease_pin, "credential_event", permission, at, latest=True)[
                "content"
            ]
        )
        require(
            isinstance(lease, dict)
            and set(lease)
            == {"operation", "enabled", "valid_from", "expires_at", "authority", "principal_id"}
            and type(lease["enabled"]) is bool
            and lease["operation"] == permission
            and lease["principal_id"] == cfg["operator_id"]
            and _time(lease["valid_from"]) == lease["valid_from"]
            and _time(lease["expires_at"]) == lease["expires_at"]
            and lease["valid_from"] < lease["expires_at"],
            "Malformed local lease record",
        )
        allowed = lease["enabled"] and lease["valid_from"] <= at < lease["expires_at"]
        result = {
            "occurrence_id": occurrence_id,
            "dataset_id": dataset,
            "operation": operation,
            "rationale": rationale,
            "runtime_id": cfg["runtime_id"],
            "source_pin": source_pin,
            "lease_pin": lease_pin,
            "prior_attempt_pin": prior_attempt_pin,
            "performed_by": cfg["operator_id"],
            "recorded_operating_review_contact": cfg["operating_reviewer_id"],
            "review_performed": False,
            "business_attempted_at": at,
            "actual_elapsed_seconds": None,
            "duration_basis": (
                "LOCAL_FILE_COPY_AND_REREAD_WALL_DURATION_SEPARATE_FROM_AUTHORED_TIME"
            ),
            "recording_timeliness": "AFTER_DUE" if at > slot["due_at"] else "BY_DUE",
            "status": "FAILED",
            "error_code": "LOCAL_LEASE_UNAVAILABLE" if not allowed else None,
            "qualification": QUALIFICATION,
            "copied_bytes": 0,
            "object_pin": None,
        }
        if operation == "BACKUP":
            source = _selected(db, cfg, source_pin, "source_dataset", dataset, at, latest=True)
            raw = source["content"]
        else:
            source = native(db, source_pin, at)
            require(
                source["company"] == cfg["plan"]["company_id"]
                and source["branch"] == cfg["plan"]["branch_id"]
                and source["system"] == "backup_object",
                "Exact local backup object required",
            )
            backup = _latest(db, cfg, "backup_job", source["record"], at)
            # Find the exact historical completed attempt that produced this object.
            candidates = db.execute(
                "SELECT content,sha256 FROM versions WHERE company=? AND branch=? AND "
                "system='backup_job' AND record=? AND available_at<=?",
                (source["company"], source["branch"], source["record"], at),
            ).fetchall()
            require(
                all(sha(r["content"]) == r["sha256"] for r in candidates),
                "Backup job history changed",
            )
            matches = [
                decode(r[0]) for r in candidates if decode(r[0]).get("object_pin") == source_pin
            ]
            require(
                backup is not None and len(matches) == 1 and matches[0]["dataset_id"] == dataset,
                "Backup catalogue identity mismatch",
            )
            comparison = _selected(
                db, cfg, comparison_source_pin, "source_dataset", dataset, at, latest=True
            )
            result["comparison_source_pin"] = comparison_source_pin
            result["checkpoint_age_seconds"] = (
                datetime.fromisoformat(at)
                - datetime.fromisoformat(native(db, matches[0]["source_pin"])["event_at"])
            ).total_seconds()
            raw = source["content"]
            if allowed:
                try:
                    disk = checked_bytes(Path(runtime) / matches[0]["copy_path"])
                    require(disk == raw, "Backup copy differs")
                except (OSError, CompanyStoreError):
                    allowed = False
                    result["error_code"] = "BACKUP_COPY_INTEGRITY_UNAVAILABLE"
        if allowed:
            copied, path, elapsed = _copy(
                Path(runtime),
                command_id,
                raw,
                {
                    "runtime_sha256": expected_runtime_sha256,
                    "expected_revision": expected_revision,
                    "operation": operation,
                    "occurrence_id": occurrence_id,
                    "source_pin": source_pin,
                    "lease_pin": lease_pin,
                    "comparison_source_pin": comparison_source_pin,
                    "prior_attempt_pin": prior_attempt_pin,
                    "rationale": rationale,
                },
            )
            ref = _insert(
                db,
                cfg,
                "backup_object" if operation == "BACKUP" else "restored_dataset",
                occurrence_id,
                copied,
                at,
                "COPY-" + sha(command_id.encode())[:48],
            )
            result.update(
                status="COMPLETED",
                object_pin=ref,
                copy_path=path,
                actual_elapsed_seconds=elapsed,
                copied_bytes=len(copied),
            )
            if operation == "RESTORE":
                result["byte_copy_matches_selected_backup"] = copied == source["content"]
                result["comparison_bytes_equal"] = copied == comparison["content"]
                if cfg["datasets"][dataset] == "JSON_RECORDS":
                    actual, expected = _records(copied), _records(comparison["content"])
                    result["content_reconciliation"] = {
                        "missing_ids": sorted(expected.keys() - actual.keys()),
                        "unexpected_ids": sorted(actual.keys() - expected.keys()),
                        "changed_ids": sorted(
                            k
                            for k in expected.keys() & actual.keys()
                            if encoded(expected[k]) != encoded(actual[k])
                        ),
                        "usability": (
                            "DECLARED_RECORD_EQUALITY_ONLY_NOT_PRODUCTION_APPLICATION_ACCEPTANCE"
                        ),
                    }
        ref = _insert(
            db,
            cfg,
            system,
            occurrence_id,
            encoded(result),
            at,
            "JOB-" + sha(command_id.encode())[:48],
        )
        if result["status"] == "FAILED":
            _insert(
                db,
                cfg,
                "failure_ticket",
                occurrence_id,
                encoded(
                    {
                        "job_pin": ref,
                        "error_code": result["error_code"],
                        "status": "OPEN_RECORDED_FAILURE_NOT_AUTOMATICALLY_CLOSED",
                    }
                ),
                at,
                "FAIL-" + sha(command_id.encode())[:48],
            )
        return {"job_pin": ref, "object_pin": result["object_pin"], "status": result["status"]}

    return _execute(
        runtime,
        expected_runtime_sha256,
        expected_revision,
        command_id,
        attempted_at,
        {
            "kind": operation,
            "rationale": rationale,
            "occurrence_id": occurrence_id,
            "source_pin": source_pin,
            "lease_pin": lease_pin,
            "prior_attempt_pin": prior_attempt_pin,
            "comparison_source_pin": comparison_source_pin,
        },
        perform,
    )


def run_backup(runtime, **kwargs):
    """Execute one declared backup attempt; no catch-up or implicit schedule expansion."""
    return _run(runtime, operation="BACKUP", **kwargs)


def run_restore(runtime, *, backup_pin, **kwargs):
    """Restore an exact historical backup, compare to an explicit current dataset pin."""
    return _run(runtime, operation="RESTORE", source_pin=backup_pin, **kwargs)


def reconcile(runtime, *, expected_runtime_sha256, as_of):
    """Independent expected-job census from declaration, not observed job membership."""
    cfg = _config(Path(runtime), expected_runtime_sha256)
    at = _time(as_of)
    _criterion_check(cfg, at)
    require(at >= cfg["plan"]["declared_at"], "Declaration not yet available")
    require(
        sha(checked_bytes(Path(runtime) / "DECLARATION.json", 2 * 1024 * 1024))
        == cfg["declaration_original_sha256"],
        "Retained declaration changed",
    )
    with database(Path(runtime)) as db:
        _bound_config(db, cfg, expected_runtime_sha256)
        rows = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system IN "
            "('backup_job','restore_job') AND available_at<=? ORDER BY record,version",
            (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], at),
        ).fetchall()
        require(
            sum(len(r["content"]) for r in rows) <= 64 * 1024 * 1024, "Bounded job census exceeded"
        )
        history = {}
        for row in rows:
            require(sha(row["content"]) == row["sha256"], "Job original changed")
            require(
                decode(row["provenance"]).get("runtime_id") == cfg["runtime_id"],
                "Job belongs to a different runtime definition",
            )
            history.setdefault(row["record"], []).append(
                {"job_pin": pin(row), **decode(row["content"])}
            )
    occurrences = []
    for slot in cfg["plan"]["schedule"]:
        jobs = history.get(slot["id"], [])
        latest = jobs[-1] if jobs else None
        occurrences.append(
            {
                "schedule": slot,
                "binding": cfg["bindings"][slot["id"]],
                "history": jobs,
                "state": latest["status"]
                if latest
                else ("MISSING_DUE" if at >= slot["due_at"] else "NOT_YET_DUE"),
                "is_due": at >= slot["due_at"],
                "prior_failed_attempts": sum(j["status"] == "FAILED" for j in jobs),
            }
        )
    _criterion_check(cfg, at)
    return {
        "declaration_ref": cfg["declaration_ref"],
        "runtime_sha256": expected_runtime_sha256,
        "qualification": QUALIFICATION,
        "as_of": at,
        "occurrences": occurrences,
        "unexpected_job_ids": sorted(set(history) - set(cfg["bindings"])),
        "declared_count": len(occurrences),
        "due_count": sum(o["is_due"] for o in occurrences),
        "missing_due_count": sum(o["state"] == "MISSING_DUE" for o in occurrences),
        "failed_occurrence_count": sum(o["state"] == "FAILED" for o in occurrences),
        "actual_copy_completed_count": sum(o["state"] == "COMPLETED" for o in occurrences),
        "whole_period_effectiveness": "NOT_ASSESSED",
        "approved_bia_targets": "NOT_ESTABLISHED",
        "population_acceptance": "NOT_PERFORMED",
        "native_history": "IMMUTABLE_RECORDS_NO_RETENTION_DELETION",
        "source_validation": "PINNED_DECLARATION_AND_RECORDED_JOBS_NOT_CURRENT_COPY_RETEST",
    }
