"""Explicit private companion recovery; engagement backups still exclude personal drafts.

Trusted local operator only. Restore requires an explicit identity mapping and current
membership, never transfers old tokens/grants, and never overwrites an existing draft
store. Scope-stale drafts retain their original context digest and remain hidden.
"""

import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from .draft_store import DraftStore
from .store import DomainError

COLUMNS = (
    "principal",
    "engagement",
    "action",
    "object_id",
    "version",
    "fields",
    "context_digest",
    "base_version",
    "updated_at",
    "command_id",
    "command_digest",
)
MAX_BACKUP_BYTES = 100 * 1024 * 1024


def _parent(path):
    if (
        any(p.is_symlink() for p in [path, *path.parents])
        or not path.parent.is_dir()
        or path.parent.stat().st_mode & 0o077
    ):
        raise DomainError("Private nonsymlink recovery parent required")


def _write(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def backup(drafts: DraftStore, destination: Path):
    destination = Path(destination).absolute()
    _parent(destination)
    if destination.exists():
        raise DomainError("New draft companion destination required")
    with drafts._db() as db:
        db.execute("BEGIN")
        rows = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM drafts ORDER BY principal,engagement,action,object_id"
            )
        ]
    body = {
        "format": "PERSONAL_DRAFT_COMPANION_V1",
        "rows": rows,
        "created_at": datetime.now(UTC).isoformat(),
        "automatic_engagement_restore": False,
    }
    data = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(data) > MAX_BACKUP_BYTES:
        raise DomainError("Draft companion exceeds bounded backup size", status=413)
    destination.mkdir(mode=0o700)
    _write(destination / "drafts.json", data)
    manifest = {
        "format": body["format"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "rows": len(rows),
        "explicit_identity_mapping_required": True,
    }
    _write(destination / "MANIFEST.json", json.dumps(manifest, indent=2).encode())
    return manifest


def restore(source: Path, store, *, principal_map: dict[str, str]):
    source = Path(source).absolute()
    _parent(source)
    paths = [source / "drafts.json", source / "MANIFEST.json"]
    if not source.is_dir() or source.stat().st_mode & 0o077:
        raise DomainError("Private draft companion required")
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise DomainError("Private regular companion files required")
    if paths[0].stat().st_size > MAX_BACKUP_BYTES or paths[1].stat().st_size > 4096:
        raise DomainError("Draft companion exceeds bounds")
    data, manifest = paths[0].read_bytes(), json.loads(paths[1].read_bytes())
    if manifest.get("sha256") != hashlib.sha256(data).hexdigest() or manifest.get("bytes") != len(
        data
    ):
        raise DomainError("Draft companion integrity failure")
    body = json.loads(data)
    if body.get("format") != "PERSONAL_DRAFT_COMPANION_V1" or not isinstance(
        body.get("rows"), list
    ):
        raise DomainError("Invalid draft companion schema")
    rows = body["rows"]
    if any(not isinstance(row, dict) or set(row) != set(COLUMNS) for row in rows):
        raise DomainError("Invalid draft row schema")
    counts = Counter(row["principal"] for row in rows)
    if any(count > 500 for count in counts.values()):
        raise DomainError("Restored personal draft quota exceeded")
    for owner in counts:
        owned = [row for row in rows if row["principal"] == owner]
        if any(row["fields"] is not None and not isinstance(row["fields"], str) for row in owned):
            raise DomainError("Invalid serialized personal draft")
        if sum(len((row["fields"] or "").encode()) for row in owned) > 10_000_000:
            raise DomainError("Restored personal draft quota exceeded")
    owners = {row.get("principal") for row in rows}
    if (
        not isinstance(principal_map, dict)
        or set(principal_map) != owners
        or len(set(principal_map.values())) != len(principal_map)
    ):
        raise DomainError("Exact distinct owner mapping required")
    destination = store.root / "personal-drafts.sqlite3"
    _parent(destination)
    if destination.exists():
        raise DomainError("Draft restore cannot overwrite an existing store")
    # Use the existing validator and authorization against live target engagement state.
    with tempfile.TemporaryDirectory(prefix="draft-restore-", dir=store.root) as temporary:
        proxy = SimpleNamespace(root=Path(temporary), get=store.get, membership=store.membership)
        staging = DraftStore(proxy)
        seen = set()
        for row in rows:
            if set(row) != set(COLUMNS) or type(row["version"]) is not int or row["version"] < 1:
                raise DomainError("Invalid draft row")
            actor = principal_map[row["principal"]]
            identity = (actor, row["engagement"], row["action"], row["object_id"])
            if identity in seen:
                raise DomainError("Duplicate mapped draft identity")
            seen.add(identity)
            staging._context(
                *identity
            )  # Rechecks expired/revoked principals and current membership.
            if row["fields"] is not None:
                staging.write(
                    *identity,
                    {
                        "command_id": "restore-validation",
                        "expected_version": 0,
                        "fields": json.loads(row["fields"]),
                        "base_workpaper_version": row["base_version"],
                    },
                )
            with staging._db() as db:
                db.execute(
                    "INSERT OR REPLACE INTO drafts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (actor, *(row[key] for key in COLUMNS[1:])),
                )
        # Atomic no-clobber publication on the same filesystem; no partial target on failure.
        os.link(staging.path, destination)
    receipt = {
        "status": "PERSONAL_DRAFT_COMPANION_RESTORED",
        "rows": len(rows),
        "source_sha256": manifest["sha256"],
        "explicit_owner_mapping": True,
        "old_credentials_or_grants_copied": False,
        "scope_context_preserved": True,
        "formal_records_modified": False,
    }
    return receipt
