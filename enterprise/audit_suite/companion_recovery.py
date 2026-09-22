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
from .personal_views_recovery import TABLES as VIEW_TABLES
from .personal_views_recovery import restore_tables as restore_views
from .personal_views_recovery import validate as validate_views
from .private_publication import publish
from .store import DomainError, canonical, digest
from .workspace_context import WorkspaceContexts

MAX_BYTES = 128 * 1024 * 1024
TABLES = {
    "personal_views": VIEW_TABLES,
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
    if kind == "personal_views":
        try:
            if (
                not isinstance(body["captured_at"], str)
                or datetime.fromisoformat(body["captured_at"]).tzinfo is None
            ):
                raise ValueError("Missing capture timestamp")
            validate_views(tables)
        except (ValueError, TypeError, KeyError) as exc:
            raise DomainError("Invalid personal-view snapshot") from exc
        return
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


def backup(
    destination: Path,
    *,
    contexts=None,
    jobs=None,
    instructor_access_root=None,
    instructor_releases=None,
    personal_views=None,
    investigation_handoffs=None,
    work_guidance=None,
    instructor_key_views=None,
    instructor_assessments=None,
):
    """Capture selected live companion objects; never starts/retries jobs."""
    destination = _new(destination)
    if (
        contexts is None
        and jobs is None
        and instructor_access_root is None
        and instructor_releases is None
        and personal_views is None
        and investigation_handoffs is None
        and work_guidance is None
        and instructor_key_views is None
        and instructor_assessments is None
    ):
        raise DomainError("Select at least one companion")
    members, captures = {}, {}
    for kind, instance in [
        ("contexts", contexts),
        ("jobs", jobs),
        ("personal_views", personal_views),
    ]:
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
    if instructor_releases is not None:
        from .instructor_releases import validate_snapshot

        snapshot = instructor_releases.snapshot()
        validate_snapshot(snapshot)
        members["instructor-releases.json"] = _json(snapshot)
        captures["instructor_releases"] = datetime.now(UTC).isoformat()
    if investigation_handoffs is not None:
        from .investigation_handoffs import validate_snapshot

        snapshot = investigation_handoffs.snapshot()
        validate_snapshot(snapshot)
        members["investigation-handoffs.json"] = _json(snapshot)
        captures["investigation_handoffs"] = datetime.now(UTC).isoformat()
    if work_guidance is not None:
        from .work_guidance import validate_archive

        snapshot = work_guidance.snapshot()
        validate_archive(snapshot)
        members["work-guidance.json"] = _json(snapshot)
        captures["work_guidance"] = datetime.now(UTC).isoformat()
    if instructor_key_views is not None:
        from .instructor_key_views import validate_archive

        snapshot = instructor_key_views.snapshot()
        validate_archive(snapshot)
        members["instructor-key-views.json"] = _json(snapshot)
        captures["instructor_key_views"] = datetime.now(UTC).isoformat()
    if instructor_assessments is not None:
        from .instructor_assessments import validate_archive

        snapshot = instructor_assessments.snapshot()
        validate_archive(snapshot)
        members["instructor-assessments.json"] = _json(snapshot)
        captures["instructor_assessments"] = datetime.now(UTC).isoformat()
    manifest = {
        "instructor_assessments_restore_mode": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
        if instructor_assessments is not None
        else "NOT_INCLUDED",
        "instructor_key_views_restore_mode": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
        if instructor_key_views is not None
        else "NOT_INCLUDED",
        "work_guidance_restore_mode": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
        if work_guidance is not None
        else "NOT_INCLUDED",
        "schema": "PRIVATE_COMPANION_V1",
        "component_captured_at": captures,
        "globally_atomic": False,
        "jobs_restore_mode": "ARCHIVE_ONLY",
        "investigation_handoffs_restore_mode": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
        if investigation_handoffs is not None
        else "NOT_INCLUDED",
        "personal_views_restore_mode": "EXPLICIT_OWNER_MAPPING_CURRENT_AUTHORITY"
        if personal_views is not None
        else "NOT_INCLUDED",
        "instructor_releases_restore_mode": (
            "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
            if instructor_releases is not None
            else "NOT_INCLUDED"
        ),
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
    manifest_raw = _read(source / "MANIFEST.json")
    manifest = json.loads(manifest_raw)
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise DomainError("Separate companion source and restoration roots required")
    allowed = {
        "contexts.json",
        "jobs.json",
        "access.jsonl",
        "head.json",
        "instructor-releases.json",
        "personal_views.json",
        "investigation-handoffs.json",
        "work-guidance.json",
        "instructor-key-views.json",
        "instructor-assessments.json",
    }
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
            if kind == "personal_views":
                from .inference import _json as strict_json

                bodies[kind] = strict_json(members[kind + ".json"])
            else:
                bodies[kind] = json.loads(members[kind + ".json"])
            _validate(kind, bodies[kind])
    if "access.jsonl" in members:
        InstructorAccessLog._verify(members["access.jsonl"], json.loads(members["head.json"]))
    if "instructor-releases.json" in members:
        from .inference import _json as strict_json
        from .instructor_releases import validate_snapshot

        try:
            validate_snapshot(strict_json(members["instructor-releases.json"]))
        except (ValueError, TypeError, KeyError) as error:
            raise DomainError("Invalid private release archive") from error
    if "investigation-handoffs.json" in members:
        from .inference import _json as strict_json
        from .investigation_handoffs import validate_snapshot

        try:
            validate_snapshot(strict_json(members["investigation-handoffs.json"]))
        except (ValueError, TypeError, KeyError) as error:
            raise DomainError("Invalid investigation handoff archive") from error
    if "work-guidance.json" in members:
        from .inference import _json as strict_json
        from .work_guidance import validate_archive

        try:
            validate_archive(strict_json(members["work-guidance.json"]))
        except (ValueError, TypeError, KeyError) as error:
            raise DomainError("Invalid personal guidance archive") from error
    if "instructor-key-views.json" in members:
        from .inference import _json as strict_json
        from .instructor_key_views import validate_archive

        try:
            validate_archive(strict_json(members["instructor-key-views.json"]))
        except (ValueError, TypeError, KeyError) as error:
            raise DomainError("Invalid saved instructor Key view archive") from error
    if "instructor-assessments.json" in members:
        from .inference import _json as strict_json
        from .instructor_assessments import validate_archive

        try:
            validate_archive(strict_json(members["instructor-assessments.json"]))
        except (ValueError, TypeError, KeyError) as error:
            raise DomainError("Invalid instructor assessment archive") from error
    tables = bodies.get("contexts", {}).get("tables")
    view_tables = bodies.get("personal_views", {}).get("tables")
    owners = {r["actor"] for r in tables["contexts"]} if tables is not None else set()
    owners |= {r["actor"] for r in view_tables["views"]} if view_tables is not None else set()
    if tables is not None or view_tables is not None:
        if (
            engine is None
            or not isinstance(principal_map, dict)
            or set(principal_map) != owners
            or any(not isinstance(v, str) or not v for v in principal_map.values())
            or len(set(principal_map.values())) != len(owners)
        ):
            raise DomainError("Exact distinct companion owner mapping required")
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
        restored_views = None
        view_authority = []
        if view_tables is not None:
            view_root = stage / "personal-views"
            view_root.mkdir(mode=0o700)
            restored_views, view_authority = restore_views(
                view_root,
                engine,
                view_tables,
                principal_map,
                hashlib.sha256(manifest_raw).hexdigest(),
            )
        if "instructor-releases.json" in members:
            _write(
                stage / "instructor-releases-ARCHIVE-ONLY.json", members["instructor-releases.json"]
            )
        if "jobs.json" in members:
            _write(stage / "jobs-ARCHIVE-ONLY.json", members["jobs.json"])
        if "investigation-handoffs.json" in members:
            _write(
                stage / "investigation-handoffs-ARCHIVE-ONLY.json",
                members["investigation-handoffs.json"],
            )
        if "work-guidance.json" in members:
            _write(stage / "work-guidance-ARCHIVE-ONLY.json", members["work-guidance.json"])
        if "instructor-key-views.json" in members:
            _write(
                stage / "instructor-key-views-ARCHIVE-ONLY.json",
                members["instructor-key-views.json"],
            )
        if "instructor-assessments.json" in members:
            _write(
                stage / "instructor-assessments-ARCHIVE-ONLY.json",
                members["instructor-assessments.json"],
            )
        if "access.jsonl" in members:
            log_root = stage / "instructor-access-archive"
            log_root.mkdir(mode=0o700)
            for name in ("access.jsonl", "head.json"):
                _write(log_root / name, members[name])
        receipt = {
            "schema": "PRIVATE_COMPANION_RESTORE_V1",
            "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "restored_at": datetime.now(UTC).isoformat(),
            "component_captured_at": manifest["component_captured_at"],
            "globally_atomic": False,
            "principal_map": principal_map if tables is not None or view_tables is not None else {},
            "personal_views": "OPERATIONAL_EXPLICIT_OWNER_MAPPING_CURRENT_AUTHORITY"
            if view_tables is not None
            else "NOT_INCLUDED",
            "original_hashed_personal_view_content_preserved": view_tables is not None,
            "credentials_or_grants_restored": False,
            "instructor_assessments": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
            if "instructor-assessments.json" in members
            else "NOT_INCLUDED",
            "instructor_key_views": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
            if "instructor-key-views.json" in members
            else "NOT_INCLUDED",
            "jobs": "ARCHIVE_ONLY",
            "work_guidance": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
            if "work-guidance.json" in members
            else "NOT_INCLUDED",
            "investigation_handoffs": "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
            if "investigation-handoffs.json" in members
            else "NOT_INCLUDED",
            "instructor_releases": (
                "ARCHIVE_ONLY_NOT_OPERATIONALLY_REHYDRATED"
                if "instructor-releases.json" in members
                else "NOT_INCLUDED"
            ),
            "release_principals_or_bindings_rehydrated": False,
            "automatic_execution": False,
            "original_hashed_context_content_preserved": True,
        }
        _write(stage / "RESTORE_RECEIPT.json", _json(receipt))
        if tables is not None:
            for actor, engagement, permissions in authorized:
                if sorted(restored._state(actor, engagement).get("permissions", [])) != permissions:
                    raise DomainError("Context restore authority changed", status=403)
        for actor, engagement, basis in view_authority:
            if restored_views._state(actor, engagement)[1] != basis:
                raise DomainError("Saved-view restore authority changed", status=403)
        if (
            _read(source / "MANIFEST.json") != manifest_raw
            or {p.name for p in source.iterdir()} != names | {"MANIFEST.json"}
            or any(_read(source / name) != raw for name, raw in members.items())
        ):
            raise DomainError("Companion source changed before publication")
        publish(stage, destination)
    return receipt
