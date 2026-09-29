"""Local private company-source backup/restore; restore invalidates copied read grants."""

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _now


def _new_root(destination):
    destination = Path(destination).absolute()
    if any(p.is_symlink() for p in [destination, *destination.parents]):
        raise CompanyStoreError("Directory aliases forbidden")
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
    ):
        raise CompanyStoreError("New directory under existing private parent required")
    destination.mkdir(mode=0o700)
    return destination


def _logical(db):
    expected = {
        "no_version_update",
        "no_version_delete",
        "no_collection_update",
        "no_collection_delete",
    }
    actual = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    if not expected.issubset(actual):
        raise CompanyStoreError("Required immutability protections missing")
    result = {}
    for table in ("systems", "versions", "collections", "access_events"):
        rows = db.execute(f"SELECT * FROM {table}").fetchall()
        encoded = []
        for row in rows:
            encoded.append(
                [
                    {"bytes_sha256": hashlib.sha256(v).hexdigest()} if isinstance(v, bytes) else v
                    for v in row
                ]
            )
        result[table] = hashlib.sha256(
            json.dumps(sorted(encoded, key=str), sort_keys=True).encode()
        ).hexdigest()
    for content, sha in db.execute("SELECT content,sha256 FROM versions"):
        if hashlib.sha256(content).hexdigest() != sha:
            raise CompanyStoreError("Company source integrity failure")
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise CompanyStoreError("Database integrity failure")
    return result


def backup(store: CompanyStore, destination: Path):
    """SQLite consistent snapshot and native/logical digest receipt. No content on stdout."""
    root = _new_root(destination)
    target = root / "company.sqlite3"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    os.close(fd)
    with store._db() as source, closing(sqlite3.connect(target)) as copied:
        source.backup(copied)
        logical = _logical(copied)
    manifest = {
        "format": "company-backup-v1",
        "created_at": _now(),
        "database_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "logical_digests": logical,
        "restore_requires_new_grants": True,
    }
    path = root / "MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    path.chmod(0o600)
    return manifest


def restore(source: Path, destination: Path):
    """Restore only a verified backup into a new root; all copied grants are revoked."""
    source = Path(source).absolute()
    paths = [source, source / "company.sqlite3", source / "MANIFEST.json"]
    if any(p.is_symlink() for path in paths for p in [path, *path.parents]):
        raise CompanyStoreError("Backup aliases forbidden")
    if any(not p.exists() or p.stat().st_mode & 0o077 for p in paths):
        raise CompanyStoreError("Private backup required")
    manifest = json.loads(paths[2].read_text())
    data = paths[1].read_bytes()
    if manifest.get("format") != "company-backup-v1" or hashlib.sha256(
        data
    ).hexdigest() != manifest.get("database_sha256"):
        raise CompanyStoreError("Backup hash mismatch")
    # Read-only validation before creating any destination; never executes backup SQL scripts.
    with closing(sqlite3.connect(paths[1].as_uri() + "?mode=ro", uri=True)) as db:
        if _logical(db) != manifest["logical_digests"]:
            raise CompanyStoreError("Backup logical mismatch")
    root = _new_root(destination)
    target = root / "company.sqlite3"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    with closing(sqlite3.connect(target)) as db, db:
        prior = _logical(db)
        db.execute("UPDATE grants SET active=0")
        if _logical(db) != prior:
            raise CompanyStoreError("Source history changed during restore")
    # Initialize expected schema/immutability triggers and validate restored source bytes.
    store = CompanyStore(root)
    with store._db() as db:
        if _logical(db) != manifest["logical_digests"]:
            raise CompanyStoreError("Restored history mismatch")
    receipt = {
        "format": "company-restore-v1",
        "restored_at": _now(),
        "backup_sha256": manifest["database_sha256"],
        "source_history_preserved": True,
        "all_read_grants_revoked": True,
    }
    path = root / "RESTORE.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    path.chmod(0o600)
    return receipt
