"""Opt-in retained history: an unchanged sealed journal and a small ordinary tail.

The prefix remains the original SQLite file. The tail contains its current
header and existing identities, then only subsequent ordinary commands. A
connection-local view gives existing readers one history; an insert trigger
routes new events exclusively into the tail. This is not a new engagement.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import stat
import sys
import time
from pathlib import Path

from .history_inspection import _stamp
from .recovery import _history
from .sealed_history_authority import (
    LocalAuthority,
    SessionAuthority,
    initialize,
    initialize_sessions,
)
from .store import DomainError, Store, _ClosingConnection, canonical, digest

SCHEMA = "SH_RETAINED_SEALED_PREFIX_ORDINARY_TAIL_V1"
CODEC_SCHEMA = "SH_RETAINED_SEALED_PREFIX_CANONICAL_FRAGMENT_TAIL_V1"
EVENT_COLUMNS = (
    "engagement",
    "revision",
    "command_id",
    "request_hash",
    "actor",
    "recorded_at",
    "previous_hash",
    "hash",
    "state",
    "command",
)
TAIL_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE principals (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,roles TEXT NOT NULL,
 token_hash TEXT UNIQUE NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY,principal TEXT NOT NULL REFERENCES principals(id),
 csrf TEXT NOT NULL,expires REAL NOT NULL,authenticated_at REAL);
CREATE TABLE engagements (id TEXT PRIMARY KEY,revision INTEGER NOT NULL,state TEXT NOT NULL);
CREATE TABLE members (
 engagement TEXT NOT NULL REFERENCES engagements(id),
 principal TEXT NOT NULL REFERENCES principals(id),permission TEXT NOT NULL,
 PRIMARY KEY(engagement,principal));
CREATE TABLE event_tail (
 engagement TEXT NOT NULL REFERENCES engagements(id),revision INTEGER NOT NULL,
 command_id TEXT NOT NULL,request_hash TEXT NOT NULL,actor TEXT NOT NULL,
 recorded_at REAL NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL,
 state TEXT NOT NULL,command TEXT NOT NULL,
 PRIMARY KEY(engagement,revision),UNIQUE(engagement,command_id));
CREATE TRIGGER event_tail_no_update BEFORE UPDATE ON event_tail
 BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
CREATE TRIGGER event_tail_no_delete BEFORE DELETE ON event_tail
 BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
CREATE TABLE authority_events (
 seq INTEGER PRIMARY KEY,body TEXT NOT NULL,sha256 TEXT NOT NULL,signature TEXT NOT NULL);
CREATE TRIGGER authority_no_update BEFORE UPDATE ON authority_events
 BEGIN SELECT RAISE(ABORT,'operator transitions are immutable'); END;
CREATE TRIGGER authority_no_delete BEFORE DELETE ON authority_events
 BEGIN SELECT RAISE(ABORT,'operator transitions are immutable'); END;
CREATE TABLE issued_sessions (
 token_hash TEXT PRIMARY KEY,body TEXT NOT NULL,signature TEXT NOT NULL);
CREATE TRIGGER issued_sessions_no_update BEFORE UPDATE ON issued_sessions
 BEGIN SELECT RAISE(ABORT,'session issuance is immutable'); END;
CREATE TRIGGER issued_sessions_no_delete BEFORE DELETE ON issued_sessions
 BEGIN SELECT RAISE(ABORT,'session issuance is immutable'); END;
"""


def _require(condition, message):
    if not condition:
        raise DomainError(message, code="INTEGRITY", status=503)


def _file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _private(path, *, directory=False):
    path = Path(path).absolute()
    _require(
        path == path.resolve()
        and not any(p.is_symlink() for p in [path, *path.parents]),
        "Unaliased sealed-history path required",
    )
    info = path.lstat()
    _require(
        (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and not info.st_mode & 0o077
        and (directory or info.st_nlink == 1),
        "Private ordinary sealed-history member required",
    )
    return path


def _write_new(path, value):
    data = (canonical(value) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def _schema_hash(db):
    return digest(
        [
            dict(r)
            for r in db.execute(
                "SELECT type,name,tbl_name,sql FROM main.sqlite_master ORDER BY type,name"
            )
        ]
    )


def _original_permissions(roles):
    original = json.loads(roles)
    if original == ["instructor"]:
        return {"instruct", "review", "learn"}
    if original == ["reviewer"]:
        return {"review", "learn"}
    return {"learn"} if original == ["learner"] else set()


class _SealedConnection(_ClosingConnection):
    def backup(self, *args, **kwargs):
        # sqlite3.Connection.backup copies only the main database, not the
        # attached original. Never emit a misleading tail-only recovery image.
        raise DomainError(
            "Sealed history requires a complete composed recovery export", status=403
        )

    def close(self):
        managed_context = getattr(self, "_managed_connection_context", None)
        try:
            try:
                super().close()
            finally:
                pending = getattr(self, "_request_graph_candidate", None)
                if pending is not None:
                    scope, key, outside, roots, graph = pending
                    # Only ordinary quiescent SQLite lifecycle is reusable. The
                    # earlier inside proof and this exact outside closure must
                    # both succeed; changed or preexisting sidecars never qualify.
                    if _stamp(self._sealed_owner.db_path) == outside:
                        scope.put(key, outside, roots, graph)
                    self._request_graph_candidate = None
                invocation = getattr(self, "_codec_invocation", None)
                if invocation is not None:
                    invocation.close()
                    self._codec_invocation = None
                contents = getattr(self, "_codec_contents", None)
                if contents is not None:
                    contents.clear()
                    self._codec_contents = None
                self._sealed_owner.check_prefix()
        finally:
            if managed_context is not None:
                self._managed_connection_context = None
                managed_context.__exit__(*sys.exc_info())


def prepare_tail(store, actor, engagement, destination, *, state_codec=False):
    """Copy only the exact current header/auth rows into a new private tail.

    This operator primitive verifies the complete prefix hash chain. Company
    activation additionally requires the retained loader's full native/typed
    source verification, under its fresh source lock, before publication.
    It never overwrites a path or copies old events into the tail.
    """
    _require(
        not isinstance(store, SealedHistoryStore),
        "An ordinary original prefix is required",
    )
    _require(
        type(state_codec) is bool, "Exact optional canonical codec choice required"
    )
    root = _private(store.root, directory=True)
    prefix = _private(store.db_path)
    outside = _stamp(prefix)
    _require(
        not any(outside[0][1:]), "Sealed prefix requires quiescent absent sidecars"
    )
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    destination.mkdir(mode=0o700)  # O_EXCL semantics: even an empty directory refuses.
    tail_path = destination / "tail.sqlite3"
    fd = os.open(tail_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    with (
        store.connect() as source,
        sqlite3.connect(tail_path, factory=_ClosingConnection) as tail,
    ):
        tail.row_factory = sqlite3.Row
        source.execute("BEGIN IMMEDIATE")
        source.execute("PRAGMA query_only=ON")
        store._authorize(source, actor, engagement, {"instruct"})
        _require(
            {r[0] for r in source.execute("SELECT id FROM engagements")}
            == {engagement},
            "Exactly the existing selected engagement required",
        )
        _require(
            source.execute("PRAGMA quick_check").fetchone()[0] == "ok",
            "Prefix SQLite integrity failed",
        )
        counts = _history(source)
        current = source.execute(
            "SELECT * FROM engagements WHERE id=?", (engagement,)
        ).fetchone()
        latest = source.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision DESC LIMIT 1",
            (engagement,),
        ).fetchone()
        tail.executescript(
            TAIL_SQL.replace("event_tail", "event_frames") if state_codec else TAIL_SQL
        )
        codec_initial = None
        if state_codec:
            from .canonical_state_codec import SCHEMA as NODE_SCHEMA
            from .canonical_state_codec import SQL, encode

            tail.executescript(SQL)
            initial_root, size = encode(tail, json.loads(current["state"]))
            codec_initial = {
                "schema": NODE_SCHEMA,
                "initial_root": initial_root,
                "initial_state_bytes": size,
                "initial_state_sha256": hashlib.sha256(
                    current["state"].encode()
                ).hexdigest(),
            }
        for table in ("principals", "engagements", "members", "sessions"):
            rows = source.execute(f"SELECT * FROM {table}")
            for row in rows:
                tail.execute(
                    f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})",
                    tuple(row),
                )
        initial_auth = {
            table: digest(
                [dict(r) for r in source.execute(f"SELECT * FROM {table} ORDER BY 1")]
            )
            for table in ("principals", "members", "sessions")
        }
        _require(
            counts[engagement]["events"] == current["revision"] + 1
            and counts[engagement]["last_hash"] == latest["hash"],
            "Prefix terminal history differs",
        )
        tail_schema = _schema_hash(tail)
        prefix_identity = {
            "path": str(prefix),
            "bytes": prefix.stat().st_size,
            "engagement": engagement,
            "revision": current["revision"],
            "last_hash": latest["hash"],
            "current_state_sha256": hashlib.sha256(
                current["state"].encode()
            ).hexdigest(),
            "initial_auth_sha256": initial_auth,
        }
    _require(_stamp(prefix) == outside, "Original prefix changed during preparation")
    # Fresh physical bytes are externally pinned, including non-event pages.
    prefix_identity["sha256"] = _file_sha(prefix)
    _require(
        _stamp(prefix) == outside, "Original prefix changed during full byte hashing"
    )
    _require(
        not any(_stamp(tail_path)[0][1:]), "Prepared tail did not close quiescently"
    )
    authority_descriptor, initial_head = initialize(
        destination, prefix_identity["sha256"], engagement
    )
    manifest = {
        "schema": CODEC_SCHEMA if state_codec else SCHEMA,
        "audit_root": str(root),
        "prefix": prefix_identity,
        "tail_path": str(tail_path),
        "initial_tail_sha256": _file_sha(tail_path),
        "tail_schema_sha256": tail_schema,
        "operator_authority": authority_descriptor,
        "session_authority": initialize_sessions(destination),
        "initial_authority_head": initial_head,
    }
    if state_codec:
        manifest["state_codec"] = codec_initial
    pin = _write_new(destination / "SEALED_HISTORY.json", manifest)
    fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
    os.fsync(fd)
    os.close(fd)
    return {"path": str(destination / "SEALED_HISTORY.json"), "sha256": pin}


class SealedHistoryStore(Store):
    """Same Store command/auth interface; no new audit, identity or source."""

    PRIVATE_VIEW_MAX_BYTES = 32 * 1024 * 1024

    def __init__(
        self,
        root,
        manifest_path,
        manifest_sha256,
        *,
        authority_head=None,
        session_revocations=None,
        compact_prefix=None,
    ):
        self.root = _private(root, directory=True)
        self.manifest_path = _private(manifest_path)
        _require(
            self.manifest_path.stat().st_size <= 1024 * 1024
            and _file_sha(self.manifest_path) == manifest_sha256,
            "Externally pinned sealed-history manifest required",
        )
        self.manifest_sha256 = manifest_sha256
        self.manifest = json.loads(self.manifest_path.read_text())
        _require(
            set(self.manifest)
            == {
                "schema",
                "audit_root",
                "prefix",
                "tail_path",
                "initial_tail_sha256",
                "tail_schema_sha256",
                "operator_authority",
                "session_authority",
                "initial_authority_head",
            }
            | (
                {"state_codec"}
                if self.manifest.get("schema") == CODEC_SCHEMA
                else set()
            )
            | (
                {"storage_derivation"}
                if "storage_derivation" in self.manifest
                and self.manifest.get("schema") == CODEC_SCHEMA
                else set()
            )
            and self.manifest["schema"] in {SCHEMA, CODEC_SCHEMA}
            and self.manifest["audit_root"] == str(self.root),
            "Exact sealed-history schema/root required",
        )
        self.prefix = self.manifest["prefix"]
        self.state_codec = self.manifest.get("state_codec")
        _require(
            (self.manifest["schema"] == CODEC_SCHEMA and type(self.state_codec) is dict)
            or (self.manifest["schema"] == SCHEMA and self.state_codec is None),
            "Exact canonical codec descriptor required",
        )
        _require(
            set(self.prefix)
            == {
                "path",
                "bytes",
                "sha256",
                "engagement",
                "revision",
                "last_hash",
                "current_state_sha256",
                "initial_auth_sha256",
            }
            and type(self.prefix["revision"]) is int
            and self.prefix["revision"] >= 0
            and type(self.prefix["bytes"]) is int
            and self.prefix["bytes"] > 0,
            "Strict sealed-prefix metadata required",
        )
        # Original physical SHA/path remains the signed authority lineage.
        # The explicit derivative mapping never rewrites that descriptor.
        self.compact_prefix = None
        original_path = Path(self.prefix["path"])
        _require(
            original_path == self.root / "engagements.sqlite3",
            "Original retained journal lineage path required",
        )
        if compact_prefix is None:
            self.prefix_path = _private(original_path)
        else:
            from .compact_prefix_storage import CompactPrefix

            self.compact_prefix = CompactPrefix(compact_prefix, self.prefix)
            self.prefix_path = self.compact_prefix.database
        self.db_path = _private(self.manifest["tail_path"])
        _require(
            self.db_path.parent == self.manifest_path.parent
            and self.db_path != self.prefix_path,
            "Separate ordinary tail required",
        )
        self._prefix_stamp = _stamp(self.prefix_path)
        _require(
            not any(self._prefix_stamp[0][1:]), "Sealed prefix must have no sidecars"
        )
        if self.compact_prefix is None:
            _require(
                self.prefix_path.stat().st_size == self.prefix["bytes"]
                and _file_sha(self.prefix_path) == self.prefix["sha256"],
                "Fresh complete prefix byte pin differs",
            )
        self.check_prefix()
        self.authority = LocalAuthority(
            self.manifest["operator_authority"],
            self.manifest["initial_authority_head"]
            if authority_head is None
            else authority_head,
            directory=self.manifest_path.parent,
            prefix_sha256=self.prefix["sha256"],
            engagement=self.prefix["engagement"],
        )
        self.session_authority = SessionAuthority(
            self.manifest["session_authority"], revocation_pins=session_revocations
        )
        _require(
            self.session_authority.revocations
            == self.manifest_path.parent / "SESSION_REVOCATIONS",
            "Original local session-revocation directory required",
        )
        self._prefix_integrity = (
            None  # Published only after full typed native verification.
        )
        self.check_prefix()

    @property
    def event_table(self):
        return "event_frames" if self.state_codec is not None else "event_tail"

    def verify_codec(self, db):
        managed = getattr(self, "_managed_history_integrity", None)
        if managed is not None and not managed.force_full:
            return managed.verify_image(db)
        if self.state_codec is None:
            return None
        if not db.in_transaction:
            # Existing trusted projection callers may not have reserved a
            # transaction themselves. Keep the fresh graph and all subsequent
            # reconstructed reads on this exact consistent connection.
            db.execute("BEGIN")
        from .canonical_state_codec import SCHEMA as NODE_SCHEMA
        from .canonical_state_codec import VerifiedInvocationGraph, decode, valid_id

        choice = self.state_codec
        _require(
            type(choice) is dict
            and set(choice)
            == {"schema", "initial_root", "initial_state_bytes", "initial_state_sha256"}
            and choice["schema"] == NODE_SCHEMA
            and valid_id(choice["initial_root"])
            and type(choice["initial_state_bytes"]) is int
            and choice["initial_state_bytes"] > 0
            and choice["initial_state_sha256"] == self.prefix["current_state_sha256"],
            "Exact initial canonical graph projection required",
        )
        roots = [choice["initial_root"]]
        for row in db.execute("SELECT state FROM main.event_frames ORDER BY revision"):
            roots.append(self._state_descriptor(row[0])["root"])
        from .request_integrity import current as current_request_integrity

        stamp = _stamp(self.db_path)
        existing = getattr(db, "_codec_invocation", None)
        if (
            existing is not None
            and existing._roots == frozenset(roots)
            and existing._changes == db.total_changes
            and getattr(db, "_codec_verified_stamp", None) == stamp
        ):
            existing.check(db)
            return existing._proof
        scope = current_request_integrity()
        key = (id(self), self.manifest_sha256, self.db_path)
        outside = db._request_outer_stamp
        reusable_image = not any(outside[0][1:]) and stamp[0][0] == outside[0][0]
        cached = (
            None
            if scope is None or not reusable_image
            else scope.get(key, outside, roots)
        )
        if cached is None:
            invocation = VerifiedInvocationGraph(db, roots)
            initial = decode(db, choice["initial_root"], invocation=invocation)
            _require(
                len(initial) == choice["initial_state_bytes"]
                and hashlib.sha256(initial).hexdigest()
                == choice["initial_state_sha256"],
                "Exact original current-state graph projection differs",
            )
            _require(_stamp(self.db_path) == stamp, "Graph changed during fresh proof")
            if scope is not None and reusable_image:
                db._request_graph_candidate = (scope, key, outside, roots, invocation)
        else:
            invocation = VerifiedInvocationGraph.from_request_proof(db, cached)
            _require(
                _stamp(self.db_path) == stamp,
                "Graph changed during request-local reuse",
            )
        previous = getattr(db, "_codec_invocation", None)
        if previous is not None:
            previous.close()
        # Actual bytes are invocation-local, discarded with this connection.
        # Only metadata may be published in retained integrity descriptors.
        db._codec_invocation = invocation
        db._codec_verified_stamp = stamp
        return invocation._proof

    @staticmethod
    def _state_descriptor(raw):
        from .canonical_state_codec import MAX_BYTES, valid_id

        value = json.loads(raw)
        _require(
            type(value) is dict
            and set(value) == {"root", "bytes", "sha256"}
            and valid_id(value["root"])
            and valid_id(value["sha256"])
            and type(value["bytes"]) is int
            and 0 < value["bytes"] <= MAX_BYTES
            and canonical(value) == raw,
            "Exact canonical event-state descriptor required",
        )
        return value

    def check_prefix(self):
        _private(self.prefix_path)
        if self.compact_prefix is not None:
            self.compact_prefix.check()
        _private(self.db_path)
        _private(self.manifest_path)
        _require(
            _stamp(self.prefix_path) == self._prefix_stamp
            and not any(self._prefix_stamp[0][1:])
            and _file_sha(self.manifest_path) == self.manifest_sha256,
            "Sealed historical prefix or external pin changed; full revalidation required",
        )
        if "storage_derivation" in self.manifest:
            from .pristine_tail_conversion import verify_derivation

            self._derivation_stamp = verify_derivation(
                self, expected_stamp=getattr(self, "_derivation_stamp", None)
            )
        if hasattr(self, "session_authority"):
            self.session_authority.check_revocations(
                self.prefix["sha256"], self.prefix["engagement"]
            )
        return self._prefix_stamp

    def prefix_connection(self):
        self.check_prefix()
        # The immutable original is already externally byte-pinned and has no
        # sidecars. Closing stamp checks cover external mutation during reads.
        db = sqlite3.connect(
            self.prefix_path.as_uri() + "?immutable=1",
            uri=True,
            factory=_ClosingConnection,
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA trusted_schema=OFF")
        if self.compact_prefix is not None:
            self.compact_prefix.install(db)
        db.execute("PRAGMA query_only=ON")
        return db

    def connect(self):
        managed = getattr(self, "_managed_history_integrity", None)
        if managed is None:
            return self._connect_unwrapped()
        context = managed.locked()
        db = None
        try:
            context.__enter__()
            db = self._connect_unwrapped()
            db._managed_connection_context = context
            # Validate before inherited get/session/listing methods see rows.
            # Roll back this read-only validation reservation so each ordinary
            # caller retains its existing transaction/BEGIN semantics.
            if not managed._issuing:
                try:
                    db.execute("BEGIN IMMEDIATE")
                    managed.verify_image(db)
                finally:
                    db.rollback()
            return db
        except BaseException:
            if db is not None:
                db.close()
            else:
                context.__exit__(*sys.exc_info())
            raise

    def _connect_unwrapped(self):
        self.check_prefix()
        outside = _stamp(self.db_path)
        db = sqlite3.connect(
            self.db_path, timeout=15, uri=True, factory=_SealedConnection
        )
        db._sealed_owner = self
        db._request_outer_stamp = outside
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        _require(
            _schema_hash(db) == self.manifest["tail_schema_sha256"],
            "Ordinary tail schema changed",
        )
        db.execute(
            "ATTACH DATABASE ? AS sealed_prefix",
            (self.prefix_path.as_uri() + "?immutable=1",),
        )
        if self.compact_prefix is None:
            db.execute(
                "CREATE TEMP VIEW prefix_events AS SELECT * FROM sealed_prefix.events"
            )
        else:
            self.compact_prefix.install(
                db, schema="sealed_prefix", view="prefix_events"
            )
        if self.state_codec is not None:
            from .canonical_state_codec import decode, encode

            def serialize_state(raw):
                value = json.loads(raw)
                _require(
                    canonical(value) == raw, "Exact canonical state input required"
                )
                root, size = encode(db, value)
                return canonical(
                    {
                        "root": root,
                        "bytes": size,
                        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                    }
                )

            def reconstruct_state(raw):
                item = self._state_descriptor(raw)
                result = decode(
                    db,
                    item["root"],
                    proof=getattr(db, "_codec_proof", None),
                    contents=getattr(db, "_codec_contents", None),
                    invocation=getattr(db, "_codec_invocation", None),
                )
                _require(
                    len(result) == item["bytes"]
                    and hashlib.sha256(result).hexdigest() == item["sha256"],
                    "Reconstructed exact event-state hash differs",
                )
                return result.decode("utf-8")

            db.create_function("canonical_state_encode", 1, serialize_state)
            db.create_function("canonical_state_decode", 1, reconstruct_state)
            projection = ",".join(
                "canonical_state_decode(state) AS state" if name == "state" else name
                for name in EVENT_COLUMNS
            )
            db.execute(
                f"CREATE TEMP VIEW event_tail AS SELECT rowid,{projection} FROM main.event_frames"
            )
        columns = ",".join(EVENT_COLUMNS)
        tail_view = "event_tail" if self.state_codec is not None else "main.event_tail"
        encoded_state = (
            "canonical_state_encode(NEW.state)"
            if self.state_codec is not None
            else "NEW.state"
        )
        db.execute(
            f"CREATE TEMP VIEW events AS SELECT {columns} FROM prefix_events "
            f"UNION ALL SELECT {columns} FROM {tail_view}"
        )
        db.executescript(f"""
        CREATE TEMP TRIGGER insert_retained_event INSTEAD OF INSERT ON events BEGIN
          SELECT CASE WHEN NEW.engagement != (SELECT id FROM main.engagements)
            OR NEW.revision <= (SELECT MAX(revision) FROM prefix_events)
            OR EXISTS(SELECT 1 FROM prefix_events WHERE engagement=NEW.engagement
                       AND command_id=NEW.command_id)
          THEN RAISE(ABORT,'sealed prefix identity/revision/command cannot be replaced') END;
          INSERT INTO {self.event_table} VALUES(NEW.engagement,NEW.revision,NEW.command_id,
            NEW.request_hash,NEW.actor,NEW.recorded_at,NEW.previous_hash,NEW.hash,
            {encoded_state},NEW.command);
        END;
        """)
        return db

    def ordered_raw_queries(self):
        """Literal indexed components; never sort the combined events view."""
        prefix = (
            "sealed_prefix.prefix_frames"
            if self.compact_prefix is not None
            else "sealed_prefix.events"
        )
        return (
            f"SELECT * FROM {prefix} WHERE engagement=? ORDER BY revision",
            f"SELECT * FROM main.{self.event_table} WHERE engagement=? ORDER BY revision",
        )

    def iter_raw_events(self, db, engagement):
        """One exact raw event at a time under the caller's consistent lock.

        This preserves original whitespace and decodes only the requested row.
        It is storage traversal, not an alternative to typed/native replay.
        """
        _require(
            getattr(db, "_sealed_owner", None) is self
            and db.in_transaction
            and type(engagement) is str
            and engagement == self.prefix["engagement"],
            "Exact transactional sealed raw reader required",
        )
        self.check_prefix()
        current = db.execute(
            "SELECT revision,state FROM main.engagements WHERE id=?", (engagement,)
        ).fetchone()
        _require(
            current is not None
            and type(current["revision"]) is int
            and current["revision"] >= self.prefix["revision"]
            and type(current["state"]) is str,
            "Strict current raw traversal boundary required",
        )
        outside = _stamp(self.db_path)
        count, previous, latest = 0, "", None
        for component, query in enumerate(self.ordered_raw_queries()):
            plans = db.execute("EXPLAIN QUERY PLAN " + query, (engagement,))
            _require(
                all("TEMP B-TREE" not in row["detail"].upper() for row in plans),
                "Indexed separately ordered raw cursors required",
            )
            cursor = db.execute(query, (engagement,))
            while (source := cursor.fetchone()) is not None:
                row = {key: source[key] for key in EVENT_COLUMNS[:8]}
                _require(
                    row["engagement"] == engagement
                    and type(row["revision"]) is int
                    and row["revision"] == count
                    and row["previous_hash"] == previous,
                    "Complete ordered raw prefix/tail boundary differs",
                )
                if component == 0 and self.compact_prefix is not None:
                    for kind in ("state", "command"):
                        row[kind] = self.compact_prefix.decode(
                            db,
                            source[kind + "_root"],
                            source[kind + "_bytes"],
                            source[kind + "_sha256"],
                            schema="sealed_prefix",
                        )
                else:
                    row["command"] = source["command"]
                    row["state"] = (
                        db.execute(
                            "SELECT canonical_state_decode(?)", (source["state"],)
                        ).fetchone()[0]
                        if component == 1 and self.state_codec is not None
                        else source["state"]
                    )
                _require(
                    type(row["state"]) is str and type(row["command"]) is str,
                    "Exact original raw UTF-8 state and command required",
                )
                latest, previous, count = row["state"], row["hash"], count + 1
                yield row
            if component == 0:
                _require(
                    count == self.prefix["revision"] + 1
                    and previous == self.prefix["last_hash"],
                    "Complete immutable raw prefix differs",
                )
        _require(
            count == current["revision"] + 1
            and canonical(json.loads(latest)) == canonical(json.loads(current["state"]))
            and _stamp(self.db_path) == outside,
            "Complete raw tip/current or transactional identity differs",
        )
        self.check_prefix()

    def verify_projection(self, db):
        """Fresh exact original projection and signed current identity closure.

        The initial file hash describes the published initialization image.
        Before the first legitimate command/login/authority transition its
        complete physical bytes must still match that pin. Thereafter the
        reconstructed event chain, signed identity transitions and current
        session contract establish current authority, not an obsolete file hash.
        """
        prefix = self.prefix
        self.verify_codec(db)
        row = db.execute(
            "SELECT id,revision,state FROM sealed_prefix.engagements"
        ).fetchall()
        _require(
            len(row) == 1
            and row[0]["id"] == prefix["engagement"]
            and type(row[0]["revision"]) is int
            and row[0]["revision"] == prefix["revision"]
            and hashlib.sha256(row[0]["state"].encode()).hexdigest()
            == prefix["current_state_sha256"],
            "Externally pinned initial current-state projection differs",
        )
        actual_auth = {
            table: digest(
                [
                    dict(r)
                    for r in db.execute(
                        f"SELECT * FROM sealed_prefix.{table} ORDER BY 1"
                    )
                ]
            )
            for table in ("principals", "members", "sessions")
        }
        _require(
            actual_auth == prefix["initial_auth_sha256"],
            "Externally pinned original authority projection differs",
        )
        original_ids = {
            r[0] for r in db.execute("SELECT id FROM sealed_prefix.principals")
        }
        _require(
            {r[0] for r in db.execute("SELECT id FROM main.principals")} == original_ids
            and {r[0] for r in db.execute("SELECT id FROM main.engagements")}
            == {prefix["engagement"]}
            and not db.execute(
                "SELECT 1 FROM sessions WHERE principal NOT IN (SELECT id FROM principals)"
            ).fetchone(),
            "Current tail acquired a foreign identity/engagement/session",
        )
        for person in original_ids:
            self.validate_credentials(db, person)
        no_changes = (
            not db.execute(f"SELECT 1 FROM main.{self.event_table} LIMIT 1").fetchone()
            and not db.execute("SELECT 1 FROM main.authority_events LIMIT 1").fetchone()
            and not db.execute("SELECT 1 FROM main.issued_sessions LIMIT 1").fetchone()
            and not self.session_authority.known_revocations
            and all(
                digest(
                    [
                        dict(r)
                        for r in db.execute(f"SELECT * FROM main.{table} ORDER BY 1")
                    ]
                )
                == actual_auth[table]
                for table in ("principals", "members", "sessions")
            )
        )
        if no_changes:
            current = db.execute(
                "SELECT revision,state FROM main.engagements"
            ).fetchone()
            _require(
                current["revision"] == prefix["revision"]
                and hashlib.sha256(current["state"].encode()).hexdigest()
                == prefix["current_state_sha256"],
                "Initial ordinary tail state differs",
            )
            # During a SQLite connection its own empty sidecars may exist, but
            # no SQL initialization or write has occurred in this query-only
            # validation transaction; the original main-file image is exact.
            _require(
                _file_sha(self.db_path) == self.manifest["initial_tail_sha256"],
                "Published initial tail physical image differs",
            )

    def validate_credentials(self, db, principal_id):
        """Recompute current identity/member authority from signed transitions."""
        expected = {
            r["id"]: dict(r)
            for r in db.execute("SELECT * FROM sealed_prefix.principals")
        }
        members = {
            (r["engagement"], r["principal"]): r["permission"]
            for r in db.execute("SELECT * FROM sealed_prefix.members")
        }
        epochs = {k: 0 for k in expected}
        previous_clock = 0
        for event in self.authority.records(db):
            person = event["principal"]
            old = expected.get(person)
            clock = event["recorded_at"]
            payload = event["payload"]
            _require(
                old is not None
                and type(clock) in (int, float)
                and math.isfinite(clock)
                and previous_clock <= clock <= time.time()
                and type(payload) is dict,
                "Signed authority identity/chronology differs",
            )
            if event["kind"] == "credential.rotate":
                _require(
                    set(payload)
                    == {
                        "old_token_hash",
                        "new_token_hash",
                        "old_expires",
                        "new_expires",
                        "lifetime",
                    }
                    and old["revoked"] == 0
                    and type(payload["lifetime"]) is int
                    and 60 <= payload["lifetime"] <= 7 * 86400
                    and payload["old_token_hash"] == old["token_hash"]
                    and payload["old_expires"] == old["expires"]
                    and payload["new_expires"] == clock + payload["lifetime"]
                    and isinstance(payload["new_token_hash"], str)
                    and len(payload["new_token_hash"]) == 64
                    and payload["new_token_hash"] != old["token_hash"],
                    "Signed credential rotation is not an exact bounded transition",
                )
                old["token_hash"], old["expires"] = (
                    payload["new_token_hash"],
                    payload["new_expires"],
                )
                epochs[person] = clock
            elif event["kind"] == "principal.revoke":
                _require(
                    set(payload) == {"before", "after"}
                    and type(payload["before"]) is int
                    and type(payload["after"]) is int
                    and payload["before"] == old["revoked"] == 0
                    and payload["after"] == 1,
                    "Signed revocation cannot reactivate an identity",
                )
                old["revoked"] = 1
            elif event["kind"] == "membership.grant":
                key = (self.prefix["engagement"], person)
                _require(
                    set(payload) == {"engagement", "before", "after"}
                    and payload["engagement"] == key[0]
                    and key in members
                    and payload["before"] == members[key]
                    and payload["after"] in _original_permissions(old["roles"])
                    and old["revoked"] == 0,
                    "Signed membership transition differs from the original member",
                )
                members[key] = payload["after"]
            else:
                _require(False, "Unknown signed operator transition")
            previous_clock = clock
        self.validate_issuance_history(db)
        row = db.execute(
            "SELECT * FROM principals WHERE id=?", (principal_id,)
        ).fetchone()
        original = expected.get(principal_id)
        _require(
            row is not None
            and original is not None
            and row["name"] == original["name"]
            and row["roles"] == original["roles"]
            and row["token_hash"] == original["token_hash"]
            and row["expires"] == original["expires"]
            and type(row["revoked"]) is int
            and row["revoked"] == original["revoked"],
            "Current credential differs from its genuine signed rotation history",
        )
        actual_members = {
            (r["engagement"], r["principal"]): r["permission"]
            for r in db.execute(
                "SELECT * FROM members WHERE principal=?", (principal_id,)
            )
        }
        _require(
            actual_members
            == {k: v for k, v in members.items() if k[1] == principal_id},
            "Current membership differs from signed original-member history",
        )
        revoked = self.session_authority.check_revocations(
            self.prefix["sha256"], self.prefix["engagement"]
        )
        for session in db.execute(
            "SELECT * FROM sessions WHERE principal=?", (principal_id,)
        ):
            _require(
                session["token_hash"] not in revoked,
                "Signed logout permanently invalidated session",
            )
            at = session["authenticated_at"]
            original_session = db.execute(
                "SELECT * FROM sealed_prefix.sessions WHERE token_hash=?",
                (session["token_hash"],),
            ).fetchone()
            if original_session is not None:
                _require(
                    epochs[principal_id] == 0
                    and tuple(original_session) == tuple(session),
                    "Original session was invalidated or repaired",
                )
            else:
                _require(
                    type(at) in (int, float)
                    and math.isfinite(at)
                    and epochs[principal_id] <= at <= time.time()
                    and type(session["expires"]) in (int, float)
                    and math.isfinite(session["expires"])
                    and session["expires"] == at + 3600,
                    "Current session predates rotation or has unbounded expiry",
                )
                issued = db.execute(
                    "SELECT body,signature FROM issued_sessions WHERE token_hash=?",
                    (session["token_hash"],),
                ).fetchone()
                _require(issued is not None, "Actual signed login issuance required")
                expected_issuance = dict(session) | {
                    "prefix_sha256": self.prefix["sha256"],
                    "engagement": self.prefix["engagement"],
                    "credential_token_hash": original["token_hash"],
                }
                _require(
                    digest(
                        self.session_authority.verify(
                            issued["body"], issued["signature"]
                        )
                    )
                    == digest(expected_issuance),
                    "Signed login issuance/session differs",
                )
        return original

    def validate_issuance_history(self, db):
        """Every durable login issuance must have actual signed original authority.

        Logged-out and rotated-away issuances remain verifiable historical
        records. An orphan unsigned row cannot waive the initial physical pin.
        Only integrity descriptors are calculated, never reusable sessions.
        """
        credentials = {}
        for row in db.execute("SELECT * FROM sealed_prefix.principals"):
            credentials[row["id"]] = [
                {
                    "hash": row["token_hash"],
                    "start": 0,
                    "end": None,
                    "expires": row["expires"],
                    "revoked": None,
                }
            ]
        for event in self.authority.records(db):
            editions = credentials[event["principal"]]
            clock = event["recorded_at"]
            if event["kind"] == "credential.rotate":
                editions[-1]["end"] = clock
                editions.append(
                    {
                        "hash": event["payload"]["new_token_hash"],
                        "start": clock,
                        "end": None,
                        "expires": event["payload"]["new_expires"],
                        "revoked": None,
                    }
                )
            elif event["kind"] == "principal.revoke":
                editions[-1]["revoked"] = clock
        for row in db.execute("SELECT * FROM main.issued_sessions"):
            value = self.session_authority.verify(row["body"], row["signature"])
            _require(
                type(value) is dict
                and set(value)
                == {
                    "token_hash",
                    "principal",
                    "csrf",
                    "expires",
                    "authenticated_at",
                    "prefix_sha256",
                    "engagement",
                    "credential_token_hash",
                }
                and type(value["token_hash"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", value["token_hash"]) is not None
                and value["token_hash"] == row["token_hash"]
                and type(value["principal"]) is str
                and value["principal"] in credentials
                and type(value["csrf"]) is str
                and 1 <= len(value["csrf"]) <= 128
                and type(value["authenticated_at"]) in (int, float)
                and math.isfinite(value["authenticated_at"])
                and 0 < value["authenticated_at"] <= time.time()
                and type(value["expires"]) in (int, float)
                and math.isfinite(value["expires"])
                and value["expires"] == value["authenticated_at"] + 3600
                and value["prefix_sha256"] == self.prefix["sha256"]
                and value["engagement"] == self.prefix["engagement"],
                "Historical signed login issuance identity/clock differs",
            )
            at = value["authenticated_at"]
            _require(
                any(
                    value["credential_token_hash"] == edition["hash"]
                    and edition["start"] <= at < edition["expires"]
                    and (edition["end"] is None or at <= edition["end"])
                    and (edition["revoked"] is None or at <= edition["revoked"])
                    for edition in credentials[value["principal"]]
                ),
                "Historical login lacks a valid original credential edition",
            )

    def _principal(self, db, person_id):
        self.validate_credentials(db, person_id)
        return super()._principal(db, person_id)

    def create(self, *args, **kwargs):
        raise DomainError(
            "Retained sealed storage cannot create a new engagement", status=403
        )

    def inspect_sealed_history(self, actor, engagement, *, revisions=()):
        from .sealed_history_inspection import inspect_composed

        return inspect_composed(self, actor, engagement, revisions=revisions)

    def history(self, actor, engagement_id):
        """Refuse the legacy eager API before selecting any event-state bytes.

        Selected revisions use inspect_history. Complete history belongs in
        the independently verified streaming compressed packet, never a list
        of every full state in an interactive response.
        """
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._authorize(db, actor, engagement_id)
            self.check_prefix()
        raise DomainError(
            "Choose a recorded revision for interactive history, or export the complete "
            "compressed packet; eager full-state history is unavailable in sealed storage",
            code="HISTORY_STREAM_REQUIRED",
            status=413,
        )

    def check_private_view_budget(self, value):
        """Bound protected metadata JSON before the HTTP serializer builds its body.

        This preserves every returned field or refuses the whole view. It does
        not truncate a comparison, original, selected state or complete export.
        """
        size = 0
        encoder = json.JSONEncoder(
            ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
        for chunk in encoder.iterencode(value):
            size += len(chunk.encode("utf-8"))
            if size > self.PRIVATE_VIEW_MAX_BYTES:
                raise DomainError(
                    "Protected view exceeds the interactive response budget; use focused "
                    "workspace selections or the complete compressed packet",
                    code="VIEW_BUDGET_EXCEEDED",
                    status=413,
                )
        return value

    def provision(self, *args, **kwargs):
        raise DomainError(
            "Retained sealed storage preserves existing identities", status=403
        )

    def command(self, actor, engagement_id, command, reducer, *, permissions):
        managed = getattr(self, "_managed_history_integrity", None)
        operation = lambda: super(SealedHistoryStore, self).command(
            actor, engagement_id, command, reducer, permissions=permissions)
        if managed is None:
            return operation()
        return managed.mutate(operation, kind="AUDIT_APPEND", command=command)

    @property
    def authority_head(self):
        return dict(self.authority.head_choice)

    def _commit_operator_transition(self, kind, principal_id, change):
        managed = getattr(self, "_managed_history_integrity", None)
        if managed is None:
            return self._commit_operator_transition_unwrapped(kind, principal_id, change)
        return managed.mutate(
            lambda: self._commit_operator_transition_unwrapped(kind, principal_id, change),
            kind="AUTH_TRANSITION")

    def _commit_operator_transition_unwrapped(self, kind, principal_id, change):
        new_head = None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            expected = self.validate_credentials(db, principal_id)
            payload, result = change(db, expected)
            if payload is not None:
                new_head = self.authority.append(
                    db,
                    kind=kind,
                    principal=principal_id,
                    recorded_at=result.pop("recorded_at"),
                    payload=payload,
                )
            self.check_prefix()
        if new_head is not None:
            # Advance only this trusted local instance's integrity-head pin.
            # A reopened service must be handed this new external pin explicitly.
            self.authority.head_choice = new_head
        return result | {"authority_head": self.authority_head}

    def rotate_credential(self, principal_id, *, lifetime=86400):
        """Trusted local signed operation, never an HTTP password-reset route."""
        if type(lifetime) is not int or not 60 <= lifetime <= 7 * 86400:
            raise DomainError("Credential lifetime must be 60 seconds to seven days")
        key = secrets.token_urlsafe(32)

        def change(db, expected):
            if expected["revoked"] != 0:
                raise DomainError(
                    "Only an existing non-revoked principal can rotate", status=403
                )
            now = time.time()
            payload = {
                "old_token_hash": expected["token_hash"],
                "new_token_hash": self._key_hash(key),
                "old_expires": expected["expires"],
                "new_expires": now + lifetime,
                "lifetime": lifetime,
            }
            db.execute(
                "UPDATE principals SET token_hash=?,expires=? WHERE id=?",
                (payload["new_token_hash"], payload["new_expires"], principal_id),
            )
            db.execute("DELETE FROM sessions WHERE principal=?", (principal_id,))
            return payload, {
                "id": principal_id,
                "credential": key,
                "expires_at": now + lifetime,
                "prior_credentials": "INVALIDATED",
                "prior_sessions": "INVALIDATED",
                "recorded_at": now,
            }

        return self._commit_operator_transition(
            "credential.rotate", principal_id, change
        )

    def revoke(self, principal_id):
        def change(db, expected):
            if expected["revoked"] == 1:
                return None, {"id": principal_id, "revoked": True}
            db.execute("UPDATE principals SET revoked=1 WHERE id=?", (principal_id,))
            db.execute("DELETE FROM sessions WHERE principal=?", (principal_id,))
            return {"before": 0, "after": 1}, {
                "id": principal_id,
                "revoked": True,
                "recorded_at": time.time(),
            }

        return self._commit_operator_transition(
            "principal.revoke", principal_id, change
        )

    def grant(self, engagement_id, principal_id, permission):
        if engagement_id != self.prefix["engagement"] or permission not in {
            "learn",
            "review",
            "instruct",
        }:
            raise DomainError("Exact original engagement/member permission required")

        def change(db, expected):
            self._principal(db, principal_id)
            _require(
                permission in _original_permissions(expected["roles"]),
                "Membership cannot exceed the original role authority",
            )
            old = db.execute(
                "SELECT permission FROM members WHERE engagement=? AND principal=?",
                (engagement_id, principal_id),
            ).fetchone()
            if old is None:
                raise DomainError(
                    "Retained storage cannot add a new member", status=403
                )
            db.execute(
                "UPDATE members SET permission=? WHERE engagement=? AND principal=?",
                (permission, engagement_id, principal_id),
            )
            return {
                "engagement": engagement_id,
                "before": old["permission"],
                "after": permission,
            }, {
                "id": principal_id,
                "permission": permission,
                "recorded_at": time.time(),
            }

        return self._commit_operator_transition(
            "membership.grant", principal_id, change
        )

    def login(self, credential):
        managed = getattr(self, "_managed_history_integrity", None)
        if managed is None:
            return self._login_unwrapped(credential)
        return managed.mutate(lambda: self._login_unwrapped(credential), kind="AUTH_TRANSITION")

    def _login_unwrapped(self, credential):
        """Authenticate and publish the session in one ordinary writer transaction."""
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM principals WHERE token_hash=?",
                (self._key_hash(credential),),
            ).fetchone()
            if row is None:
                raise DomainError(
                    "Invalid credential", code="UNAUTHENTICATED", status=401
                )
            person = self._principal(db, row["id"])
            now = time.time()
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?)",
                (self._key_hash(token), row["id"], csrf, now + 3600, now),
            )
            issuance = {
                "token_hash": self._key_hash(token),
                "principal": row["id"],
                "csrf": csrf,
                "expires": now + 3600,
                "authenticated_at": now,
                "prefix_sha256": self.prefix["sha256"],
                "engagement": self.prefix["engagement"],
                "credential_token_hash": self._key_hash(credential),
            }
            body, signature = self.session_authority.issue(issuance)
            db.execute(
                "INSERT INTO issued_sessions VALUES (?,?,?)",
                (self._key_hash(token), body, signature),
            )
            self.check_prefix()
        return {"token": token, "csrf": csrf, "viewer": person}

    def logout(self, token):
        managed = getattr(self, "_managed_history_integrity", None)
        if managed is None:
            return self._logout_unwrapped(token)
        return managed.mutate(lambda: self._logout_unwrapped(token), kind="AUTH_TRANSITION")

    def _logout_unwrapped(self, token):
        """Normal server logout, with a signed tombstone outside mutable tables."""
        token_hash = self._key_hash(token)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT principal FROM sessions WHERE token_hash=?", (token_hash,)
            ).fetchone()
            if row is not None:
                self._principal(db, row["principal"])
                self.session_authority.logout(
                    token_hash,
                    row["principal"],
                    self.prefix["sha256"],
                    self.prefix["engagement"],
                )
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
            self.check_prefix()
