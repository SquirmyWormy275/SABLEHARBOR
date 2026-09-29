"""Private, serialized engagement storage with scoped identities and replay receipts.

Only trusted application code receives this object. Neither HTTP payloads nor model
tools choose actors, permissions, recorded_at, or private storage paths. SQLite
provides one writer at a time; this is a local deployment, not a clustered store.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path


class DomainError(ValueError):
    def __init__(self, message: str, *, code: str = "INVALID", status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(12)}"


class _ClosingConnection(sqlite3.Connection):
    """Commit or roll back on context exit, then release the SQLite handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.stat().st_mode & 0o077:
            raise DomainError("Private store directory must have mode 0700")
        self.db_path = self.root / "engagements.sqlite3"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS principals (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, roles TEXT NOT NULL,
              token_hash TEXT UNIQUE NOT NULL, expires REAL NOT NULL,
              revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS sessions (
              token_hash TEXT PRIMARY KEY, principal TEXT NOT NULL REFERENCES principals(id),
              csrf TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS engagements (
              id TEXT PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS members (
              engagement TEXT NOT NULL REFERENCES engagements(id),
              principal TEXT NOT NULL REFERENCES principals(id), permission TEXT NOT NULL,
              PRIMARY KEY(engagement,principal));
            CREATE TABLE IF NOT EXISTS events (
              engagement TEXT NOT NULL REFERENCES engagements(id), revision INTEGER NOT NULL,
              command_id TEXT NOT NULL, request_hash TEXT NOT NULL, actor TEXT NOT NULL,
              recorded_at REAL NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL,
              state TEXT NOT NULL, command TEXT NOT NULL,
              PRIMARY KEY(engagement,revision), UNIQUE(engagement,command_id));
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
              BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
              BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
            """)
        os.chmod(self.db_path, 0o600)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=15, factory=_ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def provision(self, name: str, roles: list[str], *, lifetime: int = 86400) -> dict:
        """Trusted local operator provisioning; never called from anonymous HTTP."""
        if not roles or not set(roles) <= {"learner", "instructor", "reviewer", "admin"}:
            raise DomainError("Unknown principal role")
        if not 60 <= lifetime <= 86400 * 30:
            raise DomainError("Credential lifetime outside permitted range")
        key, person_id = secrets.token_urlsafe(32), identifier("USER")
        with self.connect() as db:
            db.execute(
                "INSERT INTO principals VALUES (?,?,?,?,?,0)",
                (person_id, name, canonical(roles), self._key_hash(key), time.time() + lifetime),
            )
        return {"id": person_id, "name": name, "roles": roles, "credential": key}

    @staticmethod
    def _key_hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def _principal(self, db: sqlite3.Connection, person_id: str) -> dict:
        p = db.execute("SELECT * FROM principals WHERE id=?", (person_id,)).fetchone()
        if not p or p["revoked"] or p["expires"] <= time.time():
            raise DomainError("Identity is expired or revoked", code="UNAUTHENTICATED", status=401)
        return {"id": p["id"], "display_name": p["name"], "roles": json.loads(p["roles"])}

    def authenticate(self, credential: str) -> dict:
        with self.connect() as db:
            p = db.execute(
                "SELECT id FROM principals WHERE token_hash=?", (self._key_hash(credential),)
            ).fetchone()
            if not p:
                raise DomainError("Invalid credential", code="UNAUTHENTICATED", status=401)
            return self._principal(db, p["id"])

    def login(self, credential: str) -> dict:
        p = self.authenticate(credential)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)",
                (self._key_hash(token), p["id"], csrf, time.time() + 3600),
            )
        return {"token": token, "csrf": csrf, "viewer": p}

    def session(self, token: str, *, csrf: str | None = None, mutation: bool = False) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE token_hash=?", (self._key_hash(token),)
            ).fetchone()
            if not row or row["expires"] <= time.time():
                raise DomainError("Session expired", code="UNAUTHENTICATED", status=401)
            if mutation and not hmac.compare_digest(row["csrf"], csrf or ""):
                raise DomainError("Invalid request token", code="CSRF", status=403)
            return {**self._principal(db, row["principal"]), "csrf_token": row["csrf"]}

    def logout(self, token: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (self._key_hash(token),))

    def revoke(self, person_id: str) -> None:
        """Trusted operator revocation, effective on every subsequent read/write."""
        with self.connect() as db:
            db.execute("UPDATE principals SET revoked=1 WHERE id=?", (person_id,))

    def grant(self, engagement_id: str, principal_id: str, permission: str) -> None:
        """Trusted operator membership grant; roles alone never grant engagement access."""
        if permission not in {"learn", "review", "instruct"}:
            raise DomainError("Invalid membership")
        with self.connect() as db:
            self._principal(db, principal_id)
            db.execute(
                "INSERT INTO members VALUES (?,?,?) ON CONFLICT(engagement,principal) "
                "DO UPDATE SET permission=excluded.permission",
                (engagement_id, principal_id, permission),
            )

    def _authorize(
        self,
        db: sqlite3.Connection,
        actor: str,
        engagement_id: str,
        permissions: set[str] | None = None,
    ) -> str:
        self._principal(db, actor)
        m = db.execute(
            "SELECT permission FROM members WHERE engagement=? AND principal=?",
            (engagement_id, actor),
        ).fetchone()
        if not m or (permissions is not None and m["permission"] not in permissions):
            raise DomainError(
                "Engagement unavailable for this identity", code="FORBIDDEN", status=403
            )
        return m["permission"]

    def create(self, actor: str, state: dict, command_id: str) -> dict:
        if not isinstance(command_id, str) or not 1 <= len(command_id) <= 128:
            raise DomainError("Creation requires a command ID of 1–128 characters")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            p = self._principal(db, actor)
            if not {"learner", "instructor"}.intersection(p["roles"]):
                raise DomainError("Identity cannot create training engagements", status=403)
            # Creation identity is stable across transport retries, scoped to this actor.
            engagement_id = "ENG-" + digest([actor, command_id])[:24]
            previous = db.execute(
                "SELECT state FROM events WHERE engagement=? AND revision=0", (engagement_id,)
            ).fetchone()
            if previous:
                existing = json.loads(previous["state"])
                if existing.get("creation_hash") != digest(state):
                    raise DomainError("Command ID already used for different input", status=409)
                return existing
            state = {
                **state,
                "id": engagement_id,
                "revision": 0,
                "created_by": actor,
                "creation_hash": digest(state),
                "origin": "SYNTHETIC",
            }
            db.execute(
                "INSERT INTO engagements VALUES (?,?,?)", (engagement_id, 0, canonical(state))
            )
            permission = "instruct" if "instructor" in p["roles"] else "learn"
            db.execute("INSERT INTO members VALUES (?,?,?)", (engagement_id, actor, permission))
            self._append(db, actor, state, command_id, {"kind": "engagement.create"}, "")
            return state

    def _append(
        self,
        db: sqlite3.Connection,
        actor: str,
        state: dict,
        command_id: str,
        command: dict,
        previous_hash: str,
    ) -> None:
        recorded_at = time.time()
        request_hash = digest(command)
        envelope = {
            "actor": actor,
            "recorded_at": recorded_at,
            "previous_hash": previous_hash,
            "state": state,
            "command": command,
            "command_id": command_id,
        }
        db.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                state["id"],
                state["revision"],
                command_id,
                request_hash,
                actor,
                recorded_at,
                previous_hash,
                digest(envelope),
                canonical(state),
                canonical(command),
            ),
        )

    def get(self, actor: str, engagement_id: str) -> dict:
        with self.connect() as db:
            self._authorize(db, actor, engagement_id)
            row = db.execute(
                "SELECT state FROM engagements WHERE id=?", (engagement_id,)
            ).fetchone()
            return json.loads(row["state"])

    def membership(self, actor: str, engagement_id: str) -> str:
        with self.connect() as db:
            return self._authorize(db, actor, engagement_id)

    def listing(self, actor: str) -> list[dict]:
        with self.connect() as db:
            self._principal(db, actor)
            return [
                json.loads(r["state"])
                for r in db.execute(
                    "SELECT e.state FROM engagements e JOIN members m ON e.id=m.engagement "
                    "WHERE m.principal=? ORDER BY e.rowid DESC",
                    (actor,),
                )
            ]

    def listing_summaries(self, actor: str) -> list[dict]:
        """Read navigation metadata without retaining complete engagement states.

        SQLite still reads/parses each accessible current state. Only the seven
        summary values cross into Python; no historical state or schema is changed.
        """
        fields = ("id", "title", "discipline", "mode", "phase", "revision", "simulated_at")
        with self.connect() as db:
            self._principal(db, actor)
            result = []
            try:
                rows = db.execute(
                    "SELECT e.id, e.revision, json_extract(e.state, "
                    "'$.id', '$.title', '$.discipline', '$.mode', '$.phase', "
                    "'$.revision', '$.simulated_at') AS summary "
                    "FROM engagements e JOIN members m ON e.id=m.engagement "
                    "WHERE m.principal=? ORDER BY e.rowid DESC",
                    (actor,),
                )
                for row in rows:
                    values = json.loads(row["summary"])
                    if (
                        len(values) != len(fields)
                        or any(type(values[i]) is not str for i in (0, 1, 2, 3, 4, 6))
                        or type(values[5]) is not int
                        or values[0] != row["id"]
                        or values[5] != row["revision"]
                    ):
                        raise DomainError(
                            "Invalid engagement summary", code="INVALID_STATE", status=500
                        )
                    result.append(dict(zip(fields, values, strict=True)))
            except sqlite3.OperationalError as exc:
                if "malformed JSON" not in str(exc):
                    raise
                raise DomainError(
                    "Invalid engagement summary", code="INVALID_STATE", status=500
                ) from exc
            return result

    @staticmethod
    def _validate_command(command: dict) -> None:
        if not isinstance(command, dict) or set(command) != {
            "command_id",
            "expected_revision",
            "kind",
            "payload",
        }:
            raise DomainError("Command requires only ID, expected revision, kind and payload")
        if (
            not isinstance(command["command_id"], str)
            or not 1 <= len(command["command_id"]) <= 128
            or type(command["expected_revision"]) is not int
            or command["expected_revision"] < 0
            or not isinstance(command["kind"], str)
            or not 1 <= len(command["kind"]) <= 128
            or not isinstance(command["payload"], dict)
        ):
            raise DomainError("Invalid command envelope")

    def _preflight(self, db, actor, engagement_id, command, permissions) -> dict | None:
        self._authorize(db, actor, engagement_id, permissions)
        duplicate = db.execute(
            "SELECT * FROM events WHERE engagement=? AND command_id=?",
            (engagement_id, command["command_id"]),
        ).fetchone()
        if duplicate:
            envelope = {
                "actor": duplicate["actor"],
                "recorded_at": duplicate["recorded_at"],
                "previous_hash": duplicate["previous_hash"],
                "state": json.loads(duplicate["state"]),
                "command": json.loads(duplicate["command"]),
                "command_id": duplicate["command_id"],
            }
            if (
                digest(envelope) != duplicate["hash"]
                or digest(envelope["command"]) != duplicate["request_hash"]
            ):
                raise DomainError("Replay receipt integrity failure", code="INTEGRITY", status=500)
            if duplicate["actor"] != actor or duplicate["request_hash"] != digest(command):
                raise DomainError(
                    "Command ID already used", code="IDEMPOTENCY_CONFLICT", status=409
                )
            return json.loads(duplicate["state"])
        row = db.execute("SELECT revision FROM engagements WHERE id=?", (engagement_id,)).fetchone()
        if row["revision"] != command["expected_revision"]:
            raise DomainError(
                "Engagement changed; reload before applying this edit",
                code="REVISION_CONFLICT",
                status=409,
            )
        return None

    def preflight(
        self, actor: str, engagement_id: str, command: dict, *, permissions: set[str]
    ) -> dict | None:
        """Replay an authorized receipt before expensive work; not a write reservation.

        The command transaction repeats all checks after inference or rendering,
        so a revoked identity or intervening revision still prevents mutation.
        """
        self._validate_command(command)
        with self.connect() as db:
            db.execute("BEGIN")
            return self._preflight(db, actor, engagement_id, command, permissions)

    def command(
        self,
        actor: str,
        engagement_id: str,
        command: dict,
        reducer: Callable[[dict, dict, str], dict],
        *,
        permissions: set[str],
    ) -> dict:
        self._validate_command(command)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            duplicate = self._preflight(db, actor, engagement_id, command, permissions)
            if duplicate is not None:
                return duplicate
            row = db.execute("SELECT * FROM engagements WHERE id=?", (engagement_id,)).fetchone()
            if row["revision"] != command["expected_revision"]:
                raise DomainError(
                    "Engagement changed; reload before applying this edit",
                    code="REVISION_CONFLICT",
                    status=409,
                )
            state = reducer(json.loads(row["state"]), command, actor)
            if state.get("id") != engagement_id or state.get("origin") != "SYNTHETIC":
                raise DomainError("Reducer changed immutable engagement identity")
            state["revision"] = row["revision"] + 1
            previous = db.execute(
                "SELECT hash FROM events WHERE engagement=? ORDER BY revision DESC LIMIT 1",
                (engagement_id,),
            ).fetchone()["hash"]
            self._append(db, actor, state, command["command_id"], command, previous)
            db.execute(
                "UPDATE engagements SET revision=?,state=? WHERE id=?",
                (state["revision"], canonical(state), engagement_id),
            )
            return state

    def history(self, actor: str, engagement_id: str) -> list[dict]:
        with self.connect() as db:
            self._authorize(db, actor, engagement_id)
            rows = db.execute(
                "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement_id,)
            ).fetchall()
            previous, result = "", []
            for revision, row in enumerate(rows):
                record = {
                    "actor": row["actor"],
                    "recorded_at": row["recorded_at"],
                    "previous_hash": row["previous_hash"],
                    "state": json.loads(row["state"]),
                    "command": json.loads(row["command"]),
                    "command_id": row["command_id"],
                }
                if (
                    row["revision"] != revision
                    or previous != row["previous_hash"]
                    or digest(record) != row["hash"]
                    or digest(record["command"]) != row["request_hash"]
                ):
                    raise DomainError("History integrity failure", code="INTEGRITY", status=500)
                previous = row["hash"]
                result.append({**record, "hash": previous, "revision": revision})
            return result
