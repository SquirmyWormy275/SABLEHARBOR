"""Private company history independent of engagements.

This is a trusted local operator adapter, not an HTTP authorization boundary.
Only an authenticated operator may register, append, grant or revoke. Read callers
must receive principal, engagement and simulated as-of from the trusted service.
No scenario truth or rubric belongs in this store. Branches are explicit identities;
there is no implicit inheritance or fallback to another branch.
"""

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class CompanyStoreError(ValueError):
    """Invalid, conflicting, unavailable or unauthorized company operation."""


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise CompanyStoreError("Invalid identity")
    return value


def _time(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        return stamp.astimezone(UTC).isoformat(timespec="microseconds")
    except (ValueError, TypeError, AttributeError) as error:
        raise CompanyStoreError("Explicit timestamp offset required") from error


def _now():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as error:
        raise CompanyStoreError("Invalid provenance") from error


class CompanyStore:
    """Single private SQLite source and collection journal, bounded to 25 MiB/version."""

    def __init__(self, private_root: Path):
        root = Path(private_root).absolute()
        if any(p.is_symlink() for p in [root, *root.parents]):
            raise CompanyStoreError("Source directory aliases are forbidden")
        if not root.is_dir() or root.stat().st_mode & 0o077:
            raise CompanyStoreError("Existing private 0700 directory required")
        self.path = root / "company.sqlite3"
        if self.path.exists() and (not self.path.is_file() or self.path.stat().st_mode & 0o077):
            raise CompanyStoreError("Private regular database required")
        if self.path.is_symlink():
            raise CompanyStoreError("Database alias forbidden")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS systems(
                  company TEXT, branch TEXT, system TEXT, owner TEXT NOT NULL,
                  PRIMARY KEY(company,branch,system));
                CREATE TABLE IF NOT EXISTS versions(
                  company TEXT, branch TEXT, system TEXT, record TEXT, version INTEGER,
                  event_at TEXT, available_at TEXT NOT NULL, imported_at TEXT NOT NULL,
                  origin TEXT NOT NULL, provenance TEXT NOT NULL, content BLOB NOT NULL,
                  sha256 TEXT NOT NULL, command_id TEXT UNIQUE NOT NULL, input_digest TEXT NOT NULL,
                  PRIMARY KEY(company,branch,system,record,version),
                  FOREIGN KEY(company,branch,system) REFERENCES systems(company,branch,system));
                CREATE TABLE IF NOT EXISTS grants(
                  principal TEXT, engagement TEXT, company TEXT, branch TEXT, system TEXT,
                  active INTEGER NOT NULL,
                  PRIMARY KEY(principal,engagement,company,branch,system));
                CREATE TABLE IF NOT EXISTS access_events(
                  id INTEGER PRIMARY KEY, principal TEXT, engagement TEXT, company TEXT,
                  branch TEXT, system TEXT, active INTEGER, recorded_at TEXT);
                CREATE TABLE IF NOT EXISTS collections(
                  command_id TEXT PRIMARY KEY, input_digest TEXT NOT NULL, receipt TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS no_version_update BEFORE UPDATE ON versions
                  BEGIN SELECT RAISE(ABORT,'Immutable source'); END;
                CREATE TRIGGER IF NOT EXISTS no_version_delete BEFORE DELETE ON versions
                  BEGIN SELECT RAISE(ABORT,'Immutable source'); END;
                CREATE TRIGGER IF NOT EXISTS no_collection_update BEFORE UPDATE ON collections
                  BEGIN SELECT RAISE(ABORT,'Immutable collection'); END;
                CREATE TRIGGER IF NOT EXISTS no_collection_delete BEFORE DELETE ON collections
                  BEGIN SELECT RAISE(ABORT,'Immutable collection'); END;
            """)

    @contextmanager
    def _db(self):
        if (
            any(p.is_symlink() for p in [self.path, *self.path.parents])
            or self.path.stat().st_mode & 0o077
        ):
            raise CompanyStoreError("Private database required")
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _key(company_id, branch_id, system_id):
        return tuple(_id(v) for v in (company_id, branch_id, system_id))

    def register_system(self, company_id, branch_id, system_id, owner_id):
        """Trusted operator registration; changing owner requires a future versioned API."""
        key = self._key(company_id, branch_id, system_id)
        owner = _id(owner_id)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?", key
            ).fetchone()
            if old and old[0] != owner:
                raise CompanyStoreError("System registration conflict")
            db.execute("INSERT OR IGNORE INTO systems VALUES(?,?,?,?)", (*key, owner))

    def append_version(
        self,
        company_id,
        branch_id,
        system_id,
        record_id,
        *,
        expected_version,
        command_id,
        event_at,
        available_at,
        content,
        provenance,
        origin="AUTHORED_TRAINING_SOURCE",
    ):
        """Append correction with optimistic concurrency; imported_at is always real time."""
        key = (*self._key(company_id, branch_id, system_id), _id(record_id))
        command = _id(command_id)
        if type(expected_version) is not int or expected_version < 0:
            raise CompanyStoreError("Nonnegative expected version required")
        if not isinstance(content, bytes) or not 0 < len(content) <= 25 * 1024 * 1024:
            raise CompanyStoreError("Source bytes must be between 1 byte and 25 MiB")
        if origin not in {
            "AUTHORED_TRAINING_SOURCE",
            "MIGRATED_SYNTHETIC_HISTORY",
            "REPOSITORY_SYNTHETIC_DOCUMENT",
        }:
            raise CompanyStoreError("Explicit synthetic source origin required")
        if not isinstance(provenance, dict) or not provenance.get("source_reference"):
            raise CompanyStoreError("Source reference provenance required")
        provenance_json = _json(provenance)
        if len(provenance_json.encode()) > 65536:
            raise CompanyStoreError("Provenance too large")
        event = (
            None
            if event_at is None
            and origin in {"MIGRATED_SYNTHETIC_HISTORY", "REPOSITORY_SYNTHETIC_DOCUMENT"}
            else _time(event_at)
        )
        available = _time(available_at)
        if event is not None and available < event:
            raise CompanyStoreError("Record availability cannot precede business event")
        sha = hashlib.sha256(content).hexdigest()
        fingerprint = hashlib.sha256(
            _json([key, expected_version, event, available, origin, provenance, sha]).encode()
        ).hexdigest()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM versions WHERE command_id=?", (command,)).fetchone()
            if prior:
                if prior["input_digest"] != fingerprint:
                    raise CompanyStoreError("Import idempotency conflict")
                return self._metadata(prior)
            current = db.execute(
                "SELECT COALESCE(MAX(version),0) FROM versions WHERE company=? "
                "AND branch=? AND system=? AND record=?",
                key,
            ).fetchone()[0]
            if current != expected_version:
                raise CompanyStoreError("Source version conflict")
            imported = _now()
            try:
                db.execute(
                    "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        *key,
                        current + 1,
                        event,
                        available,
                        imported,
                        origin,
                        provenance_json,
                        content,
                        sha,
                        command,
                        fingerprint,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise CompanyStoreError("Registered source system required") from error
            row = db.execute("SELECT * FROM versions WHERE command_id=?", (command,)).fetchone()
            return self._metadata(row)

    def grant(self, principal_id, engagement_id, company_id, branch_id, system_id, *, active=True):
        """Trusted operator only. Revocation remains effective against exact receipt replays."""
        key = self._key(company_id, branch_id, system_id)
        principal, engagement = _id(principal_id), _id(engagement_id)
        if type(active) is not bool:
            raise CompanyStoreError("Boolean access state required")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute(
                "SELECT 1 FROM systems WHERE company=? AND branch=? AND system=?", key
            ).fetchone():
                raise CompanyStoreError("Registered source system required")
            db.execute(
                "INSERT INTO grants VALUES(?,?,?,?,?,?) "
                "ON CONFLICT DO UPDATE SET active=excluded.active",
                (principal, engagement, *key, int(active)),
            )
            db.execute(
                "INSERT INTO access_events VALUES(NULL,?,?,?,?,?,?,?)",
                (principal, engagement, *key, int(active), _now()),
            )

    @staticmethod
    def _metadata(row):
        return {
            k: (json.loads(row[k]) if k == "provenance" else row[k])
            for k in (
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
                "sha256",
            )
        }

    def _read(self, db, principal_id, engagement_id, key, version, as_of):
        principal, engagement = _id(principal_id), _id(engagement_id)
        if type(version) is not int or version < 1:
            raise CompanyStoreError("Exact positive source version required")
        allowed = db.execute(
            "SELECT active FROM grants WHERE principal=? AND engagement=? "
            "AND company=? AND branch=? AND system=?",
            (principal, engagement, *key[:3]),
        ).fetchone()
        if not allowed or not allowed[0]:
            raise CompanyStoreError("Source unavailable or unauthorized")
        row = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=? AND available_at<=? AND (event_at IS NULL OR event_at<=?)",
            (*key, version, as_of, as_of),
        ).fetchone()
        if not row:
            raise CompanyStoreError("Source unavailable or unauthorized")
        if hashlib.sha256(row["content"]).hexdigest() != row["sha256"]:
            raise CompanyStoreError("Source integrity failure")
        return row

    def list_systems(self, principal_id, engagement_id, company_id, branch_id):
        """Discover registered systems with an active exact engagement/branch grant."""
        principal, engagement, company, branch = (
            _id(v) for v in (principal_id, engagement_id, company_id, branch_id)
        )
        with self._db() as db:
            rows = db.execute(
                "SELECT s.system,s.owner FROM systems s JOIN grants g "
                "ON s.company=g.company AND s.branch=g.branch AND s.system=g.system "
                "WHERE g.principal=? AND g.engagement=? AND g.company=? AND g.branch=? "
                "AND g.active=1 ORDER BY s.system",
                (principal, engagement, company, branch),
            ).fetchall()
            return {"systems": [{"system": row["system"], "owner": row["owner"]} for row in rows]}

    def list_records(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        *,
        as_of,
        after_record=None,
        limit=100,
    ):
        """Discover latest available exact version per record, keyset paginated (max 1000).

        Returns metadata only. A later unavailable correction does not hide an earlier
        available version. Unknown migrated event dates remain explicitly null.
        """
        key = self._key(company_id, branch_id, system_id)
        principal, engagement = _id(principal_id), _id(engagement_id)
        clock = _time(as_of)
        after = "" if after_record is None else _id(after_record)
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise CompanyStoreError("List limit must be 1..1000")
        with self._db() as db:
            db.execute("BEGIN")
            allowed = db.execute(
                "SELECT active FROM grants WHERE principal=? AND engagement=? "
                "AND company=? AND branch=? AND system=?",
                (principal, engagement, *key),
            ).fetchone()
            if not allowed or not allowed[0]:
                raise CompanyStoreError("Source unavailable or unauthorized")
            rows = db.execute(
                "SELECT v.* FROM versions v JOIN (SELECT record, MAX(version) version "
                "FROM versions WHERE company=? AND branch=? AND system=? AND record>? "
                "AND available_at<=? AND (event_at IS NULL OR event_at<=?) GROUP BY record "
                "ORDER BY record LIMIT ?) current ON v.record=current.record "
                "AND v.version=current.version WHERE v.company=? AND v.branch=? AND v.system=? "
                "ORDER BY v.record",
                (*key, after, clock, clock, limit + 1, *key),
            ).fetchall()
            return {
                "records": [self._metadata(row) for row in rows[:limit]],
                "next_after_record": rows[limit - 1]["record"] if len(rows) > limit else None,
            }

    def read_version(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        record_id,
        *,
        version,
        as_of,
    ):
        """Exact source retrieval; as_of is a server-authorized simulation clock."""
        key = (*self._key(company_id, branch_id, system_id), _id(record_id))
        with self._db() as db:
            db.execute("BEGIN")
            row = self._read(db, principal_id, engagement_id, key, version, _time(as_of))
            return {**self._metadata(row), "content": row["content"]}

    def collect(
        self,
        principal_id,
        engagement_id,
        company_id,
        branch_id,
        system_id,
        record_id,
        *,
        version,
        as_of,
        command_id,
    ):
        """Atomically retain collection provenance; no source mutation or new company fact."""
        key = (*self._key(company_id, branch_id, system_id), _id(record_id))
        command, clock = _id(command_id), _time(as_of)
        fingerprint = hashlib.sha256(
            _json([principal_id, engagement_id, key, version, clock]).encode()
        ).hexdigest()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._read(db, principal_id, engagement_id, key, version, clock)
            prior = db.execute(
                "SELECT * FROM collections WHERE command_id=?", (command,)
            ).fetchone()
            if prior:
                if prior["input_digest"] != fingerprint:
                    raise CompanyStoreError("Collection idempotency conflict")
                return json.loads(prior["receipt"])
            receipt = {
                "source": self._metadata(row),
                "principal_id": principal_id,
                "engagement_id": engagement_id,
                "collected_at": _now(),
                "simulated_as_of": clock,
                "command_id": command,
                "content_bytes": len(row["content"]),
            }
            db.execute(
                "INSERT INTO collections VALUES(?,?,?)", (command, fingerprint, _json(receipt))
            )
            return receipt
