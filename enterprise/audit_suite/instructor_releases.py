"""Explicit private HINT/POINTER releases; never part of audit/model state.

Separate backup integration is required. Journal hashing detects accidental edits,
not a privileged rewrite of the database and its hash chain.
"""

import json
import os
import re
import sqlite3
import stat
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .explanation_binding import verify_snapshot
from .portfolio_explanation import validate_routes
from .store import DomainError, canonical, digest, identifier

ZERO = "0" * 64
MAX_ROWS = 2000


def require(condition, message, status=400):
    if not condition:
        raise DomainError(message, status=status)


def text(value, limit=4000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= limit, "Bounded text required")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise DomainError("Valid Unicode text required") from error
    return value


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names), "Exact release fields required")


def pin(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "Exact SHA256 required"
    )
    return value


def basis(state):
    return {k: state.get(k) for k in ("scope", "company_source_binding", "evidence_acquisition")}


class InstructorReleases:
    def __init__(self, private_root: Path, engine, bindings):
        require(
            Path(private_root).is_absolute() and ".." not in Path(private_root).parts,
            "Canonical absolute release directory required",
        )
        self.root = Path(private_root).absolute()
        self.path = self.root / "releases.sqlite3"
        self.engine, self.bindings = engine, bindings
        self._private()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db(check=False) as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS documents(
                  id TEXT PRIMARY KEY,kind TEXT,content TEXT,sha TEXT);
              CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,content TEXT,sha TEXT);
              CREATE TABLE IF NOT EXISTS commands(
                  actor TEXT,eid TEXT,command TEXT,digest TEXT,result TEXT,
                  PRIMARY KEY(actor,eid,command));
              CREATE TRIGGER IF NOT EXISTS documents_no_update BEFORE UPDATE ON documents
                  BEGIN SELECT RAISE(ABORT,'Immutable release'); END;
              CREATE TRIGGER IF NOT EXISTS documents_no_delete BEFORE DELETE ON documents
                  BEGIN SELECT RAISE(ABORT,'Immutable release'); END;
              CREATE TRIGGER IF NOT EXISTS commands_no_update BEFORE UPDATE ON commands
                  BEGIN SELECT RAISE(ABORT,'Immutable release receipt'); END;
              CREATE TRIGGER IF NOT EXISTS commands_no_delete BEFORE DELETE ON commands
                  BEGIN SELECT RAISE(ABORT,'Immutable release receipt'); END;
              CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                  BEGIN SELECT RAISE(ABORT,'Immutable assistance journal'); END;
              CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                  BEGIN SELECT RAISE(ABORT,'Immutable assistance journal'); END;
            """)

    def _private(self):
        require(
            not any(p.is_symlink() for p in (self.root, *self.root.parents)),
            "Private path aliases forbidden",
        )
        require(
            self.root.is_dir() and not self.root.stat().st_mode & 0o077,
            "Existing private0700 release directory required",
        )
        if self.path.exists() or self.path.is_symlink():
            s = self.path.lstat()
            require(
                stat.S_ISREG(s.st_mode) and not s.st_mode & 0o077 and s.st_nlink == 1,
                "Private regular0600 release database required",
            )

    @contextmanager
    def _db(self, check=True):
        self._private()
        before = self.path.stat()
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            after = self.path.stat()
            require(
                (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
                "Release database changed",
            )
            if check:
                prior = ZERO
                number = 0
                for number, row in enumerate(db.execute("SELECT * FROM events ORDER BY seq"), 1):
                    event = json.loads(row["content"])
                    require(
                        row["seq"] == number
                        and event["previous"] == prior
                        and digest(event) == row["sha"]
                        and canonical(event) == row["content"],
                        "Assistance journal integrity failure",
                        503,
                    )
                    prior = row["sha"]
                require(number <= MAX_ROWS * 5, "Journal limit")
            yield db
            self._private()
            current = self.path.stat()
            require(
                (before.st_dev, before.st_ino) == (current.st_dev, current.st_ino),
                "Release database changed",
            )
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _member(self, actor, eid, role):
        require(
            self.engine.store.membership(actor, eid) == role,
            "Current scoped membership required",
            403,
        )

    def _state(self, teacher, recipient, eid):
        self._member(teacher, eid, "instruct")
        self._member(recipient, eid, "learn")
        return self.engine.store.get(teacher, eid)

    def _key(self, teacher, eid):
        # Validate privately without impersonating a sponsoring instructor access event
        # when the authenticated caller is the named recipient.
        self._member(teacher, eid, "instruct")
        selected = deepcopy(self.bindings.get(eid))
        require(selected is not None, "No protected Key binding configured", 503)
        try:
            snapshot = verify_snapshot(
                selected["path"], expected_manifest_sha256=selected["manifest_sha256"]
            )
            require(snapshot["engagement"]["id"] == eid, "Key engagement differs", 503)
            validate_routes(self.engine, snapshot)
        except (OSError, ValueError, KeyError) as error:
            raise DomainError("Protected Key unavailable", status=503) from error
        require(selected == self.bindings.get(eid), "Key binding changed", 409)
        self._member(teacher, eid, "instruct")
        return selected["manifest_sha256"]

    def _pointers(self, state, pointers, *, verify_bytes=True, row_index=None):
        require(isinstance(pointers, list) and len(pointers) <= 4, "At most four pointers required")
        out = []
        seen = set()
        for p in pointers:
            fields(p, ("kind", "id", "sha256"))
            require(
                isinstance(p["kind"], str) and p["kind"] in {"task", "artifact"},
                "Only task/artifact pointers supported",
            )
            text(p["id"], 128)
            pin(p["sha256"])
            require((p["kind"], p["id"]) not in seen, "Duplicate pointer")
            seen.add((p["kind"], p["id"]))
            rows = (
                row_index.get((p["kind"], p["id"]), [])
                if row_index is not None
                else [
                    r
                    for r in state.get("tasks" if p["kind"] == "task" else "artifacts", [])
                    if r["id"] == p["id"]
                ]
            )
            require(len(rows) == 1, "Pointer unavailable", 409)
            row = rows[0]
            control = row.get("control_id") or row.get("coverage", {}).get("control_id")
            boundary = row.get("boundary_id") or row.get("coverage", {}).get("boundary_id")
            require(
                not control or control in {c["id"] for c in state.get("controls", [])},
                "Pointer outside controls",
                409,
            )
            require(
                not boundary or boundary in state["scope"].get("boundaries", []),
                "Pointer outside boundaries",
                409,
            )
            if p["kind"] == "artifact":
                require(
                    row.get("audience", "LEARNER") == "LEARNER"
                    and row.get("status") == "AVAILABLE"
                    and row.get("engagement_id", state["id"]) == state["id"],
                    "Pointer is not learner-visible",
                    403,
                )
                require(
                    type(row.get("bytes")) is int and 0 <= row["bytes"] <= 4 * 1024 * 1024,
                    "Bounded artifact required",
                )
                require(row.get("sha256") == p["sha256"], "Artifact changed", 409)
                if verify_bytes:
                    try:
                        self.engine.artifacts.read(row)
                    except OSError as error:
                        raise DomainError(
                            "Retained pointer original unavailable", status=409
                        ) from error
            else:
                require(
                    row.get("applicability", "CURRENT_SCOPE") == "CURRENT_SCOPE"
                    and row.get("scope_version", state.get("generation_epoch", 0))
                    == state.get("generation_epoch", 0),
                    "Task is historical",
                    409,
                )
                require(digest(row) == p["sha256"], "Task changed", 409)
            out.append(dict(p))
        return out

    @staticmethod
    def _put(db, kind, value):
        require(
            db.execute("SELECT count(*) FROM documents").fetchone()[0] < MAX_ROWS,
            "Release draft limit reached",
        )
        db.execute(
            "INSERT INTO documents VALUES(?,?,?,?)",
            (value["id"], kind, canonical(value), digest(value)),
        )

    @staticmethod
    def _get(db, id, kind):
        text(id, 128)
        row = db.execute("SELECT * FROM documents WHERE id=? AND kind=?", (id, kind)).fetchone()
        require(row is not None, "Release unavailable", 404)
        value = json.loads(row["content"])
        require(
            digest(value) == row["sha"] and canonical(value) == row["content"],
            "Release integrity failure",
            503,
        )
        return value

    @staticmethod
    def _event(db, action, release, actor, details=None):
        previous = db.execute("SELECT seq,sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq = previous["seq"] + 1 if previous else 1
        require(seq <= MAX_ROWS * 5, "Assistance journal limit reached")
        event = {
            "action": action,
            "release_id": release,
            "actor": actor,
            "recorded_at": datetime.now(UTC).isoformat(),
            "previous": previous["sha"] if previous else ZERO,
            "details": details or {},
        }
        db.execute("INSERT INTO events VALUES(?,?,?)", (seq, canonical(event), digest(event)))

    @staticmethod
    def _actions(db, release):
        return [
            json.loads(r[0])["action"]
            for r in db.execute("SELECT content FROM events ORDER BY seq")
            if json.loads(r[0])["release_id"] == release
        ]

    def preview(self, instructor, eid, payload):
        fields(payload, ("recipient_id", "expected_revision", "stage", "text", "pointers"))
        p = json.loads(canonical(payload))
        text(p["recipient_id"], 128)
        text(p["text"])
        require(
            type(p["expected_revision"]) is int and p["expected_revision"] >= 0,
            "Exact revision required",
        )
        require(
            isinstance(p["stage"], str) and p["stage"] in {"HINT", "POINTER"},
            "Only HINT/POINTER supported",
        )
        state = self._state(instructor, p["recipient_id"], eid)
        require(state["revision"] == p["expected_revision"], "Preview revision changed", 409)
        pointers = self._pointers(state, p["pointers"])
        require(
            bool(pointers) == (p["stage"] == "POINTER"),
            "HINT has no pointers; POINTER requires explicit pointers",
        )
        key = self._key(instructor, eid)
        value = {
            "id": identifier("PREVIEW"),
            "engagement_id": eid,
            "instructor_id": instructor,
            "recipient_id": p["recipient_id"],
            "revision": state["revision"],
            "state_sha256": digest(state),
            "context_sha256": digest(basis(state)),
            "key_manifest_sha256": key,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
            "content": {
                "stage": p["stage"],
                "text": p["text"],
                "pointers": pointers,
                "authorship": "INSTRUCTOR_AUTHORED_ASSISTANCE_NOT_VERIFIED_FINDING",
                "professional_acceptance": "NOT_ASSERTED",
            },
        }
        with self._db() as db:
            self._check(value, exact=True)
            self._put(db, "PREVIEW", value)
        return {"preview": value, "preview_sha256": digest(value), "delivered": False}

    def _check(self, value, exact=False):
        state = self._state(value["instructor_id"], value["recipient_id"], value["engagement_id"])
        require(
            digest(basis(state)) == value["context_sha256"],
            "Release context changed; suspended",
            409,
        )
        require(
            self._key(value["instructor_id"], value["engagement_id"])
            == value["key_manifest_sha256"],
            "Key changed; release suspended",
            409,
        )
        if exact:
            require(
                state["revision"] == value["revision"] and digest(state) == value["state_sha256"],
                "Preview state changed",
                409,
            )
            require(
                datetime.now(UTC) < datetime.fromisoformat(value["expires_at"]),
                "Preview expired",
                409,
            )
        self._pointers(state, value["content"]["pointers"])
        require(
            self._key(value["instructor_id"], value["engagement_id"])
            == value["key_manifest_sha256"],
            "Key changed during release check",
            409,
        )
        final = self._state(value["instructor_id"], value["recipient_id"], value["engagement_id"])
        require(digest(final) == digest(state), "Engagement changed during release check", 409)

    @staticmethod
    def _replay(db, actor, eid, payload):
        text(payload["command_id"], 128)
        row = db.execute(
            "SELECT * FROM commands WHERE actor=? AND eid=? AND command=?",
            (actor, eid, payload["command_id"]),
        ).fetchone()
        if row:
            require(
                row["digest"] == digest(payload),
                "Command ID reused with changed release input",
                409,
            )
            return json.loads(row["result"])
        return None

    @staticmethod
    def _receipt(db, actor, eid, payload, result):
        require(
            db.execute("SELECT count(*) FROM commands").fetchone()[0] < MAX_ROWS * 5,
            "Release command limit reached",
        )
        db.execute(
            "INSERT INTO commands VALUES(?,?,?,?,?)",
            (actor, eid, payload["command_id"], digest(payload), canonical(result)),
        )
        return result

    def confirm(self, instructor, eid, payload):
        fields(payload, ("preview_id", "preview_sha256", "command_id"))
        pin(payload["preview_sha256"])
        self._member(instructor, eid, "instruct")
        with self._db() as db:
            preview = self._get(db, payload["preview_id"], "PREVIEW")
            require(
                preview["instructor_id"] == instructor and preview["engagement_id"] == eid,
                "Preview unavailable",
                403,
            )
            require(digest(preview) == payload["preview_sha256"], "Preview digest changed", 409)
            replay = self._replay(db, instructor, eid, payload)
            if replay:
                value = self._get(db, replay["release_id"], "RELEASE")
                require(
                    value["preview_id"] == preview["id"], "Release receipt identity differs", 503
                )
                self._check(value)
                require("REVOKED" not in self._actions(db, value["id"]), "Release revoked", 403)
                return replay
            require(
                not any(
                    json.loads(r[0]).get("preview_id") == preview["id"]
                    for r in db.execute("SELECT content FROM documents WHERE kind='RELEASE'")
                ),
                "Preview already released; inspect its existing receipt",
                409,
            )
            self._check(preview, exact=True)
            value = {
                **preview,
                "id": identifier("RELEASE"),
                "preview_id": preview["id"],
                "preview_sha256": digest(preview),
            }
            self._put(db, "RELEASE", value)
            self._event(db, "RELEASED", value["id"], instructor)
            self._check(preview, exact=True)
            return self._receipt(
                db,
                instructor,
                eid,
                payload,
                {
                    "release_id": value["id"],
                    "release_sha256": digest(value),
                    "status": "RELEASED",
                    "delivered": False,
                },
            )

    def list(self, recipient, eid):
        self._member(recipient, eid, "learn")
        result = []
        with self._db() as db:
            for row in db.execute("SELECT id FROM documents WHERE kind='RELEASE'"):
                value = self._get(db, row["id"], "RELEASE")
                if value["recipient_id"] != recipient or value["engagement_id"] != eid:
                    continue
                actions = self._actions(db, value["id"])
                status = "REVOKED" if "REVOKED" in actions else "RELEASED"
                if status == "RELEASED":
                    try:
                        self._check(value)
                    except DomainError:
                        status = "SUSPENDED"
                result.append(
                    {
                        "release_id": value["id"],
                        "status": status,
                        "delivered": "DELIVERED" in actions,
                        "acknowledged": "ACKNOWLEDGED" in actions,
                    }
                )
            self._member(recipient, eid, "learn")
        return result

    def read(self, recipient, eid, release_id):
        self._member(recipient, eid, "learn")
        with self._db() as db:
            value = self._get(db, release_id, "RELEASE")
            require(
                value["recipient_id"] == recipient and value["engagement_id"] == eid,
                "Release unavailable",
                404,
            )
            self._check(value)
            actions = self._actions(db, release_id)
            require("REVOKED" not in actions, "Release revoked", 403)
            if "DELIVERED" not in actions:
                self._event(db, "DELIVERED", release_id, recipient)
            self._check(value)
            return {
                "release_id": release_id,
                "release_sha256": digest(value),
                "content": value["content"],
                "pre_release_revision": value["revision"],
                "key_manifest_sha256": value["key_manifest_sha256"],
                "understanding": "NOT_INFERRED",
            }

    def acknowledge(self, recipient, eid, payload):
        fields(payload, ("release_id", "command_id"))
        self._member(recipient, eid, "learn")
        with self._db() as db:
            value = self._get(db, payload["release_id"], "RELEASE")
            require(
                value["recipient_id"] == recipient and value["engagement_id"] == eid,
                "Release unavailable",
                404,
            )
            self._check(value)
            actions = self._actions(db, value["id"])
            require(
                "DELIVERED" in actions and "REVOKED" not in actions,
                "Active delivered release required",
                409,
            )
            replay = self._replay(db, recipient, eid, payload)
            if replay:
                return replay
            if "ACKNOWLEDGED" not in actions:
                self._event(db, "ACKNOWLEDGED", value["id"], recipient)
            self._check(value)
            return self._receipt(
                db,
                recipient,
                eid,
                payload,
                {
                    "release_id": value["id"],
                    "status": "ACKNOWLEDGED",
                    "understanding": "NOT_INFERRED",
                },
            )

    def revoke(self, instructor, eid, payload):
        fields(payload, ("release_id", "command_id", "reason"))
        text(payload["reason"])
        self._member(instructor, eid, "instruct")
        with self._db() as db:
            value = self._get(db, payload["release_id"], "RELEASE")
            require(value["engagement_id"] == eid, "Release unavailable", 404)
            replay = self._replay(db, instructor, eid, payload)
            if replay:
                return replay
            if "REVOKED" not in self._actions(db, value["id"]):
                self._event(db, "REVOKED", value["id"], instructor, {"reason": payload["reason"]})
            self._member(instructor, eid, "instruct")
            return self._receipt(
                db,
                instructor,
                eid,
                payload,
                {
                    "release_id": value["id"],
                    "status": "REVOKED",
                    "reason": payload["reason"],
                    "previous_delivery_not_erased": True,
                },
            )

    def options(self, instructor, eid):
        """Safe explicit selection metadata; never principal tokens or hidden Key prose."""
        self._member(instructor, eid, "instruct")
        state = self.engine.store.get(instructor, eid)
        self._key(instructor, eid)
        with self.engine.store.connect() as db:
            recipients = [
                dict(r)
                for r in db.execute(
                    "SELECT p.id,p.name FROM principals p JOIN members m ON m.principal=p.id "
                    "WHERE m.engagement=? AND m.permission='learn' AND p.revoked=0 AND p.expires>? "
                    "ORDER BY p.id",
                    (eid, time.time()),
                )
            ]
        require(
            len(recipients) <= 200
            and len(state.get("tasks", [])) <= 2000
            and len(state.get("artifacts", [])) <= 2000,
            "Release options limit exceeded",
        )
        result = {
            "engagement_id": eid,
            "revision": state["revision"],
            "recipients": recipients,
            "tasks": [],
            "artifacts": [],
        }
        row_index = {}
        for kind, collection in (("task", "tasks"), ("artifact", "artifacts")):
            for row in state.get(collection, []):
                row_index.setdefault((kind, row["id"]), []).append(row)
        for kind, collection in (("task", "tasks"), ("artifact", "artifacts")):
            for row in state.get(collection, []):
                p = {
                    "kind": kind,
                    "id": row["id"],
                    "sha256": digest(row) if kind == "task" else row.get("sha256"),
                }
                try:
                    self._pointers(state, [p], verify_bytes=False, row_index=row_index)
                except (DomainError, OSError):
                    continue
                result[collection].append(
                    {
                        "id": row["id"],
                        "title" if kind == "task" else "name": row.get(
                            "title" if kind == "task" else "name", row["id"]
                        ),
                        "sha256": p["sha256"],
                    }
                )
        for r in recipients:
            self._member(r["id"], eid, "learn")
        self._member(instructor, eid, "instruct")
        require(
            digest(self.engine.store.get(instructor, eid)) == digest(state),
            "Release options changed",
            409,
        )
        return result

    def history(self, instructor, eid):
        """Own released metadata only; no private draft or released content in lists."""
        self._member(instructor, eid, "instruct")
        result = []
        with self._db() as db:
            for row in db.execute("SELECT id FROM documents WHERE kind='RELEASE'"):
                value = self._get(db, row["id"], "RELEASE")
                if value["instructor_id"] != instructor or value["engagement_id"] != eid:
                    continue
                actions = self._actions(db, value["id"])
                status = "REVOKED" if "REVOKED" in actions else "RELEASED"
                if status == "RELEASED":
                    try:
                        self._check(value)
                    except DomainError:
                        status = "SUSPENDED"
                result.append(
                    {
                        "release_id": value["id"],
                        "recipient_id": value["recipient_id"],
                        "stage": value["content"]["stage"],
                        "status": status,
                        "delivered": "DELIVERED" in actions,
                        "acknowledged": "ACKNOWLEDGED" in actions,
                        "pre_release_revision": value["revision"],
                    }
                )
            self._member(instructor, eid, "instruct")
        return result

    def snapshot(self):
        """Trusted operator only; sensitive drafts included; no operational restore."""
        with self._db() as db:
            value = {
                "format": "PRIVATE_INSTRUCTOR_RELEASE_ARCHIVE_V1",
                "tables": {
                    table: [
                        dict(row)
                        for row in db.execute("SELECT * FROM " + table + " ORDER BY " + order)
                    ]
                    for table, order in (
                        ("documents", "id"),
                        ("events", "seq"),
                        ("commands", "actor,eid,command"),
                    )
                },
            }
            validate_snapshot(value)
            return value


def _validate_snapshot(value):
    """Validate a bounded inert logical archive; grants/operational restoration excluded."""
    fields(value, ("format", "tables"))
    require(
        value["format"] == "PRIVATE_INSTRUCTOR_RELEASE_ARCHIVE_V1", "Unsupported release archive"
    )
    fields(value["tables"], ("documents", "events", "commands"))
    tables = value["tables"]
    for name in tables:
        require(
            isinstance(tables[name], list) and len(tables[name]) <= MAX_ROWS * 5,
            "Bounded archive tables required",
        )
    require(len(canonical(value).encode()) <= 64 * 1024 * 1024, "Release archive too large")
    documents = {}
    for row in tables["documents"]:
        fields(row, ("id", "kind", "content", "sha"))
        require(
            row["kind"] in {"PREVIEW", "RELEASE"} and row["id"] not in documents,
            "Unique typed release document required",
        )
        body = json.loads(row["content"])
        require(
            canonical(body) == row["content"]
            and digest(body) == row["sha"]
            and body["id"] == row["id"],
            "Release document integrity failure",
        )
        documents[row["id"]] = (row["kind"], body)
    previous = ZERO
    actions = {}
    for seq, row in enumerate(tables["events"], 1):
        fields(row, ("seq", "content", "sha"))
        event = json.loads(row["content"])
        fields(event, ("action", "release_id", "actor", "recorded_at", "previous", "details"))
        require(
            type(row["seq"]) is int
            and row["seq"] == seq
            and canonical(event) == row["content"]
            and digest(event) == row["sha"]
            and event["previous"] == previous,
            "Release event chain differs",
        )
        previous = row["sha"]
        require(
            event["release_id"] in documents and documents[event["release_id"]][0] == "RELEASE",
            "Event release missing",
        )
        body = documents[event["release_id"]][1]
        prior = actions.setdefault(event["release_id"], [])
        action = event["action"]
        require(
            action in {"RELEASED", "DELIVERED", "ACKNOWLEDGED", "REVOKED"}
            and action not in prior
            and "REVOKED" not in prior,
            "Invalid assistance lifecycle",
        )
        require((not prior) == (action == "RELEASED"), "Release must precede assistance access")
        if action in {"DELIVERED", "ACKNOWLEDGED"}:
            require(event["actor"] == body["recipient_id"], "Wrong assistance recipient")
        if action == "ACKNOWLEDGED":
            require("DELIVERED" in prior, "Acknowledgement before delivery")
        prior.append(action)
    for kind, body in documents.values():
        if kind == "RELEASE":
            require(
                body["preview_id"] in documents and documents[body["preview_id"]][0] == "PREVIEW",
                "Release preview missing",
            )
            original = documents[body["preview_id"]][1]
            require(
                body["preview_sha256"] == digest(original)
                and {
                    k: v for k, v in body.items() if k not in {"id", "preview_id", "preview_sha256"}
                }
                == {k: v for k, v in original.items() if k != "id"},
                "Release differs from preview",
            )
            require(body["id"] in actions, "Release journal missing")
    commands = set()
    for row in tables["commands"]:
        fields(row, ("actor", "eid", "command", "digest", "result"))
        identity = (row["actor"], row["eid"], row["command"])
        require(identity not in commands, "Duplicate release command")
        commands.add(identity)
        pin(row["digest"])
        result = json.loads(row["result"])
        require(
            canonical(result) == row["result"] and result["release_id"] in documents,
            "Command release missing",
        )
        kind, body = documents[result["release_id"]]
        require(
            kind == "RELEASE" and body["engagement_id"] == row["eid"], "Command engagement differs"
        )
    return value


def validate_snapshot(value):
    try:
        return _validate_snapshot(value)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        raise DomainError("Invalid private release archive") from error
