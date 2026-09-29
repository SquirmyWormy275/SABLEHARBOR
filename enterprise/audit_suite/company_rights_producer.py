"""Explicit portal authority for the private Daedalus company-rights gateway.

This module creates no grants from audit roles, CompanyStore grants, or the
public personnel census. A trusted operator must bind each authenticated audit
principal to a real synthetic company person and purpose, then register every
exact policy record and its explicit grants. The checkpoint belongs in a
separate private root that is never restored with the rights database.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from .store import Store, canonical

AUDIENCE = "ALEXANDRIA_DAEDALUS_COMPANY_RECORDS"
ISSUER = "SABLEHARBOR_AUDIT_PORTAL_COMPANY_RIGHTS_V1"
WINDOW = timedelta(minutes=5)
DISCLOSURE_ACTIONS = frozenset(
    {
        "read",
        "search",
        "snippet",
        "citation",
        "count",
        "graph",
        "vector",
        "tool_result",
        "answer",
        "export",
        "memory",
        "existence",
    }
)
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class RightsUnavailable(ValueError):
    """The producer cannot make an authoritative current assertion."""


def _text(value: object) -> str:
    if not isinstance(value, str) or not IDENTITY.fullmatch(value):
        raise RightsUnavailable("Explicit valid identity required")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise RightsUnavailable("Exact SHA-256 required")
    return value


def _path(value: object) -> str:
    if not isinstance(value, str) or "\\" in value or not value:
        raise RightsUnavailable("Repository-relative source path required")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise RightsUnavailable("Repository-relative source path required")
    return value


def _private_root(path: Path) -> Path:
    path = Path(path).absolute()
    if (
        not path.is_dir()
        or any(part.is_symlink() for part in (path, *path.parents))
        or path.stat().st_mode & 0o077
    ):
        raise RightsUnavailable("Existing private 0700 root required")
    return path


def _instant(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat(timespec="microseconds")


def pinned_git_source_reader(repository: Path, source_commit: str) -> Callable[[str], bytes]:
    """Read exact tracked bytes at the asserted public source commit."""
    repository = Path(repository).absolute()
    if not repository.is_dir() or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise RightsUnavailable("Pinned source repository and commit required")

    def read(path: str) -> bytes:
        path = _path(path)
        try:
            result = subprocess.run(
                ["git", "-C", str(repository), "show", f"{source_commit}:{path}"],
                capture_output=True,
                check=True,
                timeout=10,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RightsUnavailable("Pinned source unavailable") from exc
        if len(result.stdout) > 25 * 1024 * 1024:
            raise RightsUnavailable("Pinned source exceeds producer limit")
        return result.stdout

    return read


class CompanyRightsProducer:
    """Persistent rights revision plus an independently read restore checkpoint.

    ``source_bytes`` and ``validate_record`` are trusted server code, never a
    request body or model tool. The former must return the exact pinned source
    bytes for a repository-relative path; the latter is the accepted company
    information-policy validator. Both are called again before each snapshot.
    """

    def __init__(
        self,
        *,
        store: Store,
        rights_root: Path,
        checkpoint_root: Path,
        policy_file: Path,
        policy_sha256: str,
        source_commit: str,
        source_bytes: Callable[[str], bytes],
        validate_record: Callable[[dict], dict],
        decide: Callable[..., str],
        known_person_ids: frozenset[str],
    ):
        self.store = store
        self.rights_root = _private_root(rights_root)
        self.checkpoint_root = _private_root(checkpoint_root)
        if (
            self.rights_root == self.checkpoint_root
            or self.rights_root in self.checkpoint_root.parents
            or self.checkpoint_root in self.rights_root.parents
        ):
            raise RightsUnavailable("Checkpoint must have an independent restore root")
        self.policy_file = Path(policy_file).absolute()
        self.policy_sha256 = _sha(policy_sha256)
        if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise RightsUnavailable("Exact source commit required")
        self.source_commit = source_commit
        if not callable(source_bytes) or not callable(validate_record) or not callable(decide):
            raise RightsUnavailable("Trusted policy and source readers required")
        self.source_bytes = source_bytes
        self.validate_record = validate_record
        self.decide = decide
        if (
            not isinstance(known_person_ids, frozenset)
            or not known_person_ids
            or any(
                not isinstance(person, str) or not IDENTITY.fullmatch(person)
                for person in known_person_ids
            )
        ):
            raise RightsUnavailable("Trusted company person population required")
        self.known_person_ids = known_person_ids
        self.rights_db = self.rights_root / "company-rights.sqlite3"
        self.checkpoint_db = self.checkpoint_root / "company-rights-checkpoint.sqlite3"
        self.lock_path = self.checkpoint_root / "company-rights.lock"
        self._check_policy()
        with self._locked():
            with self._db(self.rights_db) as db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS state(revision INTEGER NOT NULL);
                    INSERT INTO state SELECT 0 WHERE NOT EXISTS(SELECT 1 FROM state);
                    CREATE TABLE IF NOT EXISTS bindings(
                      principal TEXT NOT NULL, engagement TEXT NOT NULL,
                      person_id TEXT NOT NULL, tenant TEXT NOT NULL, purpose TEXT NOT NULL,
                      PRIMARY KEY(principal,engagement));
                    CREATE TABLE IF NOT EXISTS records(
                      record_id TEXT PRIMARY KEY, repository_path TEXT UNIQUE NOT NULL,
                      source_sha256 TEXT NOT NULL, policy_row TEXT NOT NULL);
                """)
            with self._db(self.checkpoint_db) as db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS state(
                      epoch INTEGER NOT NULL,rights_revision INTEGER NOT NULL);
                    INSERT INTO state SELECT 0,0 WHERE NOT EXISTS(SELECT 1 FROM state);
                    CREATE TABLE IF NOT EXISTS revoked(person_id TEXT PRIMARY KEY);
                    CREATE TABLE IF NOT EXISTS tombstones(record_id TEXT PRIMARY KEY);
                    CREATE TABLE IF NOT EXISTS holds(record_id TEXT PRIMARY KEY);
                """)

    @contextmanager
    def _locked(self):
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @contextmanager
    def _db(self, path: Path):
        if path.is_symlink() or (path.exists() and path.stat().st_mode & 0o077):
            raise RightsUnavailable("Private rights database required")
        db = sqlite3.connect(path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
            os.chmod(path, 0o600)

    def _check_policy(self):
        if (
            self.policy_file.is_symlink()
            or not self.policy_file.is_file()
            or hashlib.sha256(self.policy_file.read_bytes()).hexdigest() != self.policy_sha256
        ):
            raise RightsUnavailable("Accepted information policy pin unavailable")

    @staticmethod
    def _revision(db):
        rows = db.execute("SELECT revision FROM state").fetchall()
        if len(rows) != 1 or type(rows[0][0]) is not int or rows[0][0] < 0:
            raise RightsUnavailable("Rights revision unavailable")
        return rows[0][0]

    @staticmethod
    def _checkpoint(db):
        rows = db.execute("SELECT epoch,rights_revision FROM state").fetchall()
        if len(rows) != 1 or any(type(value) is not int or value < 0 for value in rows[0]):
            raise RightsUnavailable("Revocation checkpoint unavailable")
        return rows[0][0], rows[0][1]

    def _mutate_rights(
        self, expected_revision: int, action: Callable[[sqlite3.Connection], None]
    ) -> int:
        if type(expected_revision) is not int or expected_revision < 0:
            raise RightsUnavailable("Expected rights revision required")
        with self._locked():
            with self._db(self.rights_db) as rights, self._db(self.checkpoint_db) as checkpoint:
                rights.execute("BEGIN IMMEDIATE")
                checkpoint.execute("BEGIN IMMEDIATE")
                current = self._revision(rights)
                _, high_water = self._checkpoint(checkpoint)
                if current != expected_revision or high_water != current:
                    raise RightsUnavailable("Rights revision changed or restored")
                action(rights)
                rights.execute("UPDATE state SET revision=?", (current + 1,))
                checkpoint.execute(
                    "UPDATE state SET rights_revision=?,epoch=epoch+1", (current + 1,)
                )
                # A rights commit without its high-water mark fails closed on
                # all later snapshots; no old revision is ever accepted.
                rights.commit()
                checkpoint.commit()
                return current + 1

    def bind_person(
        self,
        *,
        principal_id: str,
        engagement_id: str,
        person_id: str,
        tenant: str,
        purpose: str,
        expected_revision: int,
    ) -> int:
        principal_id, engagement_id = _text(principal_id), _text(engagement_id)
        person_id, tenant, purpose = _text(person_id), _text(tenant), _text(purpose)
        if person_id not in self.known_person_ids:
            raise RightsUnavailable("Company person absent from trusted population")
        with self.store.connect() as db:
            self.store._authorize(db, principal_id, engagement_id)

        def write(db):
            db.execute(
                "INSERT INTO bindings VALUES(?,?,?,?,?) ON CONFLICT(principal,engagement) "
                "DO UPDATE SET person_id=excluded.person_id,"
                "tenant=excluded.tenant,purpose=excluded.purpose",
                (principal_id, engagement_id, person_id, tenant, purpose),
            )

        return self._mutate_rights(expected_revision, write)

    def put_record(self, row: dict, *, expected_revision: int) -> int:
        if not isinstance(row, dict):
            raise RightsUnavailable("Exact policy record required")
        row = copy.deepcopy(row)
        record_id = _text(row.get("record_id"))
        path = _path(row.get("repository_path"))
        expected_hash = _sha(row.get("source_sha256"))
        self._check_policy()
        try:
            if hashlib.sha256(self.source_bytes(path)).hexdigest() != expected_hash:
                raise RightsUnavailable("Source bytes changed")
            self.validate_record(row)
        except Exception as exc:
            raise RightsUnavailable("Policy record or source unavailable") from exc

        def write(db):
            db.execute(
                "INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(record_id) "
                "DO UPDATE SET repository_path=excluded.repository_path,"
                "source_sha256=excluded.source_sha256,policy_row=excluded.policy_row",
                (record_id, path, expected_hash, canonical(row)),
            )

        try:
            return self._mutate_rights(expected_revision, write)
        except sqlite3.IntegrityError as exc:
            raise RightsUnavailable("Duplicate source path") from exc

    def _checkpoint_change(self, table: str, key: str, active: bool) -> int:
        if table not in {"revoked", "tombstones", "holds"} or type(active) is not bool:
            raise RightsUnavailable("Explicit lifecycle transition required")
        key = _text(key)
        with self._locked():
            with self._db(self.rights_db) as rights, self._db(self.checkpoint_db) as checkpoint:
                checkpoint.execute("BEGIN IMMEDIATE")
                epoch, high_water = self._checkpoint(checkpoint)
                if high_water != self._revision(rights):
                    raise RightsUnavailable("Rights revision changed or restored")
                if (
                    table != "revoked"
                    and not rights.execute(
                        "SELECT 1 FROM records WHERE record_id=?", (key,)
                    ).fetchone()
                ):
                    raise RightsUnavailable("Unknown policy record")
                if table == "tombstones" and not active:
                    raise RightsUnavailable("Tombstones survive restoration")
                if active:
                    checkpoint.execute(f"INSERT OR IGNORE INTO {table} VALUES(?)", (key,))
                else:
                    column = "person_id" if table == "revoked" else "record_id"
                    checkpoint.execute(
                        f"DELETE FROM {table} WHERE {column}=?",
                        (key,),
                    )
                checkpoint.execute("UPDATE state SET epoch=?", (epoch + 1,))
                return epoch + 1

    def set_person_revoked(self, person_id: str, *, revoked: bool) -> int:
        if person_id not in self.known_person_ids:
            raise RightsUnavailable("Unknown company person")
        return self._checkpoint_change("revoked", person_id, revoked)

    def delete_record(self, record_id: str) -> int:
        return self._checkpoint_change("tombstones", record_id, True)

    def set_hold(self, record_id: str, *, held: bool) -> int:
        return self._checkpoint_change("holds", record_id, held)

    def record_restore(self, record_id: str) -> int:
        """Advance the epoch; a restored older copy cannot clear a tombstone."""
        key = _text(record_id)
        with self._locked():
            with self._db(self.rights_db) as rights, self._db(self.checkpoint_db) as checkpoint:
                checkpoint.execute("BEGIN IMMEDIATE")
                epoch, high_water = self._checkpoint(checkpoint)
                if high_water != self._revision(rights):
                    raise RightsUnavailable("Rights revision changed or restored")
                if not rights.execute("SELECT 1 FROM records WHERE record_id=?", (key,)).fetchone():
                    raise RightsUnavailable("Unknown policy record")
                checkpoint.execute("UPDATE state SET epoch=?", (epoch + 1,))
                return epoch + 1

    def checkpoint(self) -> dict:
        with self._locked():
            with self._db(self.rights_db) as rights, self._db(self.checkpoint_db) as db:
                epoch, high_water = self._checkpoint(db)
                if high_water != self._revision(rights):
                    raise RightsUnavailable("Rights revision changed or restored")
                revoked = [
                    r[0] for r in db.execute("SELECT person_id FROM revoked ORDER BY person_id")
                ]
                tombstones = [
                    r[0] for r in db.execute("SELECT record_id FROM tombstones ORDER BY record_id")
                ]
        now = datetime.now(UTC)
        return {
            "epoch": f"epoch-{epoch}",
            "as_of": now.isoformat(),
            "expires_at": (now + WINDOW).isoformat(),
            "revoked_ids": revoked,
            "tombstones": tombstones,
        }

    def snapshot(self, *, session_token: str, engagement_id: str) -> dict:
        """Fresh assertion for one verified portal browser session and engagement."""
        self._check_policy()
        session = self.store.authenticated_company_session(session_token, _text(engagement_id))
        with self._locked():
            with self._db(self.rights_db) as rights, self._db(self.checkpoint_db) as checkpoint:
                revision = self._revision(rights)
                epoch, high_water = self._checkpoint(checkpoint)
                if revision != high_water:
                    raise RightsUnavailable("Rights revision changed or restored")
                binding = rights.execute(
                    "SELECT person_id,tenant,purpose FROM bindings "
                    "WHERE principal=? AND engagement=?",
                    (session["principal_id"], engagement_id),
                ).fetchone()
                if not binding or binding["person_id"] not in self.known_person_ids:
                    raise RightsUnavailable("Explicit company identity binding unavailable")
                records = {}
                for stored in rights.execute("SELECT * FROM records ORDER BY record_id"):
                    row = json.loads(stored["policy_row"])
                    if (
                        row.get("record_id") != stored["record_id"]
                        or row.get("repository_path") != stored["repository_path"]
                        or row.get("source_sha256") != stored["source_sha256"]
                    ):
                        raise RightsUnavailable("Policy row changed")
                    try:
                        self.validate_record(row)
                        source = self.source_bytes(_path(stored["repository_path"]))
                    except Exception as exc:
                        raise RightsUnavailable("Source or policy unavailable") from exc
                    if (
                        not isinstance(source, bytes)
                        or hashlib.sha256(source).hexdigest() != stored["source_sha256"]
                    ):
                        raise RightsUnavailable("Source bytes changed")
                    records[stored["record_id"]] = row
                if not records:
                    raise RightsUnavailable("No classified company records")
                revoked = {r[0] for r in checkpoint.execute("SELECT person_id FROM revoked")}
                holds = {r[0] for r in checkpoint.execute("SELECT record_id FROM holds")}
                if binding["person_id"] in revoked:
                    raise RightsUnavailable("Company person revoked")
                for key in holds:
                    if key in records:
                        records[key]["legal_hold"] = True
        # Membership and session revocation are checked again after source work.
        if self.store.authenticated_company_session(session_token, engagement_id) != session:
            raise RightsUnavailable("Authentication changed during snapshot")
        self._check_policy()
        now = datetime.now(UTC)
        if session["expires_at"] <= now.timestamp():
            raise RightsUnavailable("Session expired")
        return {
            "issuer": ISSUER,
            "audience": AUDIENCE,
            "source_commit": self.source_commit,
            "policy_sha256": self.policy_sha256,
            "rights_revision": f"revision-{revision}",
            "revocation_epoch": f"epoch-{epoch}",
            "issued_at": now.isoformat(),
            "expires_at": (now + WINDOW).isoformat(),
            "assertion": {
                "id": binding["person_id"],
                "tenant": binding["tenant"],
                "purpose": binding["purpose"],
                "engagement_id": engagement_id,
                "session_id": session["session_id"],
                "authenticated_at": _instant(session["authenticated_at"]),
                "expires_at": _instant(session["expires_at"]),
                "revoked": False,
            },
            "records": records,
        }

    def authorize_disclosure(
        self,
        *,
        session_token: str,
        engagement_id: str,
        path: str,
        content: bytes,
        action: str,
    ) -> str:
        """Check one exact source before a portal response or model context."""
        if (
            not isinstance(action, str)
            or action not in DISCLOSURE_ACTIONS
            or not isinstance(content, bytes)
        ):
            raise RightsUnavailable("Company disclosure unavailable")
        path = _path(path)
        snapshot = self.snapshot(session_token=session_token, engagement_id=engagement_id)
        checkpoint = self.checkpoint()
        if snapshot["revocation_epoch"] != checkpoint["epoch"]:
            raise RightsUnavailable("Company rights changed")
        digest = hashlib.sha256(content).hexdigest()
        matching = [
            key
            for key, row in snapshot["records"].items()
            if row["repository_path"] == path and row["source_sha256"] == digest
        ]
        if len(matching) != 1:
            raise RightsUnavailable("Company disclosure unavailable")
        record_id = matching[0]
        subject = {key: snapshot["assertion"][key] for key in ("id", "tenant", "purpose")}
        now = datetime.now(UTC).isoformat()
        try:
            outcome = self.decide(
                snapshot["records"],
                record_id,
                subject,
                action,
                now,
                revoked_ids=checkpoint["revoked_ids"],
                tombstones=checkpoint["tombstones"],
            )
        except Exception as exc:
            raise RightsUnavailable("Company disclosure unavailable") from exc
        if outcome != "ALLOW":
            raise RightsUnavailable("Company disclosure unavailable")
        after = self.snapshot(session_token=session_token, engagement_id=engagement_id)
        latest = self.checkpoint()
        if (
            after["rights_revision"] != snapshot["rights_revision"]
            or after["revocation_epoch"] != snapshot["revocation_epoch"]
            or latest["epoch"] != checkpoint["epoch"]
        ):
            raise RightsUnavailable("Company rights changed")
        return record_id

    def visible_population(
        self,
        *,
        session_token: str,
        engagement_id: str,
        candidates: list[dict],
        action: str,
        complete: bool,
    ) -> list[dict]:
        """Filter a complete candidate set before snippets, ranking, paging or counts."""
        if complete is not True or not isinstance(candidates, list):
            raise RightsUnavailable("Complete source population required")
        start = self.snapshot(session_token=session_token, engagement_id=engagement_id)
        result = []
        for candidate in candidates:
            if (
                not isinstance(candidate, dict)
                or set(candidate) != {"path", "content"}
                or not isinstance(candidate["content"], bytes)
            ):
                raise RightsUnavailable("Exact source candidate required")
            try:
                self.authorize_disclosure(
                    session_token=session_token,
                    engagement_id=engagement_id,
                    path=candidate["path"],
                    content=candidate["content"],
                    action=action,
                )
            except RightsUnavailable:
                continue
            result.append(candidate)
        end = self.snapshot(session_token=session_token, engagement_id=engagement_id)
        if (
            end["rights_revision"] != start["rights_revision"]
            or end["revocation_epoch"] != start["revocation_epoch"]
        ):
            raise RightsUnavailable("Company rights changed")
        return result
