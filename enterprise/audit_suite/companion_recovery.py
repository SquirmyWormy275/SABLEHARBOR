"""Local operator companion recovery, separate from engagement/source/draft backups.

Each SQLite read transaction and locked log has its own capture timestamp. This is
not a globally atomic backup. Jobs restore as inert JSON, never an executable queue.
Hashes detect corruption, not a privileged operator rewriting a whole backup.
"""

import fcntl
import hashlib
import json
import os
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .instructor_access import MAX_LOG_BYTES, InstructorAccessLog
from .private_publication import publish
from .store import DomainError, canonical, digest
from .workspace_context import WorkspaceContexts

MAX_BYTES = 128 * 1024 * 1024
TABLES = {
    "contexts": {
        "contexts": ("id", "actor", "engagement", "version", "status", "content", "sha256"),
        "history": ("context", "version", "content", "sha256"),
        "commands": ("actor", "engagement", "command_id", "digest", "context", "version"),
    },
    "jobs": {
        "jobs": (
            "id",
            "actor",
            "engagement",
            "command_id",
            "command",
            "command_digest",
            "expected_revision",
            "status",
            "job_revision",
            "attempts",
            "created_at",
            "updated_at",
            "result_revision",
            "error_code",
        ),
        "transitions": ("job", "revision", "status", "error_code", "recorded_at"),
    },
}


def _private(path, directory=False):
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise DomainError("Recovery aliases forbidden")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise DomainError("Private regular recovery data required")


def _new(path):
    path = Path(path).absolute()
    _private(path.parent, True)
    if path.exists() or path.is_symlink():
        raise DomainError("New recovery destination required")
    return path


def _write(path, raw):
    if len(raw) > MAX_BYTES:
        raise DomainError("Companion size limit exceeded", status=413)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _read(path):
    _private(path)
    if path.stat().st_size > MAX_BYTES:
        raise DomainError("Companion size limit exceeded", status=413)
    return path.read_bytes()


def _json(value):
    return canonical(value).encode()


def _validate(kind, body):
    if set(body) != {"captured_at", "tables"} or set(body["tables"]) != set(TABLES[kind]):
        raise DomainError("Invalid companion schema")
    tables = body["tables"]
    for table, columns in TABLES[kind].items():
        if not isinstance(tables[table], list) or any(
            not isinstance(row, dict) or set(row) != set(columns) for row in tables[table]
        ):
            raise DomainError("Invalid companion table")
    if kind == "contexts":
        history = {}
        for row in tables["history"]:
            key = (row["context"], row["version"])
            content = json.loads(row["content"])
            if (
                key in history
                or digest(content) != row["sha256"]
                or content["id"] != row["context"]
                or content["version"] != row["version"]
            ):
                raise DomainError("Context history integrity failure")
            history[key] = row
        current = {}
        for row in tables["contexts"]:
            key = (row["id"], row["version"])
            record = history.get(key)
            if (
                row["id"] in current
                or record is None
                or record["content"] != row["content"]
                or record["sha256"] != row["sha256"]
                or json.loads(row["content"])["status"] != row["status"]
            ):
                raise DomainError("Context head integrity failure")
            versions = sorted(version for identifier, version in history if identifier == row["id"])
            if versions != list(range(1, row["version"] + 1)):
                raise DomainError("Incomplete context history")
            current[row["id"]] = row
        if any(identifier not in current for identifier, _ in history):
            raise DomainError("Orphan context history")
        seen = set()
        for row in tables["commands"]:
            owner = current.get(row["context"])
            key = (row["actor"], row["engagement"], row["command_id"])
            if (
                key in seen
                or owner is None
                or (row["context"], row["version"]) not in history
                or (row["actor"], row["engagement"]) != (owner["actor"], owner["engagement"])
            ):
                raise DomainError("Invalid context command ownership")
            seen.add(key)
    else:
        jobs = {}
        for row in tables["jobs"]:
            command = json.loads(row["command"])
            if (
                row["id"] in jobs
                or digest(command) != row["command_digest"]
                or command.get("kind") != "meeting.message"
                or command.get("command_id") != row["command_id"]
                or command.get("expected_revision") != row["expected_revision"]
            ):
                raise DomainError("Job command integrity failure")
            jobs[row["id"]] = row
        transitions = {}
        for row in tables["transitions"]:
            key = (row["job"], row["revision"])
            if key in transitions or row["job"] not in jobs:
                raise DomainError("Invalid job transition history")
            transitions[key] = row
        for identifier, row in jobs.items():
            revisions = sorted(v for j, v in transitions if j == identifier)
            head = transitions.get((identifier, row["job_revision"]))
            if (
                revisions != list(range(row["job_revision"] + 1))
                or head is None
                or head["status"] != row["status"]
                or head["error_code"] != row["error_code"]
            ):
                raise DomainError("Job transition head mismatch")


def backup(destination: Path, *, contexts=None, jobs=None, instructor_access_root=None):
    """Capture selected live companion objects; never starts/retries jobs."""
    destination = _new(destination)
    if contexts is None and jobs is None and instructor_access_root is None:
        raise DomainError("Select at least one companion")
    members, captures = {}, {}
    for kind, instance in [("contexts", contexts), ("jobs", jobs)]:
        if instance is None:
            continue
        with instance._db() as db:
            db.execute("BEGIN")
            tables = {
                name: [dict(r) for r in db.execute(f"SELECT * FROM {name}")]
                for name in TABLES[kind]
            }
            stamp = datetime.now(UTC).isoformat()
        body = {"captured_at": stamp, "tables": tables}
        _validate(kind, body)
        members[kind + ".json"] = _json(body)
        captures[kind] = stamp
    if instructor_access_root is not None:
        root = Path(instructor_access_root).absolute()
        _private(root, True)
        fd = os.open(root / "access.jsonl", os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            _private(root / "access.jsonl")
            raw = stream.read(MAX_LOG_BYTES + 1)
            head = _read(root / "head.json")
            InstructorAccessLog._verify(raw, json.loads(head))
            members.update({"access.jsonl": raw, "head.json": head})
            captures["instructor_access"] = datetime.now(UTC).isoformat()
    manifest = {
        "schema": "PRIVATE_COMPANION_V1",
        "component_captured_at": captures,
        "globally_atomic": False,
        "jobs_restore_mode": "ARCHIVE_ONLY",
        "members": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            for name, raw in members.items()
        },
    }
    with tempfile.TemporaryDirectory(prefix="companion-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir(mode=0o700)
        for name, raw in members.items():
            _write(stage / name, raw)
        _write(stage / "MANIFEST.json", _json(manifest))
        publish(stage, destination)
    return manifest


def restore(source: Path, destination: Path, *, engine=None, principal_map=None):
    """Restore contexts with explicit new ownership; jobs/log retained as inert archives.

    The caller must restore/provision/grant the main store independently. No old
    credentials or grants are copied. Original hashed context histories stay unchanged.
    """
    source = Path(source).absolute()
    _private(source, True)
    destination = _new(destination)
    manifest = json.loads(_read(source / "MANIFEST.json"))
    allowed = {"contexts.json", "jobs.json", "access.jsonl", "head.json"}
    names = set(manifest.get("members", {}))
    if (
        manifest.get("schema") != "PRIVATE_COMPANION_V1"
        or not names
        or not names <= allowed
        or ("access.jsonl" in names) != ("head.json" in names)
        or {p.name for p in source.iterdir()} != names | {"MANIFEST.json"}
    ):
        raise DomainError("Invalid companion inventory")
    members = {}
    for name in names:
        raw = _read(source / name)
        if manifest["members"][name] != {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }:
            raise DomainError("Companion member integrity failure")
        members[name] = raw
    bodies = {}
    for kind in TABLES:
        if kind + ".json" in members:
            bodies[kind] = json.loads(members[kind + ".json"])
            _validate(kind, bodies[kind])
    if "access.jsonl" in members:
        InstructorAccessLog._verify(members["access.jsonl"], json.loads(members["head.json"]))
    tables = bodies.get("contexts", {}).get("tables")
    if tables is not None:
        owners = {r["actor"] for r in tables["contexts"]}
        if (
            engine is None
            or not isinstance(principal_map, dict)
            or set(principal_map) != owners
            or len(set(principal_map.values())) != len(owners)
        ):
            raise DomainError("Exact distinct context owner mapping required")
    with tempfile.TemporaryDirectory(
        prefix="companion-restore-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir(mode=0o700)
        if tables is not None:
            context_root = stage / "contexts"
            context_root.mkdir(mode=0o700)
            restored = WorkspaceContexts(context_root, engine)
            authorized = []
            for row in tables["contexts"]:
                actor = principal_map[row["actor"]]
                state = restored._state(actor, row["engagement"])
                permission = state.get("permissions", [])
                authorized.append((actor, row["engagement"], sorted(permission)))
                for history in tables["history"]:
                    if history["context"] != row["id"]:
                        continue
                    prior = (
                        json.loads(history["content"]).get("context_basis", {}).get("permissions")
                    )
                    if prior is None or any(p not in permission for p in prior):
                        if "instruct" not in permission:
                            raise DomainError(
                                "Historical context requires instructor restoration", status=403
                            )
            with restored._db() as db:
                for table, columns in TABLES["contexts"].items():
                    for original in tables[table]:
                        row = dict(original)
                        if "actor" in row:
                            row["actor"] = principal_map[row["actor"]]
                        placeholders = ",".join("?" for _ in columns)
                        db.execute(
                            f"INSERT INTO {table} VALUES({placeholders})",
                            tuple(row[c] for c in columns),
                        )
        if "jobs.json" in members:
            _write(stage / "jobs-ARCHIVE-ONLY.json", members["jobs.json"])
        if "access.jsonl" in members:
            log_root = stage / "instructor-access-archive"
            log_root.mkdir(mode=0o700)
            for name in ("access.jsonl", "head.json"):
                _write(log_root / name, members[name])
        receipt = {
            "schema": "PRIVATE_COMPANION_RESTORE_V1",
            "source_manifest_sha256": hashlib.sha256(_read(source / "MANIFEST.json")).hexdigest(),
            "restored_at": datetime.now(UTC).isoformat(),
            "component_captured_at": manifest["component_captured_at"],
            "globally_atomic": False,
            "principal_map": principal_map if tables else {},
            "credentials_or_grants_restored": False,
            "jobs": "ARCHIVE_ONLY",
            "automatic_execution": False,
            "original_hashed_context_content_preserved": True,
        }
        _write(stage / "RESTORE_RECEIPT.json", _json(receipt))
        if tables is not None:
            for actor, engagement, permissions in authorized:
                if sorted(restored._state(actor, engagement).get("permissions", [])) != permissions:
                    raise DomainError("Context restore authority changed", status=403)
        publish(stage, destination)
    return receipt
