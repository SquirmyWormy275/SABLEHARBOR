"""Publish a lossless native company source edition before fresh audit creation.

This trusted local source operation selects exact, quiescent company ledgers. It
copies application-owned native systems/versions, not grants, collections,
workflow state, incoming triggers, audit records or answers. Original operating
ledgers and files remain the authority and must be preserved independently.
Publication supplies no operating-year completeness or assessment acceptance.
"""

from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from .company_activity_plan import _bytes, _write
from .company_activity_plan_sources import MAX_JOB_BYTES, _manifest
from .company_runtime_activation import (
    MAX_SYSTEMS, MAX_VERSIONS, SYSTEM_FIELDS, VERSION_FIELDS,
    _columns, _sealed_sidecars, _update, _version,
)
from .company_store import CompanyStore, CompanyStoreError, _id, _now
from .private_publication import publish

SCHEMA = "LOSSLESS_COMPANY_NATIVE_SOURCE_EDITION_V1"
MAX_COMPONENTS = 16
MAX_INPUT_BYTES = 256 * 1024 * 1024
CORE_TABLES = ("systems", "versions", "grants", "collections", "access_events")


def require(ok, message):
    if not ok:
        raise CompanyStoreError(message)


def stamp(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve()
            and not any(p.is_symlink() for p in (path, *path.parents)),
            "Canonical source-edition path required")
    s = path.lstat()
    require(s.st_uid == os.getuid() and not s.st_mode & 0o077
            and (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)
                 and s.st_nlink == 1), "Owned private ordinary source required")
    return tuple(getattr(s, key) for key in
                 ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size",
                  "st_mtime_ns", "st_ctime_ns"))


def database_pin(path, expected):
    require(isinstance(expected, str) and len(expected) == 64
            and all(c in "0123456789abcdef" for c in expected),
            "External exact source database SHA256 required")
    before = stamp(path)
    require(before[4] <= MAX_INPUT_BYTES, "Bounded company ledger required")
    _sealed_sidecars(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        opened = tuple(getattr(os.fstat(f.fileno()), key) for key in
                       ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size",
                        "st_mtime_ns", "st_ctime_ns"))
        require(opened == before, "Source changed at open")
        actual = hashlib.file_digest(f, "sha256").hexdigest()
    require(actual == expected and stamp(path) == before,
            "Source database bytes or identity changed")
    _sealed_sidecars(path)
    return {"path": str(path), "sha256": actual, "bytes": before[4],
            "stamp": list(before)}


def native_fingerprints(db):
    systems, versions = hashlib.sha256(), hashlib.sha256()
    for row in db.execute("SELECT " + ",".join(SYSTEM_FIELDS)
                          + " FROM systems ORDER BY company,branch,system"):
        _update(systems, tuple(row))
    for row in db.execute("SELECT " + ",".join(VERSION_FIELDS)
                          + " FROM versions ORDER BY company,branch,system,record,version"):
        _update(versions, [row[k] if k != "content" else
                          {"bytes": len(row[k]), "sha256": row["sha256"]}
                          for k in VERSION_FIELDS])
    return {"systems": systems.hexdigest(), "versions": versions.hexdigest()}


def publish_edition(components, destination):
    """Caller selects externally admitted source pins and stops all their writers.

    Each component is exactly id/database(path,sha256)/systems/versions. Native
    identity and registered ownership conflicts refuse the whole publication.
    No alias, retimestamping, ownership replacement or duplicate collapse exists.
    """
    destination = Path(destination)
    stamp(destination.parent, directory=True)
    require(destination.is_absolute() and destination == destination.resolve()
            and not destination.exists() and not destination.is_symlink(),
            "New private source edition outside all input roots required")
    require(type(components) is list and 1 <= len(components) <= MAX_COMPONENTS,
            "Explicit bounded source components required")
    selected, ids, input_paths = [], set(), set()
    for item in components:
        require(type(item) is dict and set(item) == {"id", "database", "systems", "versions"},
                "Exact source component fields required")
        _id(item["id"])
        require(item["id"] not in ids, "Duplicate component ID")
        ids.add(item["id"])
        require(type(item["database"]) is dict and set(item["database"]) == {"path", "sha256"},
                "Exact database pin required")
        for key, maximum in (("systems", MAX_SYSTEMS), ("versions", MAX_VERSIONS)):
            require(type(item[key]) is int and 1 <= item[key] <= maximum,
                    "Explicit native source counts required")
        path = Path(item["database"]["path"])
        require(str(path) == item["database"]["path"] and path.name == "company.sqlite3"
                and path not in input_paths and not destination.is_relative_to(path.parent),
                "Distinct canonical company databases outside output required")
        stamp(path.parent, directory=True)
        input_paths.add(path)
        selected.append((item, database_pin(path, item["database"]["sha256"])))
    started = _now()
    systems, versions, commands, seen_bytes, summaries = {}, {}, set(), 0, []
    with tempfile.TemporaryDirectory(prefix=".company-edition-", dir=destination.parent) as tmp:
        stage = Path(tmp)
        (stage / "company").mkdir(mode=0o700)
        store = CompanyStore(stage / "company")
        with store._db() as target:
            schema = {table: _columns(target, table) for table in CORE_TABLES}
        for item, before in selected:
            path = Path(before["path"])
            require(stamp(path) == tuple(before["stamp"]), "Source changed before native read")
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as source:
                source.row_factory = sqlite3.Row
                source.execute("PRAGMA query_only=ON")
                source.execute("PRAGMA trusted_schema=OFF")
                source.execute("BEGIN")
                require(all(_columns(source, table) == schema[table] for table in CORE_TABLES),
                        "Exact application-owned native table schema required")
                counts = {table: source.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                          for table in CORE_TABLES}
                require(counts["systems"] == item["systems"] and counts["versions"] == item["versions"],
                        "Selected native counts differ")
                local_systems = set()
                for row in source.execute("SELECT " + ",".join(SYSTEM_FIELDS)
                                          + " FROM systems ORDER BY company,branch,system"):
                    values = tuple(row)
                    for value in values:
                        _id(value)
                    key = values[:3]
                    require(key not in systems or systems[key] == values,
                            "Conflicting registered source owner")
                    systems[key] = values
                    local_systems.add(key)
                previous = {}
                for row in source.execute("SELECT " + ",".join(VERSION_FIELDS)
                                          + " FROM versions ORDER BY company,branch,system,record,version"):
                    _version(row, local_systems, previous)
                    values = tuple(row)
                    key = values[:5]
                    require(key not in versions, "Duplicate native record/version identity")
                    require(row["command_id"] not in commands, "Conflicting native command identity")
                    commands.add(row["command_id"])
                    versions[key] = values
                    seen_bytes += len(row["content"]) + len(row["provenance"].encode())
                    require(seen_bytes <= MAX_JOB_BYTES and len(versions) <= MAX_VERSIONS
                            and len(systems) <= MAX_SYSTEMS, "Source edition native quota exceeded")
                require(source.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                        and source.execute("PRAGMA foreign_key_check").fetchone() is None,
                        "Source database integrity differs")
                summaries.append({"id": item["id"], "database": before,
                                  "selected_counts": {k: counts[k] for k in ("systems", "versions")},
                                  "operational_authority_rows_not_transferred": {k: counts[k] for k in
                                                                            ("grants", "collections", "access_events")},
                                  "native_table_sha256": native_fingerprints(source)})
            require(database_pin(path, before["sha256"]) == before,
                    "Source changed during native read")
        with store._db() as target:
            target.execute("BEGIN IMMEDIATE")
            for values in sorted(systems.values()):
                target.execute("INSERT INTO systems VALUES(?,?,?,?)", values)
            previous = {}
            all_systems = set(systems)
            for key, values in sorted(versions.items()):
                row = dict(zip(VERSION_FIELDS, values, strict=True))
                _version(row, all_systems, previous)
                target.execute("INSERT INTO versions VALUES(" + ",".join("?" for _ in VERSION_FIELDS)
                               + ")", values)
            require(target.execute("PRAGMA foreign_key_check").fetchone() is None,
                    "Published source foreign-key mismatch")
        with store._db() as target:
            require(target.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                    "Published source integrity mismatch")
            actual_systems = [tuple(r) for r in target.execute(
                "SELECT " + ",".join(SYSTEM_FIELDS) + " FROM systems ORDER BY company,branch,system")]
            actual_versions = [tuple(r) for r in target.execute(
                "SELECT " + ",".join(VERSION_FIELDS) + " FROM versions ORDER BY company,branch,system,record,version")]
            require(actual_systems == sorted(systems.values())
                    and actual_versions == [v for k, v in sorted(versions.items())],
                    "Every native scalar and original body must remain exact")
            require(all(target.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
                        for table in ("grants", "collections", "access_events")),
                    "Source authority or collections transferred")
            fingerprints = native_fingerprints(target)
        receipt = {"schema": SCHEMA, "status": "NATIVE_SOURCE_EDITION_PUBLISHED_NOT_ASSESSED",
                   "started_at": started, "published_at": _now(), "components": summaries,
                   "native_fields_preserved": list(VERSION_FIELDS),
                   "native_table_sha256": fingerprints,
                   "native_counts": {"systems": len(systems), "versions": len(versions)},
                   "input_operational_ledgers_and_files_must_be_retained": True,
                   "source_snapshot_boundary": "PER_COMPONENT_TRANSACTIONS_WITH_GLOBAL_CLOSING_IDENTITIES_AND_TRUSTED_WRITER_QUIESCENCE",
                   "publication_atomic_to_concurrent_readers": False,
                   "original_operational_workflow_tables_copied": False,
                   "audit_created": False, "grants_created": False, "assessment_credit": False,
                   "coherent_operating_year_or_whole_estate_completeness": False,
                   "qualification": "EXACT_SELECTED_COMPANY_SOURCE_EDITION_REQUIRES_INDEPENDENT_ADMISSION",
                   "code_pins": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                 for name in ("company_source_edition.py", "company_runtime_activation.py",
                                              "company_store.py", "company_activity_plan_sources.py",
                                              "private_publication.py")}}
        _write(stage / "SOURCE_EDITION.json", _bytes(receipt))
        _sealed_sidecars(store.path)
        manifest = {"format": "PRIVATE_COMPANY_ACTIVITY_RUN_V1", "source_edition_schema": SCHEMA,
                    "audit_created": False, "grants_created": False,
                    "counts": {"systems": len(systems), "versions": len(versions),
                               "grants": 0, "collections": 0, "access_events": 0},
                    "members": {name: hashlib.sha256((stage / name).read_bytes()).hexdigest()
                                for name in ("company/company.sqlite3", "SOURCE_EDITION.json")}}
        _write(stage / "MANIFEST.json", _bytes(manifest))
        manifest_sha = hashlib.sha256((stage / "MANIFEST.json").read_bytes()).hexdigest()
        _manifest(stage / "MANIFEST.json", manifest_sha, stage / "company")
        for _, before in selected:
            require(database_pin(Path(before["path"]), before["sha256"]) == before,
                    "Closing original source pin changed")
        for _, before in selected:
            path = Path(before["path"])
            require(stamp(path) == tuple(before["stamp"]),
                    "Global closing source identity changed")
            _sealed_sidecars(path)
        publish(stage, destination)
    return {"path": str(destination / "MANIFEST.json"), "sha256": manifest_sha}
