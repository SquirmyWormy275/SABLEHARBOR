"""Private operator backups and fail-closed restoration into a fresh store."""

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path, PurePosixPath

from .serialized_json import canonical_bytes, update_object
from .store import DomainError, Store, canonical

TABLES = ("principals", "engagements", "members", "events")


def _company_source_member(relative: str) -> bool:
    return (
        re.fullmatch(
            r"worlds/ENG-[0-9a-f]+/(?:scope-[0-9]{5,}/)?"
            r"parent-support/source\.(?:json|sha256)",
            relative,
        )
        is not None
    )


def _validate_source_pins(root: Path, files: dict) -> None:
    """The digest pin is independent retained state, never recreated on restore."""
    for relative in files:
        if not _company_source_member(relative):
            continue
        parent = PurePosixPath(relative).parent
        source = str(parent / "source.json")
        pin = str(parent / "source.sha256")
        if source not in files or pin not in files:
            raise DomainError("Company source integrity pair is incomplete")
        expected = (files[source]["sha256"] + "\n").encode("ascii")
        if (root / pin).read_bytes() != expected:
            raise DomainError("Company source integrity pin mismatch")


def _file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _new_directory(path: Path) -> Path:
    path = path.absolute()
    if not path.parent.is_dir() or path.parent.stat().st_mode & 0o077:
        raise DomainError("Backup/restore parent must be an existing private directory")
    path.mkdir(mode=0o700)  # Never overwrite existing work, even an empty directory.
    return path


def _write(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _history(db) -> dict:
    counts = {}
    for engagement in db.execute("SELECT id,revision,state FROM engagements"):
        previous, count, latest = "", 0, None
        for row in db.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement["id"],)
        ):
            fields = {
                name: canonical(row[name]).encode()
                for name in ("actor", "recorded_at", "previous_hash", "command_id")
            }
            fields["state"] = canonical_bytes(row["state"])
            fields["command"] = canonical_bytes(row["command"])
            event_hash = hashlib.sha256()
            update_object(event_hash, fields)
            if (
                row["revision"] != count
                or row["previous_hash"] != previous
                or event_hash.hexdigest() != row["hash"]
                or hashlib.sha256(fields["command"]).hexdigest() != row["request_hash"]
            ):
                raise DomainError("Backup event history integrity failure")
            count += 1
            previous, latest = row["hash"], row["state"]
        if count != engagement["revision"] + 1 or latest != engagement["state"]:
            raise DomainError("Backup current state does not match its event history")
        counts[engagement["id"]] = {"events": count, "last_hash": previous}
    return counts


def backup(store: Store, destination: Path) -> dict:
    destination = _new_directory(destination)
    db_path = destination / "engagements.sqlite3"
    with store.connect() as source, sqlite3.connect(db_path) as target:
        source.backup(target)
    os.chmod(db_path, 0o600)
    files = {
        "engagements.sqlite3": {
            "sha256": _file_hash(db_path),
            "bytes": db_path.stat().st_size,
        }
    }
    references = {}

    def collect(value):
        if isinstance(value, dict):
            if (
                isinstance(value.get("id"), str)
                and value["id"].startswith("ART-")
                and all(key in value for key in ("sha256", "bytes"))
            ):
                previous = references.setdefault(value["sha256"], value["bytes"])
                if previous != value["bytes"]:
                    raise DomainError("Conflicting artifact sizes in backup")
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        counts = _history(db)
        for row in db.execute("SELECT state FROM events"):
            collect(json.loads(row["state"]))
    world_root = store.root / "worlds"
    world_files = []
    if world_root.is_dir():
        world_files.extend(world_root.rglob("*.json"))
        world_files.extend(
            p
            for p in world_root.rglob("source.sha256")
            if _company_source_member(p.relative_to(store.root).as_posix())
        )
    for path in sorted(world_files):
        if path.is_symlink() or not path.resolve().is_relative_to(store.root):
            raise DomainError("Private backup symlink rejected")
        data = path.read_bytes()
        if path.suffix == ".json":
            collect(json.loads(data))
        relative = path.relative_to(store.root).as_posix()
        files[relative] = _write(destination / relative, data)
    _validate_source_pins(destination, files)
    pack = store.root / "program-pack.json"
    if pack.is_file():
        if pack.is_symlink():
            raise DomainError("Program source symlink rejected")
        files[pack.name] = _write(destination / pack.name, pack.read_bytes())
    for content_hash, size in references.items():
        if len(content_hash) != 64 or any(c not in "0123456789abcdef" for c in content_hash):
            raise DomainError("Invalid retained artifact hash")
        path = store.root / "artifacts" / content_hash
        if path.is_symlink():
            raise DomainError("Artifact backup symlink rejected")
        data = path.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != content_hash:
            raise DomainError("Artifact backup integrity failure")
        relative = "artifacts/" + content_hash
        files[relative] = _write(destination / relative, data)
    manifest = {
        "backup_format": 1,
        "database_schema": 1,
        "status": "COMPLETE",
        "audience": "PRIVATE_OPERATOR_ONLY",
        "files": files,
        "engagements": counts,
        "restore_authentication": "INVALIDATE_ALL_PRIOR_CREDENTIALS_AND_SESSIONS",
        "runtime_prerequisites": "Matching application/repository, licensed source access, "
        "private corpus and optional local model/voice runtime are installed separately. "
        "This is a state backup, not a model or licensed-source distribution.",
    }
    _write(destination / "backup-manifest.json", (canonical(manifest) + "\n").encode())
    return manifest


def restore(source: Path, destination: Path) -> dict:
    source = source.resolve(strict=True)
    manifest = json.loads((source / "backup-manifest.json").read_text())
    if (
        manifest.get("backup_format") != 1
        or manifest.get("database_schema") != 1
        or manifest.get("status") != "COMPLETE"
    ):
        raise DomainError("Unsupported or incomplete backup format")
    for relative, expected in manifest["files"].items():
        pure = PurePosixPath(relative)
        allowed = (
            relative in {"engagements.sqlite3", "program-pack.json"}
            or _company_source_member(relative)
            or (len(pure.parts) == 2 and pure.parts[0] == "artifacts")
            or (len(pure.parts) >= 3 and pure.parts[0] == "worlds" and pure.suffix == ".json")
        )
        path = source / relative
        if (
            not allowed
            or pure.is_absolute()
            or ".." in pure.parts
            or path.is_symlink()
            or not path.resolve().is_relative_to(source)
        ):
            raise DomainError("Unsafe backup member path")
        if path.stat().st_size != expected["bytes"] or _file_hash(path) != expected["sha256"]:
            raise DomainError("Backup member integrity failure")
    _validate_source_pins(source, manifest["files"])
    if "engagements.sqlite3" not in manifest["files"]:
        raise DomainError("Backup database is absent")
    destination = _new_directory(destination)
    restored = Store(destination)
    # Import data into application-owned tables. Never execute schema/triggers
    # from an incoming SQLite file; old login sessions are deliberately omitted.
    uri = (source / "engagements.sqlite3").as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as incoming, restored.connect() as outgoing:
        incoming.row_factory = sqlite3.Row
        incoming.execute("PRAGMA trusted_schema=OFF")
        counts = _history(incoming)
        if counts != manifest["engagements"]:
            raise DomainError("Backup history manifest mismatch")
        for table in TABLES:
            columns = [r[1] for r in outgoing.execute(f"PRAGMA table_info({table})")]
            actual = [r[1] for r in incoming.execute(f"PRAGMA table_info({table})")]
            if actual != columns:
                raise DomainError("Unsupported database migration schema")
            for row in incoming.execute(f"SELECT * FROM {table}"):
                values = list(row)
                if table == "principals":
                    values[columns.index("revoked")] = 1
                outgoing.execute(
                    f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})", values
                )
    for relative in manifest["files"]:
        if relative != "engagements.sqlite3":
            _write(destination / relative, (source / relative).read_bytes())
    receipt = {
        "status": "RESTORED",
        "backup_manifest_sha256": hashlib.sha256(
            (source / "backup-manifest.json").read_bytes()
        ).hexdigest(),
        "engagements": counts,
        "prior_credentials": "ALL_REVOKED",
        "prior_sessions": "NOT_RESTORED",
        "next_step": "Provision a new local principal and explicitly grant engagement membership.",
    }
    _write(destination / "restore-receipt.json", (canonical(receipt) + "\n").encode())
    return receipt
