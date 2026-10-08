"""Opt-in, exact-byte complete-prefix storage; original authority is unchanged.

The mapping is storage provenance, not task/source acceptance. Its externally
pinned descriptor retains the original physical-file SHA and original identity
tuple. No caller can obtain activation authority by merely creating a mapping.
One raw row is processed at a time. Graph validation uses bounded indexed reads
and an owned temporary database containing ONLY visited node IDs, never states,
commands, originals or outcomes. The immutable derivative is fully read at cold
startup; subsequent selected reads require that published cold validation.
"""

import hashlib
import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import weakref
from pathlib import Path

from . import canonical_state_codec as codec
from .history_inspection import (
    _activity,
    _entry,
    _fields,
    _meta,
    _stamp,
    _verify_row,
)
from .sealed_history_store import (
    EVENT_COLUMNS,
    _file_sha,
    _private,
    _require,
    _schema_hash,
    _write_new,
)
from .serialized_json import canonical_bytes, update_object
from .store import _ClosingConnection, canonical, digest

SCHEMA = "SH_LOSSLESS_COMPLETE_PREFIX_STORAGE_MAPPING_V1"
MAX_RECORD_BYTES = 512 * 1024 * 1024
RESERVE = 16 * 1024**3
VERIFIED_NODE_CACHE_BYTES = 16 * 1024**2
PREFIX_KEYS = {
    "path",
    "bytes",
    "sha256",
    "engagement",
    "revision",
    "last_hash",
    "current_state_sha256",
    "initial_auth_sha256",
}
TABLES = ("principals", "sessions", "engagements", "members")
COLUMNS = {
    "principals": ("id", "name", "roles", "token_hash", "expires", "revoked"),
    "sessions": ("token_hash", "principal", "csrf", "expires", "authenticated_at"),
    "engagements": ("id", "revision", "state"),
    "members": ("engagement", "principal", "permission"),
}
SQL = """
CREATE TABLE principals(id TEXT PRIMARY KEY,name TEXT NOT NULL,roles TEXT NOT NULL,
 token_hash TEXT UNIQUE NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL);
CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,principal TEXT NOT NULL,
 csrf TEXT NOT NULL,expires REAL NOT NULL,authenticated_at REAL);
CREATE TABLE engagements(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,state TEXT NOT NULL);
CREATE TABLE members(engagement TEXT NOT NULL,principal TEXT NOT NULL,permission TEXT NOT NULL,
 PRIMARY KEY(engagement,principal));
CREATE TABLE prefix_frames(original_rowid INTEGER UNIQUE NOT NULL,engagement TEXT NOT NULL,revision INTEGER NOT NULL,
 command_id TEXT NOT NULL,request_hash TEXT NOT NULL,actor TEXT NOT NULL,
 recorded_at REAL NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL,
 state_root TEXT NOT NULL,state_bytes INTEGER NOT NULL,state_sha256 TEXT NOT NULL,
 command_root TEXT NOT NULL,command_bytes INTEGER NOT NULL,command_sha256 TEXT NOT NULL,
 PRIMARY KEY(engagement,revision),UNIQUE(engagement,command_id));
"""


def _strict_prefix(value):
    _require(
        type(value) is dict
        and set(value) == PREFIX_KEYS
        and type(value["revision"]) is int
        and value["revision"] >= 0
        and type(value["bytes"]) is int
        and value["bytes"] > 0
        and all(
            codec.valid_id(value[k])
            for k in ("sha256", "last_hash", "current_state_sha256")
        )
        and type(value["engagement"]) is str
        and value["engagement"]
        and type(value["initial_auth_sha256"]) is dict
        and set(value["initial_auth_sha256"]) == {"principals", "members", "sessions"}
        and all(codec.valid_id(x) for x in value["initial_auth_sha256"].values()),
        "Exact original physical-prefix lineage required",
    )


def _source_schema(value):
    _require(type(value) is list and value, "Original schema inventory required")
    names, tables = set(), set()
    for row in value:
        _require(
            type(row) is dict
            and set(row) == {"type", "name", "tbl_name", "sql"}
            and row["type"] in {"table", "index", "trigger"}
            and type(row["name"]) is str
            and row["name"]
            and row["tbl_name"] in set(TABLES) | {"events"}
            and (row["sql"] is None or type(row["sql"]) is str)
            and (row["type"], row["name"]) not in names,
            "Strict recorded original schema provenance required",
        )
        names.add((row["type"], row["name"]))
        if row["type"] == "table":
            tables.add(row["name"])
    _require(
        tables == set(TABLES) | {"events"},
        "Complete original schema table inventory required",
    )


def _reserve(path, floor):
    _require(
        shutil.disk_usage(path).free >= floor,
        "Complete-prefix disk reserve unavailable",
    )


def _raw(raw):
    _require(
        type(raw) is bytes and 0 < len(raw) <= MAX_RECORD_BYTES,
        "Bounded exact UTF-8 original bytes required",
    )
    text = raw.decode("utf-8")
    return text, canonical_bytes(text)


def encode_raw(db, raw):
    """Never substitute canonical bytes for the original bytes being stored."""
    _text, normalized = _raw(raw)
    encoder, parts, start = codec.BufferedEncoder(db), [], 0
    boundaries = (
        codec._fragmenter.boundaries(raw)
        if normalized == raw and codec._fragmenter is not None
        else range(codec.CHUNK, len(raw) + codec.CHUNK, codec.CHUNK)
    )
    for offset in boundaries:
        end = min(offset, len(raw))
        _require(
            type(end) is int and start < end <= len(raw) and end - start <= codec.CHUNK,
            "Exact bounded raw byte partitions required",
        )
        parts.append(encoder.put("L", raw[start:end], end - start))
        start = end
    _require(start == len(raw), "Complete original byte coverage required")
    root, size = encoder.concat(parts)
    encoder.flush()
    _require(size == len(raw), "Original byte length changed")
    return root, size, hashlib.sha256(raw).hexdigest()


def _roots(db):
    for row in db.execute(
        "SELECT state_root,command_root FROM prefix_frames ORDER BY revision"
    ):
        yield row[0]
        yield row[1]


def verify_graph(db, scratch_parent, *, bounds=None, min_free_bytes=0):
    """Fresh every node, acyclicity, depth and reachability with bounded RAM.

    The owned temporary index stores only node IDs/heights/reachability. It
    never contains a raw state, command, original, source body or outcome.
    """
    maximum_payload, maximum_bytes, maximum_depth = 0, 0, 0
    with tempfile.TemporaryDirectory(
        prefix="node-identities-", dir=scratch_parent
    ) as temporary:
        os.chmod(temporary, 0o700)
        path = Path(temporary) / "visited.sqlite3"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with sqlite3.connect(path, factory=_ClosingConnection) as seen:
            seen.execute("PRAGMA cache_size=-2048")
            seen.execute(
                "CREATE TABLE verified(id TEXT PRIMARY KEY,height INTEGER NOT NULL)"
            )
            seen.execute("CREATE TABLE seen(id TEXT PRIMARY KEY)")
            count = 0
            for row in db.execute(
                "SELECT rowid,id,kind,payload,bytes FROM state_nodes ORDER BY rowid"
            ):
                rowid, identifier, kind, payload, size = tuple(row)
                _require(
                    codec.valid_id(identifier)
                    and kind in {"L", "C"}
                    and type(payload) is bytes
                    and type(size) is int
                    and 0 < size <= MAX_RECORD_BYTES
                    and identifier == codec.node_id(kind, payload, size),
                    "Compact prefix node bytes/types differ",
                )
                height = 1
                if kind == "L":
                    _require(
                        size == len(payload) <= codec.CHUNK,
                        "Bounded exact literal required",
                    )
                else:
                    total = 0
                    for child in codec._children(payload):
                        found = db.execute(
                            "SELECT rowid,bytes FROM state_nodes WHERE id=?", (child,)
                        ).fetchone()
                        known = seen.execute(
                            "SELECT height FROM verified WHERE id=?", (child,)
                        ).fetchone()
                        _require(
                            found is not None
                            and type(found[1]) is int
                            and found[0] < rowid
                            and known is not None,
                            "Compact prefix ordered child missing/cyclic",
                        )
                        total += found[1]
                        height = max(height, known[0] + 1)
                    _require(total == size, "Compact prefix concatenation size differs")
                _require(
                    height <= codec.MAX_GRAPH_DEPTH,
                    "Compact graph height exceeds bound",
                )
                seen.execute("INSERT INTO verified VALUES (?,?)", (identifier, height))
                maximum_payload = max(maximum_payload, len(payload))
                maximum_bytes = max(maximum_bytes, size)
                maximum_depth = max(maximum_depth, height)
                count += 1
                if count % 512 == 0:
                    _reserve(scratch_parent, min_free_bytes)
            _require(count > 0, "Nonempty complete prefix node graph required")
            visited = 0
            for root in _roots(db):
                stack = [root]
                while stack:
                    identifier = stack.pop()
                    cursor = seen.execute(
                        "INSERT OR IGNORE INTO seen VALUES (?)", (identifier,)
                    )
                    if not cursor.rowcount:
                        continue
                    visited += 1
                    if visited % 512 == 0:
                        _reserve(scratch_parent, min_free_bytes)
                    row = db.execute(
                        "SELECT kind,payload FROM state_nodes WHERE id=?", (identifier,)
                    ).fetchone()
                    _require(row is not None, "Compact prefix root is missing")
                    if row[0] == "C":
                        stack.extend(reversed(codec._children(row[1])))
            _require(
                seen.execute("SELECT count(*) FROM seen").fetchone()[0] == count,
                "Unreachable/foreign compact prefix node refused",
            )
    if bounds is not None:
        bounds.update(
            node_payload_bytes=maximum_payload,
            node_reconstructed_bytes=maximum_bytes,
            max_graph_depth=maximum_depth,
        )
    return count


def _projection(db):
    result = {}
    for name in TABLES:
        _require(
            tuple(r[1] for r in db.execute(f"PRAGMA table_info({name})"))
            == COLUMNS[name],
            "Original header/authority column shape differs",
        )
        hasher, count = hashlib.sha256(b"["), 0
        for row in db.execute(f"SELECT * FROM {name} ORDER BY 1,2"):
            if count:
                hasher.update(b",")
            hasher.update(canonical(dict(row)).encode())
            count += 1
        hasher.update(b"]")
        result[name] = {"count": count, "sha256": hasher.hexdigest()}
    return result


def _row_contract(row, eid, revision):
    _require(
        row["engagement"] == eid
        and type(row["revision"]) is int
        and row["revision"] == revision
        and type(row["recorded_at"]) in (int, float)
        and math.isfinite(row["recorded_at"])
        and all(type(row[k]) is str for k in ("actor", "command_id", "previous_hash"))
        and row["actor"]
        and row["command_id"]
        and codec.valid_id(row["request_hash"])
        and codec.valid_id(row["hash"]),
        "Strict original event identity/metadata required",
    )


def convert_prefix(
    prefix,
    destination,
    *,
    recovery_receipts,
    min_free_bytes=RESERVE,
    engineering_neutral_only=False,
):
    """Create a derivative; never modify/adopt/retire the original or active tail.

    Recovery receipts are externally supplied provenance pins, not automatically
    interpreted backup authority. Actual use additionally requires root review
    of independent backups, quiescence, and this exact storage mapping.
    """
    _strict_prefix(prefix)
    _require(
        type(engineering_neutral_only) is bool
        and type(min_free_bytes) is int
        and min_free_bytes >= (0 if engineering_neutral_only else RESERVE),
        "Strict actual disk reserve required",
    )
    _require(
        type(recovery_receipts) is list and recovery_receipts,
        "Explicit independently reviewed recovery receipts required",
    )
    recovery = []
    for pin in recovery_receipts:
        _require(
            type(pin) is dict and set(pin) == {"path", "sha256"},
            "Exact recovery pin required",
        )
        path = _private(pin["path"])
        _require(
            codec.valid_id(pin["sha256"]) and _file_sha(path) == pin["sha256"],
            "Recovery receipt bytes changed",
        )
        recovery.append((pin, _stamp(path)))
    original = _private(prefix["path"])
    before = _stamp(original)
    _require(
        not any(before[0][1:])
        and original.stat().st_size == prefix["bytes"]
        and _file_sha(original) == prefix["sha256"],
        "Exact quiescent original required",
    )
    destination = Path(destination).absolute()
    _require(
        destination == destination.resolve() and not destination.exists(),
        "New unaliased derivative namespace required",
    )
    _private(destination.parent, directory=True)
    _reserve(destination.parent, min_free_bytes)
    destination.mkdir(mode=0o700)
    target = destination / "prefix.sqlite3"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    rolling, vector, previous, count = hashlib.sha256(b"["), hashlib.sha256(b"["), "", 0
    bounds = {
        "state_raw_bytes": 0,
        "command_raw_bytes": 0,
        "state_command_raw_bytes": 0,
        "frame_descriptor_bytes": 0,
    }
    with (
        sqlite3.connect(
            original.as_uri() + "?immutable=1", uri=True, factory=_ClosingConnection
        ) as src,
        sqlite3.connect(target, factory=_ClosingConnection) as dst,
    ):
        src.row_factory = dst.row_factory = sqlite3.Row
        src.execute("BEGIN")
        src.execute("PRAGMA query_only=ON")
        _require(
            src.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            and not src.execute("PRAGMA foreign_key_check").fetchone(),
            "Original SQLite integrity differs",
        )
        _require(
            {
                r[0]
                for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            == set(TABLES) | {"events"},
            "Unsupported original tables refused losslessly",
        )
        _require(
            tuple(r[1] for r in src.execute("PRAGMA table_info(events)"))
            == EVENT_COLUMNS,
            "Unsupported original event column shape cannot be conserved",
        )
        schema = [
            dict(r)
            for r in src.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ]
        _source_schema(schema)
        original_projection = _projection(src)
        _require(
            original_projection["engagements"]["count"] == 1,
            "Exactly one original engagement required",
        )
        dst.execute("PRAGMA cache_size=-8192")
        dst.executescript(SQL + codec.SQL)
        for name in TABLES:
            for row in src.execute(f"SELECT * FROM {name} ORDER BY 1,2"):
                dst.execute(
                    f"INSERT INTO {name} VALUES (" + ",".join("?" for _ in row) + ")",
                    tuple(row),
                )
        current = src.execute("SELECT id,revision,state FROM engagements").fetchone()
        _require(
            current["id"] == prefix["engagement"]
            and type(current["revision"]) is int
            and current["revision"] == prefix["revision"]
            and hashlib.sha256(current["state"].encode()).hexdigest()
            == prefix["current_state_sha256"],
            "Original current header differs",
        )
        _require(
            all(
                original_projection[k]["sha256"] == prefix["initial_auth_sha256"][k]
                for k in ("principals", "members", "sessions")
            ),
            "Original authority projection differs",
        )
        for row in src.execute(
            "SELECT rowid AS original_rowid,* FROM events WHERE engagement=? ORDER BY revision",
            (prefix["engagement"],),
        ):
            _reserve(destination, min_free_bytes)
            _row_contract(row, prefix["engagement"], count)
            _require(
                type(row["state"]) is str and type(row["command"]) is str,
                "Original TEXT types required",
            )
            raw_state, raw_command = row["state"].encode(), row["command"].encode()
            _state_text, state_bytes = _raw(raw_state)
            _command_text, command_bytes = _raw(raw_command)
            fields = _fields(row, state_bytes, command_bytes)
            _verify_row(row, fields, count, previous)
            state = encode_raw(dst, raw_state)
            command = encode_raw(dst, raw_command)
            for raw, descriptor in ((raw_state, state), (raw_command, command)):
                offset = 0
                for chunk in codec.chunks(dst, descriptor[0]):
                    _require(
                        raw[offset : offset + len(chunk)] == chunk,
                        "Lossless original byte comparison failed",
                    )
                    offset += len(chunk)
                _require(offset == len(raw), "Lossless original bytes incomplete")
            _require(
                type(row["original_rowid"]) is int and row["original_rowid"] > 0,
                "Exact original physical row locator required",
            )
            dst.execute(
                "INSERT INTO prefix_frames VALUES ("
                + ",".join("?" for _ in range(15))
                + ")",
                (row["original_rowid"],)
                + tuple(row[k] for k in EVENT_COLUMNS[:8])
                + state
                + command,
            )
            if count:
                rolling.update(b",")
                vector.update(b",")
            update_object(
                rolling,
                fields
                | {
                    "hash": canonical(row["hash"]).encode(),
                    "revision": canonical(count).encode(),
                },
            )
            descriptor = canonical(
                dict(zip(EVENT_COLUMNS[:8], tuple(row[k] for k in EVENT_COLUMNS[:8])))
                | {
                    "original_rowid": row["original_rowid"],
                    "state": dict(zip(("root", "bytes", "sha256"), state)),
                    "command": dict(zip(("root", "bytes", "sha256"), command)),
                }
            ).encode()
            vector.update(descriptor)
            bounds["state_raw_bytes"] = max(bounds["state_raw_bytes"], len(raw_state))
            bounds["command_raw_bytes"] = max(
                bounds["command_raw_bytes"], len(raw_command)
            )
            bounds["state_command_raw_bytes"] = max(
                bounds["state_command_raw_bytes"], len(raw_state) + len(raw_command)
            )
            bounds["frame_descriptor_bytes"] = max(
                bounds["frame_descriptor_bytes"], len(descriptor)
            )
            previous, count = row["hash"], count + 1
            _reserve(destination, min_free_bytes)
        _require(
            count == prefix["revision"] + 1
            and previous == prefix["last_hash"]
            and raw_state == current["state"].encode()
            and src.execute("SELECT count(*) FROM events").fetchone()[0] == count,
            "Original complete count/tip/current/foreign history differs",
        )
        _require(
            _projection(dst) == original_projection,
            "Copied original header/authority changed",
        )
        node_count = verify_graph(
            dst, destination, bounds=bounds, min_free_bytes=min_free_bytes
        )
        derivative_schema = _schema_hash(dst)
        dst.commit()
    interim = _stamp(original)
    _require(
        interim == before and not any(interim[0][1:]),
        "Original identity/sidecars changed during conversion",
    )
    for pin, stamp in recovery:
        _require(
            _stamp(pin["path"]) == stamp
            and _file_sha(pin["path"]) == pin["sha256"]
            and _stamp(pin["path"]) == stamp,
            "Recovery receipt changed",
        )
    _require(not any(_stamp(target)[0][1:]), "Derivative sidecars remain")
    with target.open("rb") as stream:
        os.fsync(stream.fileno())
    rolling.update(b"]")
    vector.update(b"]")
    mapping = {
        "schema": SCHEMA,
        "original_prefix": prefix,
        "storage": {
            "path": str(target),
            "sha256": _file_sha(target),
            "bytes": target.stat().st_size,
            "schema_sha256": derivative_schema,
        },
        "source_schema": schema,
        "header_projection": original_projection,
        "history": {
            "count": count,
            "tip": previous,
            "history_sha256": rolling.hexdigest(),
            "frame_vector_sha256": vector.hexdigest(),
            "node_count": node_count,
        },
        "bounds": bounds,
        "recovery_receipts": recovery_receipts,
        "engineering_neutral_only": engineering_neutral_only,
        "activation_authorized": False,
        "original_modified_or_retired": False,
    }
    storage_stamp = _stamp(target)
    path = destination / "STORAGE_MAPPING.json"
    _write_new(path, mapping)
    _require(
        _stamp(target) == storage_stamp
        and _file_sha(target) == mapping["storage"]["sha256"]
        and _stamp(target) == storage_stamp
        and _stamp(original) == before
        and _file_sha(original) == prefix["sha256"]
        and _stamp(original) == before,
        "Final source/derivative bytes or identities changed before publication",
    )
    for pin, stamp in recovery:
        _require(
            _stamp(pin["path"]) == stamp
            and _file_sha(pin["path"]) == pin["sha256"]
            and _stamp(pin["path"]) == stamp,
            "Final recovery receipt closure changed",
        )
    _reserve(destination, min_free_bytes)
    return {"path": str(path), "sha256": _file_sha(path)}


class _VerifiedNodePool:
    """Connection-local, fill-once immutable node tuples; never decoded records.

    Fixed bucket heads avoid an unaccounted dictionary resize. Each retained
    linked tuple, identifier and node value is charged before insertion; shared
    Python objects are deliberately charged again. The small fixed reserve
    covers the connection callback, close wrapper and accounting integers.
    """

    def __init__(self, db, owner, schema):
        self.connection = weakref.ref(db)
        self.owner, self.schema = owner, schema
        self.path, self.database, self.stamps = owner.path, owner.database, owner.stamps
        self.buckets = [None] * 4096
        self.base_bytes = (
            sys.getsizeof(self) + sys.getsizeof(self.__dict__)
            + sys.getsizeof(self.buckets) + 4096
        )
        self.bytes, self.count, self.disabled = self.base_bytes, 0, False

    def clear(self, *, disable=False):
        for index in range(len(self.buckets)):
            self.buckets[index] = None
        self.bytes, self.count = self.base_bytes, 0
        self.disabled |= disable

    def check(self, db):
        _require(self.connection() is db, "Compact node cache connection differs")
        names = {row[1]: row[2] for row in db.execute("PRAGMA database_list")}
        _require(
            self.owner._nodes_verified
            and (self.owner.path, self.owner.database, self.owner.stamps)
            == (self.path, self.database, self.stamps)
            and names.get(self.schema) == str(self.database)
            and _stamp(self.path) == self.stamps[0]
            and _stamp(self.database) == self.stamps[1],
            "Compact node cache storage identity differs",
        )

    def get(self, identifier):
        entry = self.buckets[hash(identifier) & 4095]
        while entry is not None:
            if entry[0] == identifier:
                return entry[1]
            entry = entry[2]
        return None

    def put(self, identifier, node):
        if self.disabled:
            return
        index = hash(identifier) & 4095
        entry = (identifier, node, self.buckets[index])
        charge = (
            sys.getsizeof(entry) + sys.getsizeof(identifier)
            + sys.getsizeof(node) + sum(sys.getsizeof(value) for value in node)
        )
        if self.bytes + charge <= VERIFIED_NODE_CACHE_BYTES:
            self.buckets[index] = entry
            self.bytes += charge
            self.count += 1


class _CompactDecode:
    def __init__(self, db, owner, schema, pool):
        self.connection, self.owner = weakref.ref(db), owner
        self.schema, self.pool = schema, pool

    def __call__(self, root, size, sha):
        return self.owner.decode(
            self.connection(), root, size, sha, schema=self.schema
        )

    def __del__(self):
        # SQLite also releases the callback if the connection is finalized.
        self.pool.clear(disable=True)


class CompactPrefix:
    """Externally explicit storage mapping, never a new authority lineage."""

    def __init__(self, pin, original_prefix):
        self._nodes_verified = False
        _strict_prefix(original_prefix)
        _require(
            type(pin) is dict
            and set(pin) == {"path", "sha256"}
            and codec.valid_id(pin["sha256"]),
            "Explicit compact mapping pin required",
        )
        self.path = _private(pin["path"])
        self.pin = pin
        mapping_stamp = _stamp(self.path)
        with self.path.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        _require(
            0 < len(raw) <= 1024 * 1024
            and hashlib.sha256(raw).hexdigest() == pin["sha256"]
            and _stamp(self.path) == mapping_stamp,
            "Consumed compact mapping bytes or opening identity differ",
        )
        self.mapping = json.loads(raw)
        m = self.mapping
        _require(
            type(m) is dict
            and set(m)
            == {
                "schema",
                "original_prefix",
                "storage",
                "source_schema",
                "header_projection",
                "history",
                "recovery_receipts",
                "engineering_neutral_only",
                "activation_authorized",
                "original_modified_or_retired",
                "bounds",
            }
            and m["schema"] == SCHEMA
            and digest(m["original_prefix"]) == digest(original_prefix)
            and type(m["engineering_neutral_only"]) is bool
            and m["activation_authorized"] is False
            and m["original_modified_or_retired"] is False,
            "Exact original lineage/storage-only mapping required",
        )
        _source_schema(m["source_schema"])
        headers = m["header_projection"]
        _require(
            type(headers) is dict
            and set(headers) == set(TABLES)
            and all(
                type(v) is dict
                and set(v) == {"count", "sha256"}
                and type(v["count"]) is int
                and v["count"] >= 0
                and codec.valid_id(v["sha256"])
                for v in headers.values()
            ),
            "Strict original typed header projection required",
        )
        _require(
            type(m["recovery_receipts"]) is list and m["recovery_receipts"],
            "Original explicit recovery receipt inventory required",
        )
        self.recoveries = []
        for item in m["recovery_receipts"]:
            _require(
                type(item) is dict
                and set(item) == {"path", "sha256"}
                and codec.valid_id(item["sha256"]),
                "Exact recovery receipt descriptor required",
            )
            path = _private(item["path"])
            _require(
                _file_sha(path) == item["sha256"], "Recovery receipt provenance changed"
            )
            self.recoveries.append((item, _stamp(path)))
        storage = m["storage"]
        _require(
            type(storage) is dict
            and set(storage) == {"path", "sha256", "bytes", "schema_sha256"}
            and codec.valid_id(storage["sha256"])
            and codec.valid_id(storage["schema_sha256"])
            and type(storage["bytes"]) is int
            and storage["bytes"] > 0,
            "Exact compact storage descriptor required",
        )
        self.database = _private(storage["path"])
        storage_stamp = _stamp(self.database)
        _require(
            self.database.parent == self.path.parent
            and self.database != Path(original_prefix["path"])
            and self.database.stat().st_size == storage["bytes"]
            and _file_sha(self.database) == storage["sha256"]
            and _stamp(self.database) == storage_stamp,
            "Compact storage bytes or opening identity differ",
        )
        self.stamps = (mapping_stamp, storage_stamp)
        self.check()

        history = m["history"]
        _require(
            type(history) is dict
            and set(history)
            == {"count", "tip", "history_sha256", "frame_vector_sha256", "node_count"}
            and type(history["count"]) is int
            and history["count"] == original_prefix["revision"] + 1
            and type(history["node_count"]) is int
            and history["node_count"] > 0
            and history["tip"] == original_prefix["last_hash"]
            and codec.valid_id(history["history_sha256"])
            and codec.valid_id(history["frame_vector_sha256"]),
            "Strict original history/vector descriptors required",
        )
        with self.connection() as db:
            _require(
                db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                and _schema_hash(db) == storage["schema_sha256"],
                "Compact SQLite/schema integrity failed",
            )
            _require(
                {
                    r[0]
                    for r in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                == set(TABLES) | {"prefix_frames", "state_nodes"}
                and not db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='view'"
                ).fetchone(),
                "Known complete compact table inventory required",
            )
            _require(
                tuple(r[1] for r in db.execute("PRAGMA table_info(prefix_frames)"))
                == ("original_rowid",)
                + EVENT_COLUMNS[:8]
                + (
                    "state_root",
                    "state_bytes",
                    "state_sha256",
                    "command_root",
                    "command_bytes",
                    "command_sha256",
                )
                and tuple(r[1] for r in db.execute("PRAGMA table_info(state_nodes)"))
                == ("id", "kind", "payload", "bytes"),
                "Known complete compact frame/node columns required",
            )
            observed = {}
            self.node_count = verify_graph(db, self.path.parent, bounds=observed)
            _require(
                self.node_count == history["node_count"]
                and digest(_projection(db)) == digest(m["header_projection"]),
                "Complete compact node/header inventory differs",
            )
            declared = m["bounds"]
            _require(
                type(declared) is dict
                and set(declared)
                == {
                    "state_raw_bytes",
                    "command_raw_bytes",
                    "state_command_raw_bytes",
                    "frame_descriptor_bytes",
                    "node_payload_bytes",
                    "node_reconstructed_bytes",
                    "max_graph_depth",
                }
                and all(type(v) is int and v > 0 for v in declared.values()),
                "Strict observed complete-prefix maximum bounds required",
            )
            observed.update(
                state_raw_bytes=0,
                command_raw_bytes=0,
                state_command_raw_bytes=0,
                frame_descriptor_bytes=0,
            )
            vector, count = hashlib.sha256(b"["), 0
            for row in db.execute("SELECT * FROM prefix_frames ORDER BY revision"):
                _row_contract(row, original_prefix["engagement"], count)
                if count:
                    vector.update(b",")
                _require(
                    type(row["original_rowid"]) is int and row["original_rowid"] > 0,
                    "Strict original row locator required",
                )
                value = {key: row[key] for key in EVENT_COLUMNS[:8]} | {
                    "original_rowid": row["original_rowid"]
                }
                for kind in ("state", "command"):
                    value[kind] = {
                        key: row[kind + "_" + key]
                        for key in ("root", "bytes", "sha256")
                    }
                    _require(
                        codec.valid_id(value[kind]["root"])
                        and codec.valid_id(value[kind]["sha256"])
                        and type(value[kind]["bytes"]) is int
                        and 0 < value[kind]["bytes"] <= MAX_RECORD_BYTES,
                        "Strict exact raw frame locators required",
                    )
                descriptor = canonical(value).encode()
                vector.update(descriptor)
                count += 1
                observed["state_raw_bytes"] = max(
                    observed["state_raw_bytes"], value["state"]["bytes"]
                )
                observed["command_raw_bytes"] = max(
                    observed["command_raw_bytes"], value["command"]["bytes"]
                )
                observed["state_command_raw_bytes"] = max(
                    observed["state_command_raw_bytes"],
                    value["state"]["bytes"] + value["command"]["bytes"],
                )
                observed["frame_descriptor_bytes"] = max(
                    observed["frame_descriptor_bytes"], len(descriptor)
                )
            vector.update(b"]")
            _require(
                count == history["count"]
                and vector.hexdigest() == history["frame_vector_sha256"],
                "Complete ordered raw-frame vector differs",
            )
            _require(observed == declared, "Observed compact maximum bounds differ")
        _require(
            _file_sha(self.database) == storage["sha256"],
            "Compact storage bytes changed during cold construction",
        )
        self.check()
        # Only the completed cold graph, type, byte and identity closure admits
        # memoization. The constructor's own connection remains uncached.
        self._nodes_verified = True

    def check(self):
        _private(self.path)
        _private(self.database)
        _require(
            (_stamp(self.path), _stamp(self.database)) == self.stamps
            and not any(self.stamps[0][0][1:])
            and not any(self.stamps[1][0][1:]),
            "Compact mapping/storage identity or sidecars changed",
        )
        for item, stamp in self.recoveries:
            _private(item["path"])
            _require(
                _stamp(item["path"]) == stamp
                and _file_sha(item["path"]) == item["sha256"]
                and _stamp(item["path"]) == stamp,
                "Recovery receipt closing identity/bytes changed",
            )
        return self.stamps

    @staticmethod
    def decode(db, root, size, sha, *, schema="main"):
        bound_pool = getattr(db, "_compact_prefix_nodes", None)
        pool = bound_pool
        if pool is not None and pool.schema != schema:
            pool = None
        try:
            if pool is not None:
                pool.check(db)
            return CompactPrefix._decode(db, root, size, sha, schema=schema, pool=pool)
        except BaseException:
            if bound_pool is not None:
                bound_pool.clear(disable=True)
            raise

    @staticmethod
    def _decode(db, root, size, sha, *, schema, pool):
        _require(
            codec.valid_id(root)
            and codec.valid_id(sha)
            and type(size) is int
            and 0 < size <= MAX_RECORD_BYTES,
            "Strict compact raw-byte locator required",
        )
        _require(
            schema in {"main", "sealed_prefix"}, "Fixed prefix node schema required"
        )
        result, active, stack = bytearray(), set(), [(root, False)]
        while stack:
            identifier, closing = stack.pop()
            if closing:
                active.remove(identifier)
                continue
            _require(
                identifier not in active and len(active) < codec.MAX_GRAPH_DEPTH,
                "Compact raw graph cycle/depth refused",
            )
            node = pool.get(identifier) if pool is not None else None
            if node is None:
                row = db.execute(
                    f"SELECT kind,payload,bytes FROM {schema}.state_nodes WHERE id=?",
                    (identifier,),
                ).fetchone()
                _require(row is not None, "Compact raw node missing")
                node = tuple(row)
                kind, payload, length = node
                _require(
                    kind in {"L", "C"}
                    and type(payload) is bytes
                    and type(length) is int
                    and identifier == codec.node_id(kind, payload, length),
                    "Compact raw node differs",
                )
                if pool is not None:
                    pool.put(identifier, node)
            kind, payload, length = node
            _require(
                kind in {"L", "C"}
                and type(payload) is bytes
                and type(length) is int,
                "Compact raw node differs",
            )
            if kind == "L":
                _require(
                    length == len(payload) <= codec.CHUNK
                    and len(result) + length <= size,
                    "Compact raw bytes exceed exact length",
                )
                result.extend(payload)
            else:
                active.add(identifier)
                stack.append((identifier, True))
                stack.extend(
                    (child, False) for child in reversed(codec._children(payload))
                )
        _require(
            len(result) == size and hashlib.sha256(result).hexdigest() == sha,
            "Compact raw bytes digest differs",
        )
        if pool is not None:
            pool.check(db)
        return result.decode("utf-8")

    def install(self, db, *, schema="main", view="events"):
        _require(
            (schema, view) in {("main", "events"), ("sealed_prefix", "prefix_events")},
            "Fixed compact projection namespace required",
        )
        if getattr(self, "_nodes_verified", False) and isinstance(db, _ClosingConnection):
            _require(
                not hasattr(db, "_compact_prefix_nodes"),
                "Compact node cache is already bound to this connection",
            )
            pool = _VerifiedNodePool(db, self, schema)
            pool.check(db)
            db._compact_prefix_nodes = pool
            reference, original_close = weakref.ref(db), type(db).close

            def close():
                pool.clear(disable=True)
                try:
                    return original_close(reference())
                finally:
                    pool.clear(disable=True)

            db.close = close
            callback = _CompactDecode(db, self, schema, pool)
        else:
            callback = lambda root, size, sha: self.decode(db, root, size, sha, schema=schema)
        try:
            db.create_function("compact_prefix_decode", 3, callback)
            columns = ",".join(EVENT_COLUMNS[:8])
            db.execute(
                f"CREATE TEMP VIEW {view} AS SELECT original_rowid AS rowid,{columns},"
                "compact_prefix_decode(state_root,state_bytes,state_sha256) AS state,"
                "compact_prefix_decode(command_root,command_bytes,command_sha256) AS command "
                f"FROM {schema}.prefix_frames"
            )
        except BaseException:
            pool = getattr(db, "_compact_prefix_nodes", None)
            if pool is not None:
                pool.clear(disable=True)
            raise

    def connection(self):
        self.check()
        db = sqlite3.connect(
            self.database.as_uri() + "?immutable=1",
            uri=True,
            factory=_ClosingConnection,
        )
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA cache_size=-8192")
            self.install(db)
            db.execute("PRAGMA query_only=ON")
            return db
        except BaseException:
            db.close()
            raise

    def selected(self, db, wanted, proof):
        """Logical roots replace physical page locators, preserving cold proof."""
        self.check()
        current = db.execute("SELECT revision,state FROM engagements").fetchone()
        _require(
            type(current["revision"]) is int
            and current["revision"] == proof["count"] - 1,
            "Compact selected current boundary differs",
        )
        selected, prefixes, activity, last, previous, count = {}, {}, [], None, "", 0
        for row in db.execute(
            "SELECT original_rowid AS locator_rowid,* FROM prefix_frames ORDER BY revision"
        ):
            rowid = row["locator_rowid"]
            _row_contract(row, self.mapping["original_prefix"]["engagement"], count)
            _require(
                row["previous_hash"] == previous
                and _meta(row) == proof["metadata"].get(rowid),
                "Compact cold-validated event metadata differs",
            )
            command_text = self.decode(
                db, row["command_root"], row["command_bytes"], row["command_sha256"]
            )
            raw_command = command_text.encode()
            command_bytes = canonical_bytes(command_text)
            _require(
                (len(raw_command), hashlib.sha256(raw_command).hexdigest())
                == proof["expected"][rowid]
                and hashlib.sha256(command_bytes).hexdigest() == row["request_hash"],
                "Original compact command bytes differ",
            )
            command = json.loads(command_text)
            if count in wanted or count == current["revision"]:
                state_text = self.decode(
                    db, row["state_root"], row["state_bytes"], row["state_sha256"]
                )
                descriptor = proof["state_integrity"][rowid]
                _require(
                    len(state_text.encode()) == descriptor["bytes"]
                    and hashlib.sha256(state_text.encode()).hexdigest()
                    == descriptor["sha256"],
                    "Original compact selected state bytes differ",
                )
                state_bytes = canonical_bytes(state_text)
                _verify_row(
                    row, _fields(row, state_bytes, command_bytes), count, previous
                )
                entry = _entry(row, json.loads(state_text), command)
                if count in wanted:
                    selected[count], prefixes[count] = entry, proof["prefixes"][count]
                if count == current["revision"]:
                    last = entry
            activity.append(_activity(row, command, command_bytes))
            previous, count = row["hash"], count + 1
        _require(
            count == proof["count"]
            and last is not None
            and digest(last["state"]) == digest(json.loads(current["state"])),
            "Complete compact selected history differs",
        )
        self.check()
        return {
            "count": count,
            "latest": last,
            "selected": selected,
            "prefix_sha256": prefixes,
            "history_sha256": proof["history_sha256"],
            "activity": activity,
            "_latest_canonical_bytes": canonical_bytes(current["state"]),
        }
