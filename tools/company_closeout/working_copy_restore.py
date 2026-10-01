"""Restore declared working copies using current portal lifecycle state.

Trusted local operator adapter over the existing portal; no new database, service,
source deletion or modification of immutable CompanyStore history. A current-state
reader and operator-retained checkpoint are mandatory and must live outside backups.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path


class RestoreError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise RestoreError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def private_directory(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Directory alias")
    require(path.is_dir() and not path.stat().st_mode & 0o077, "Private directory required")
    return path


def file_bytes(path):
    require(not path.is_symlink(), "File alias")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        require(
            stat.S_ISREG(s.st_mode)
            and s.st_uid == os.getuid()
            and s.st_nlink == 1
            and not s.st_mode & 0o077
            and s.st_size <= 65536,
            "Owned private bounded file required",
        )
        raw = os.read(fd, 65537)
        require(
            len(raw) == s.st_size and os.fstat(fd).st_ctime_ns == s.st_ctime_ns,
            "Changed or incomplete file",
        )
        return raw
    finally:
        os.close(fd)


def checkpoint(state):
    require(
        isinstance(state, dict)
        and type(state.get("revision")) is int
        and state["revision"] >= 0
        and isinstance(state.get("inventory"), list),
        "Invalid current portal state",
    )
    require(state.get("pending") is None, "Unfinished lifecycle operation")
    ids = [r["id"] for r in state["inventory"]]
    require(0 < len(ids) <= 32 and len(ids) == len(set(ids)), "Invalid population")
    require(
        all(isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", i) for i in ids),
        "Invalid identity",
    )
    return {"revision": state["revision"], "sha256": sha(encoded(state))}


def write_private(path, raw):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(raw)
            f.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def capture(directory, copies, state, *, expected_hashes):
    """Copy exact declared working-file bytes before subsequent disposal events."""
    directory = Path(directory).absolute()
    private_directory(directory.parent)
    require(not directory.exists(), "New backup destination required")
    pin = checkpoint(state)
    lookup = {r["id"]: r for r in state["inventory"]}
    require(set(copies) == set(lookup) == set(expected_hashes), "Backup population differs")
    directory.mkdir(mode=0o700)
    members = []
    for ident, source in sorted(copies.items()):
        require(lookup[ident]["recorded_status"] == "PRESENT", "Copy already disposed")
        raw = file_bytes(Path(source))
        require(
            sha(raw) == expected_hashes[ident] and lookup[ident]["matches_initial_identity"],
            "Copy differs from native declaration",
        )
        name = sha(ident.encode()) + ".bin"
        write_private(directory / name, raw)
        members.append({"id": ident, "file": name, "sha256": sha(raw), "bytes": len(raw)})
    manifest = {"format": "SH-WORKING-COPY-BACKUP-1", "checkpoint": pin, "members": members}
    write_private(directory / "MANIFEST.json", encoded(manifest))
    return sha(encoded(manifest))


def restore(backup, destination, *, backup_sha256, current_reader, expected_checkpoint):
    """Replay current decisions before publishing any restored copy for mediated use."""
    backup = private_directory(backup)
    destination = Path(destination).absolute()
    private_directory(destination.parent)
    require(
        not destination.exists() and not destination.is_relative_to(backup),
        "New separate destination required",
    )
    raw = file_bytes(backup / "MANIFEST.json")
    require(sha(raw) == backup_sha256, "Backup manifest changed")
    manifest = json.loads(raw)
    require(manifest.get("format") == "SH-WORKING-COPY-BACKUP-1", "Unknown backup format")
    state = current_reader()
    require(expected_checkpoint == checkpoint(state), "Missing or stale current checkpoint")
    require(manifest["checkpoint"]["revision"] <= state["revision"], "Current state rolled back")
    lookup = {r["id"]: r for r in state["inventory"]}
    members = manifest["members"]
    require(
        len(members) == len(lookup) and {r["id"] for r in members} == set(lookup),
        "Restore population differs",
    )
    expected_files = {"MANIFEST.json"} | {r["file"] for r in members}
    require({p.name for p in backup.iterdir()} == expected_files, "Backup has unlisted content")
    receipt = {
        "format": "SH-WORKING-COPY-RESTORE-1",
        "backup_sha256": backup_sha256,
        "current_checkpoint": expected_checkpoint,
        "members": [],
    }
    with tempfile.TemporaryDirectory(prefix="restore-stage-", dir=destination.parent) as tmp:
        stage = Path(tmp)
        for row in members:
            ident, name = row["id"], row["file"]
            require(name == sha(ident.encode()) + ".bin", "Invalid backup member path")
            data = file_bytes(backup / name)
            require(
                sha(data) == row["sha256"] and len(data) == row["bytes"], "Backup member changed"
            )
            status = lookup[ident]["recorded_status"]
            require(status in {"PRESENT", "UNLINKED"}, "Unattributed missing record")
            disposition = (
                "SUPPRESSED_DELETED"
                if status == "UNLINKED"
                else ("PRESERVED_RESTRICTED_HOLD" if lookup[ident]["holds"] else "RESTORED")
            )
            if status == "PRESENT":
                write_private(stage / name, data)
            receipt["members"].append({**row, "disposition": disposition})
        # A state transition during restore invalidates the whole publication.
        require(checkpoint(current_reader()) == expected_checkpoint, "State changed during restore")
        write_private(stage / "RESTORE.json", encoded(receipt))
        os.rename(stage, destination)
    return receipt


def disclose(destination, ident, *, current_reader, expected_checkpoint, authorized, action="read"):
    """All record/derivative surfaces share denial before bytes enter user context.

    `authorized` is a trusted policy callback over authenticated caller context;
    neither caller identity nor a boolean approval is accepted from request data.
    Raw filesystem access remains a trusted administrator capability.
    """
    destination = private_directory(destination)
    state = current_reader()
    require(checkpoint(state) == expected_checkpoint, "Stale access checkpoint")
    require(
        action
        in {
            "read",
            "snippet",
            "citation",
            "export",
            "vector",
            "count",
            "graph",
            "tool_result",
            "answer",
            "search",
            "personal_memory",
        },
        "Unknown surface",
    )
    restore_receipt = json.loads(file_bytes(destination / "RESTORE.json"))
    require(
        restore_receipt["current_checkpoint"] == expected_checkpoint, "Restore must be refreshed"
    )
    lookup = {r["id"]: r for r in state["inventory"]}
    row = lookup.get(ident)
    require(
        row is not None and row["recorded_status"] == "PRESENT" and not row["holds"],
        "Record unavailable",
    )
    require(callable(authorized) and authorized(ident, action) is True, "Not authorized")
    member = next((r for r in restore_receipt["members"] if r["id"] == ident), None)
    require(member is not None and member["disposition"] == "RESTORED", "Record suppressed")
    require(member["file"] == sha(ident.encode()) + ".bin", "Invalid restored member")
    raw = file_bytes(destination / member["file"])
    require(sha(raw) == member["sha256"], "Restored content changed")
    require(checkpoint(current_reader()) == expected_checkpoint, "State changed during disclosure")
    require(authorized(ident, action) is True, "Authorization revoked during disclosure")
    # Surface-specific grants never imply unrestricted byte disclosure.
    if action == "count":
        return 1
    if action == "citation":
        return {"record_id": ident, "sha256": member["sha256"]}
    if action == "graph":
        return {"nodes": [ident], "edges": []}
    if action in {"search", "snippet"}:
        return {"record_id": ident, "snippet": raw[:160].decode("utf-8", errors="replace")}
    if action == "vector":
        raise RestoreError("No vector index in declared working-copy environment")
    return raw
