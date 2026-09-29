"""Seed writable company runtimes from immutable activity capsules, before any audit."""

import hashlib
import secrets
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path

from .company_activity_plan import _bytes, _parse, _write
from .company_activity_plan_sources import MAX_JOB_BYTES, _manifest, _private
from .company_store import CompanyStore, CompanyStoreError, _id, _json, _now, _time
from .private_publication import publish

SCHEMA = "PRIVATE_COMPANY_RUNTIME_ACTIVATION_V1"
SYSTEM_FIELDS = ("company", "branch", "system", "owner")
VERSION_FIELDS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "event_at",
    "available_at",
    "imported_at",
    "origin",
    "provenance",
    "content",
    "sha256",
    "command_id",
    "input_digest",
)
MAX_SYSTEMS = 10000
MAX_VERSIONS = 50000


def _columns(db, table):
    row = db.execute("SELECT type,sql FROM sqlite_master WHERE name=?", (table,)).fetchone()
    if (
        not row
        or row[0] != "table"
        or not isinstance(row[1], str)
        or "VIRTUAL TABLE" in row[1].upper()
    ):
        raise CompanyStoreError("Ordinary source tables required")
    return [(r[1], r[2], r[6]) for r in db.execute(f"PRAGMA table_xinfo({table})")]


def _update(digest, values):
    body = _json(values).encode()
    digest.update(str(len(body)).encode() + b":" + body)


def _version(row, systems, previous):
    if any(
        not isinstance(row[k], str)
        for k in VERSION_FIELDS
        if k not in ("version", "event_at", "content")
    ):
        raise CompanyStoreError("Exact source scalar types required")
    for key in ("company", "branch", "system", "record", "command_id"):
        _id(row[key])
    identity = tuple(row[k] for k in VERSION_FIELDS[:4])
    if identity[:3] not in systems:
        raise CompanyStoreError("Source version lacks registered system")
    if type(row["version"]) is not int or row["version"] != previous.get(identity, 0) + 1:
        raise CompanyStoreError("Contiguous immutable source versions required")
    previous[identity] = row["version"]
    raw = row["content"]
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 25 * 1024 * 1024:
        raise CompanyStoreError("Bounded original source bytes required")
    pin = hashlib.sha256(raw).hexdigest()
    if pin != row["sha256"]:
        raise CompanyStoreError("Original source byte hash differs")
    origin = row["origin"]
    if origin not in {
        "AUTHORED_TRAINING_SOURCE",
        "MIGRATED_SYNTHETIC_HISTORY",
        "REPOSITORY_SYNTHETIC_DOCUMENT",
    }:
        raise CompanyStoreError("Explicit supported synthetic source origin required")
    event = row["event_at"]
    if event is None:
        if origin == "AUTHORED_TRAINING_SOURCE":
            raise CompanyStoreError("Authored event time required")
    elif not isinstance(event, str) or _time(event) != event:
        raise CompanyStoreError("Canonical source event timestamp required")
    for field in ("available_at", "imported_at"):
        if _time(row[field]) != row[field]:
            raise CompanyStoreError("Canonical source timestamp required")
    if event is not None and row["available_at"] < event:
        raise CompanyStoreError("Source availability precedes event")
    if len(row["provenance"].encode()) > 65536:
        raise CompanyStoreError("Bounded source provenance required")
    provenance = _parse(row["provenance"].encode())
    if not isinstance(provenance, dict) or not provenance.get("source_reference"):
        raise CompanyStoreError("Explicit original provenance required")
    expected = hashlib.sha256(
        _json(
            [identity, row["version"] - 1, event, row["available_at"], origin, provenance, pin]
        ).encode()
    ).hexdigest()
    if expected != row["input_digest"]:
        raise CompanyStoreError("Original command input digest differs")
    controls = provenance.get("control_ids", [])
    if not isinstance(controls, list) or any(not isinstance(c, str) for c in controls):
        raise CompanyStoreError("Explicit control-reference array required")
    return provenance, controls


def _sealed_sidecars(path):
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            raise CompanyStoreError("Pristine capsule cannot have SQLite journal sidecars")


def activate(capsule_root: Path, destination: Path, *, expected_manifest_sha256: str):
    capsule_root, destination = Path(capsule_root).absolute(), Path(destination).absolute()
    _private(capsule_root, directory=True)
    _private(destination.parent, directory=True)
    if (
        destination.exists()
        or destination.is_symlink()
        or ".." in destination.parts
        or any(p.is_symlink() for p in destination.parents)
        or destination.resolve().is_relative_to(capsule_root.resolve())
    ):
        raise CompanyStoreError("New private company runtime outside original capsule required")
    source_root = capsule_root / "company"
    source_path = source_root / "company.sqlite3"
    _sealed_sidecars(source_path)
    manifest, _ = _manifest(capsule_root / "MANIFEST.json", expected_manifest_sha256, source_root)
    stamp = _private(source_path)
    started = _now()
    systems = set()
    previous = {}
    controls = Counter()
    metadata = []
    system_digest = hashlib.sha256()
    version_digest = hashlib.sha256()
    with tempfile.TemporaryDirectory(
        prefix=".company-runtime-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        runtime = CompanyStore(stage)
        with (
            closing(
                sqlite3.connect(source_path.as_uri() + "?mode=ro&immutable=1", uri=True)
            ) as source,
            runtime._db() as target,
        ):
            source.row_factory = sqlite3.Row
            source.execute("PRAGMA query_only=ON")
            source.execute("PRAGMA trusted_schema=OFF")
            source.execute("BEGIN")
            target.execute("BEGIN IMMEDIATE")
            for table in ("systems", "versions", "grants", "collections", "access_events"):
                if _columns(source, table) != _columns(target, table):
                    raise CompanyStoreError("Source table columns differ from application schema")
            for table in ("grants", "collections", "access_events"):
                if source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                    raise CompanyStoreError(
                        "Pristine company capsule cannot contain access authority/history"
                    )
            counts = {
                t: source.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("systems", "versions")
            }
            size = source.execute(
                "SELECT COALESCE(SUM(length(content)+length(CAST(provenance AS BLOB))),0) "
                "FROM versions"
            ).fetchone()[0]
            if (
                not 0 < counts["systems"] <= MAX_SYSTEMS
                or not 0 < counts["versions"] <= MAX_VERSIONS
                or size > MAX_JOB_BYTES
            ):
                raise CompanyStoreError("Company seed count or byte quota exceeded")
            for key in counts:
                if (
                    type(manifest["counts"].get(key)) is not int
                    or manifest["counts"][key] != counts[key]
                ):
                    raise CompanyStoreError("Capsule counts differ from native tables")
            for row in source.execute(
                "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
            ):
                values = tuple(row)
                for value in values:
                    _id(value)
                if values[:3] in systems:
                    raise CompanyStoreError("Duplicate registered system")
                systems.add(values[:3])
                _update(system_digest, values)
                target.execute(
                    "INSERT INTO systems(company,branch,system,owner) VALUES(?,?,?,?)", values
                )
            seen_bytes = 0
            for row in source.execute(
                "SELECT "
                + ",".join(VERSION_FIELDS)
                + " FROM versions ORDER BY company,branch,system,record,version"
            ):
                _, refs = _version(row, systems, previous)
                seen_bytes += len(row["content"]) + len(row["provenance"].encode())
                if seen_bytes > MAX_JOB_BYTES:
                    raise CompanyStoreError("Company source byte quota exceeded")
                controls.update(set(refs))
                values = [
                    row[k] if k != "content" else {"bytes": len(row[k]), "sha256": row["sha256"]}
                    for k in VERSION_FIELDS
                ]
                _update(version_digest, values)
                target.execute(
                    "INSERT INTO versions("
                    + ",".join(VERSION_FIELDS)
                    + ") VALUES("
                    + ",".join("?" for _ in VERSION_FIELDS)
                    + ")",
                    tuple(row),
                )
                metadata.append(
                    {
                        k: row[k]
                        for k in ("company", "branch", "system", "record", "version", "sha256")
                    }
                )
            if target.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise CompanyStoreError("Seed foreign-key validation failed")
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise CompanyStoreError("Source database integrity failure")
        _sealed_sidecars(source_path)
        if _private(source_path) != stamp:
            raise CompanyStoreError("Capsule changed during activation")
        _manifest(capsule_root / "MANIFEST.json", expected_manifest_sha256, source_root)
        # Recheck the fresh store; application triggers protect future immutable history.
        actual_system = hashlib.sha256()
        actual_version = hashlib.sha256()
        with runtime._db() as db:
            for row in db.execute(
                "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
            ):
                _update(actual_system, tuple(row))
            for row in db.execute(
                "SELECT "
                + ",".join(VERSION_FIELDS)
                + " FROM versions ORDER BY company,branch,system,record,version"
            ):
                if hashlib.sha256(row["content"]).hexdigest() != row["sha256"]:
                    raise CompanyStoreError("Retained seed byte mismatch")
                _update(
                    actual_version,
                    [
                        row[k]
                        if k != "content"
                        else {"bytes": len(row[k]), "sha256": row["sha256"]}
                        for k in VERSION_FIELDS
                    ],
                )
            if (
                actual_system.digest() != system_digest.digest()
                or actual_version.digest() != version_digest.digest()
            ):
                raise CompanyStoreError("Exact seed row preservation failed")
            for table in ("grants", "collections", "access_events"):
                if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                    raise CompanyStoreError("Runtime authority was copied")
        receipt = {
            "schema": SCHEMA,
            "runtime_instance_id": "COMPANY-RUNTIME-" + secrets.token_hex(16),
            "activation_started_at": started,
            "activated_at": _now(),
            "capsule_root": str(capsule_root),
            "capsule_manifest_sha256": expected_manifest_sha256,
            "seed_counts": {**counts, "grants": 0, "collections": 0, "access_events": 0},
            "seed_table_sha256": {
                "systems": system_digest.hexdigest(),
                "versions": version_digest.hexdigest(),
            },
            "seed_database_sha256": hashlib.sha256(runtime.path.read_bytes()).hexdigest(),
            "seed_records": metadata,
            "explicit_control_reference_version_counts": dict(sorted(controls.items())),
            "native_fields_preserved": list(VERSION_FIELDS),
            "schema_source": "APPLICATION_OWNED_COMPANY_STORE",
            "runtime_purpose": "COMPANY_OWNED_WRITABLE_SOURCE_NOT_AUDIT_CACHE",
            "seed_database_hash_scope": "ACTIVATION_POINT_ONLY_MUTABLE_AUTHORIZED_JOURNALS",
            "capsule_modified": False,
            "grants_created": False,
            "audit_created": False,
            "qualification": "SYNTHETIC_SOURCE_QUALIFICATIONS_UNCHANGED_NOT_CANON_PROMOTION",
            "code_pins": {
                name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in (
                    "company_runtime_activation.py",
                    "company_store.py",
                    "company_activity_plan_sources.py",
                    "private_publication.py",
                )
            },
        }
        _write(stage / "ACTIVATION.json", _bytes(receipt))
        _sealed_sidecars(source_path)
        _manifest(capsule_root / "MANIFEST.json", expected_manifest_sha256, source_root)
        publish(stage, destination)
    return receipt
