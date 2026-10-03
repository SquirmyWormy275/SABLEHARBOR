"""Lossless authoritative JSON fragments, not an evidence or outcome cache.

Each event root reconstructs its original complete canonical state bytes. The
ordinary current state remains unchanged. Repeated exact fragments are stored
once in the journal; changed fragments create new immutable nodes. Integrity
proofs contain only IDs, lengths and child locators, never decoded state.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import sqlite3
import sysconfig
from pathlib import Path

from .store import DomainError, canonical

try:
    _fragmenter = importlib.import_module("enterprise.audit_suite._canonical_fragmenter_native")
except ModuleNotFoundError as error:
    if error.name != "enterprise.audit_suite._canonical_fragmenter_native":
        raise
    _fragmenter = None

SCHEMA = "SH_EXACT_CANONICAL_STATE_FRAGMENTS_V1"
DOMAIN = (SCHEMA + "\0").encode()
CHUNK = 65536
FANOUT = 128
MAX_BYTES = 2 * 1024**3
MAX_GRAPH_DEPTH = 4096
MAX_INVOCATION_BLOCK = 65536
MAX_INVOCATION_BLOCK_BYTES = 32 * 1024**2
SQL = """
CREATE TABLE state_nodes (
 id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload BLOB NOT NULL,bytes INTEGER NOT NULL);
CREATE TRIGGER state_nodes_no_update BEFORE UPDATE ON state_nodes
 BEGIN SELECT RAISE(ABORT,'canonical fragments are immutable'); END;
CREATE TRIGGER state_nodes_no_delete BEFORE DELETE ON state_nodes
 BEGIN SELECT RAISE(ABORT,'canonical fragments are immutable'); END;
"""


def require(condition, message):
    if not condition:
        raise DomainError(message, code="INTEGRITY", status=503)


def node_id(kind, payload, size):
    return hashlib.sha256(
        DOMAIN + kind.encode("ascii") + b"\0" + str(size).encode("ascii") + b"\0" + payload
    ).hexdigest()


def valid_id(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _children(raw):
    require(len(raw) <= FANOUT * 68 + 2, "Bounded canonical child references required")
    try:
        values = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DomainError(
            "Malformed canonical child references", code="INTEGRITY", status=503
        ) from error
    require(
        type(values) is list
        and 1 <= len(values) <= FANOUT
        and all(valid_id(x) for x in values)
        and canonical(values).encode() == raw,
        "Canonical ordered child locators required",
    )
    return tuple(values)


class VerifiedInvocationGraph:
    """Fresh authoritative bytes, confined to one consistent connection.

    No evidence, examination result or decoded JSON survives close. Exact small
    byte blocks may share reconstruction work within this invocation, capped at
    32MiB; full canonical state/event/request SHA calculations still use the
    actual reconstructed bytes. Ordinary unverified decode retains every hash.
    """

    def __init__(self, db, roots):
        require(db.in_transaction, "Consistent transaction required for fresh graph proof")
        self._db = db
        self._roots = frozenset(roots)
        self._nodes = {}
        self._proof = verify_nodes(db, roots, contents=self._nodes)
        self._changes = db.total_changes
        self._blocks, self._block_bytes = {}, 0

    @classmethod
    def from_request_proof(cls, db, proof):
        # The request coordinator checked exact physical journal/sidecar
        # identity and root membership under this reserved transaction. These
        # bytes were freshly checked earlier in this same HTTP invocation.
        require(db.in_transaction, "Consistent request graph transaction required")
        result = cls.__new__(cls)
        result._db = db
        result._nodes, result._proof = proof["nodes"], proof["proof"]
        result._roots = proof["roots"]
        result._changes = db.total_changes
        result._blocks, result._block_bytes = {}, 0
        return result

    def check(self, db):
        require(
            self._db is db and db.in_transaction and db.total_changes == self._changes,
            "Invocation graph closed, changed or belongs to another transaction",
        )

    def close(self):
        self._nodes.clear()
        self._proof.clear()
        self._blocks.clear()
        self._db = None

    def chunks(self, db, root):
        self.check(db)
        require(valid_id(root) and root in self._proof, "Verified invocation root unavailable")
        stack, total = [root], 0
        while stack:
            identifier = stack.pop()
            kind, raw, size = self._nodes[identifier]
            cached = self._blocks.get(identifier)
            if cached is not None:
                total += len(cached)
                yield cached
            elif kind == "L":
                total += size
                yield raw
            elif (
                size <= MAX_INVOCATION_BLOCK
                and self._block_bytes + size <= MAX_INVOCATION_BLOCK_BYTES
            ):
                # The complete graph has already been freshly byte-hashed and
                # every concatenation/order/count/depth verified in this call.
                parts, pending = [], [identifier]
                while pending:
                    child = pending.pop()
                    ck, cr, _cs = self._nodes[child]
                    if ck == "L":
                        parts.append(cr)
                    elif child in self._blocks:
                        parts.append(self._blocks[child])
                    else:
                        pending.extend(reversed(self._proof[child]["children"]))
                block = b"".join(parts)
                require(len(block) == size, "Exact invocation block reconstruction differs")
                self._blocks[identifier] = block
                self._block_bytes += size
                total += size
                yield block
            else:
                stack.extend(reversed(self._proof[identifier]["children"]))
        require(total == self._proof[root]["bytes"], "Exact invocation state byte count differs")
        self.check(db)


class Encoder:
    """One actual write transaction; temporary input interning ends with it."""

    def __init__(self, db):
        self.db = db
        self.intern = {}

    def put(self, kind, payload, size):
        key = (kind, payload, size)
        old = self.intern.get(key)
        if old is not None:
            return old
        identifier = node_id(kind, payload, size)
        self.db.execute(
            "INSERT OR IGNORE INTO state_nodes VALUES (?,?,?,?)",
            (
                identifier,
                kind,
                payload,
                size,
            ),
        )
        stored = self.db.execute(
            "SELECT kind,payload,bytes FROM state_nodes WHERE id=?", (identifier,)
        ).fetchone()
        require(tuple(stored) == (kind, payload, size), "Existing canonical fragment differs")
        result = (identifier, size)
        self.intern[key] = result
        return result

    def concat(self, fragments):
        require(bool(fragments), "Nonempty canonical fragment sequence required")
        while len(fragments) > 1:
            fragments = [
                self.put(
                    "C",
                    canonical([v[0] for v in fragments[i : i + FANOUT]]).encode(),
                    sum(v[1] for v in fragments[i : i + FANOUT]),
                )
                for i in range(0, len(fragments), FANOUT)
            ]
        return fragments[0]

    def literal(self, raw):
        require(type(raw) is bytes and raw, "Nonempty exact canonical fragment required")
        return self.concat(
            [
                self.put("L", raw[i : i + CHUNK], len(raw[i : i + CHUNK]))
                for i in range(0, len(raw), CHUNK)
            ]
        )

    def value(self, value):
        if type(value) is dict and all(type(k) is str for k in value):
            parts = [self.literal(b"{")]
            for index, key in enumerate(sorted(value)):
                if index:
                    parts.append(self.literal(b","))
                parts.extend(
                    (
                        self.literal(canonical(key).encode()),
                        self.literal(b":"),
                        self.value(value[key]),
                    )
                )
            parts.append(self.literal(b"}"))
            return self.concat(parts)
        if type(value) in (list, tuple):
            parts = [self.literal(b"[")]
            for index, item in enumerate(value):
                if index:
                    parts.append(self.literal(b","))
                parts.append(self.value(item))
            parts.append(self.literal(b"]"))
            return self.concat(parts)
        # Preserve the original json.dumps contract for scalars/legacy keys.
        return self.literal(canonical(value).encode())


def _structural_encode(db, value):
    # Preserve exact existing type/nonfinite/circular/depth error semantics
    # before publishing any fragment for an inadmissible state.
    reference = canonical(value).encode()
    # The original C json encoder admits deeper values than a Python recursive
    # structural decomposition. Preserve those bytes without a new recursion
    # failure; literal chunking remains bounded and lossless.
    stack, deep = [(value, 0)], False
    while stack and not deep:
        item, depth = stack.pop()
        deep = depth > 128
        if type(item) is dict:
            stack.extend((x, depth + 1) for x in item.values())
        elif type(item) in (list, tuple):
            stack.extend((x, depth + 1) for x in item)
    encoder = Encoder(db)
    root, size = encoder.literal(reference) if deep else encoder.value(value)
    require(
        size == len(reference) <= MAX_BYTES, "Canonical state byte length differs or exceeds bound"
    )
    return root, size


def native_code_files():
    """Explicit loaded encoder helper origins; never compile during import."""
    if _fragmenter is None:
        return {}
    path = Path(_fragmenter.__file__)
    if (
        path.name != "_canonical_fragmenter_native" + sysconfig.get_config_var("EXT_SUFFIX")
        or getattr(_fragmenter.__spec__, "name", None)
        != "enterprise.audit_suite._canonical_fragmenter_native"
        or Path(_fragmenter.__spec__.origin).resolve() != path.resolve()
    ):
        raise DomainError("Loaded byte fragmenter origin or interpreter ABI differs")
    return {
        path.name: path,
        "_canonical_fragmenter_native.c": Path(__file__).with_name(
            "_canonical_fragmenter_native.c"
        ),
    }


class BufferedEncoder:
    def __init__(self, db):
        self.db = db
        self.pending = {}

    def put(self, kind, payload, size):
        identifier = node_id(kind, payload, size)
        row = (kind, payload, size)
        previous = self.pending.setdefault(identifier, row)
        require(previous == row, "Canonical fragment identifier collision")
        return identifier, size

    def concat(self, parts):
        require(bool(parts), "Nonempty canonical fragment sequence required")
        while len(parts) > 1:
            groups, group = [], []
            for part in parts:
                group.append(part)
                # Stable child-digest boundaries, with a strict graph fanout.
                if len(group) == FANOUT or (len(group) >= 2 and int(part[0][:2], 16) & 15 == 0):
                    groups.append(group)
                    group = []
            if group:
                groups.append(group)
            parts = [
                chunk[0]
                if len(chunk) == 1
                else self.put(
                    "C", canonical([x[0] for x in chunk]).encode(), sum(x[1] for x in chunk)
                )
                for chunk in groups
            ]
        return parts[0]

    def flush(self):
        self.db.executemany(
            "INSERT OR IGNORE INTO state_nodes VALUES (?,?,?,?)",
            ((identifier, *row) for identifier, row in self.pending.items()),
        )
        identifiers = list(self.pending)
        batch = min(256, self.db.getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER))
        require(batch >= 1, "Available SQLite binding capacity required")
        for start in range(0, len(identifiers), batch):
            block = identifiers[start : start + batch]
            found = set()
            for row in self.db.execute(
                "SELECT id,kind,payload,bytes FROM state_nodes WHERE id IN ("
                + ",".join("?" for _ in block)
                + ")",
                block,
            ):
                identifier, kind, payload, size = tuple(row)
                require(
                    type(kind) is str
                    and type(payload) is bytes
                    and type(size) is int
                    and (kind, payload, size) == self.pending[identifier],
                    "Existing canonical fragment differs",
                )
                found.add(identifier)
            require(found == set(block), "Requested canonical fragment missing after insertion")


def encode(db, value):
    if _fragmenter is None:
        return _structural_encode(db, value)
    raw = canonical(value).encode()
    require(0 < len(raw) <= MAX_BYTES, "Canonical state byte length differs or exceeds bound")
    encoder, start, parts = BufferedEncoder(db), 0, []
    for end in _fragmenter.boundaries(raw):
        require(
            type(end) is int and start < end <= len(raw) and end - start <= CHUNK,
            "Strict bounded byte offsets required",
        )
        parts.append(encoder.put("L", raw[start:end], end - start))
        start = end
    require(start == len(raw), "Exact complete canonical byte coverage required")
    root, size = encoder.concat(parts)
    require(size == len(raw), "Canonical state byte length differs")
    encoder.flush()
    return root, size


def verify_nodes(db, roots, *, contents=None):
    """Fresh every stored byte, then exact complete root/child membership.

    Returned values are integrity descriptors only. No node payload, source
    document, current state or examination result survives this invocation.
    """
    require(
        type(roots) in (list, tuple, set) and roots and all(valid_id(x) for x in roots),
        "Exact complete canonical root inventory required",
    )
    require(
        contents is None or (type(contents) is dict and not contents),
        "Empty invocation-local fragment byte map required",
    )
    proof = {}
    for row in db.execute("SELECT id,kind,payload,bytes FROM state_nodes"):
        identifier, kind, raw, size = tuple(row)
        require(
            valid_id(identifier)
            and kind in {"L", "C"}
            and type(raw) is bytes
            and type(size) is int
            and 0 < size <= MAX_BYTES,
            "Strict canonical fragment fields required",
        )
        require(identifier == node_id(kind, raw, size), "Canonical fragment byte hash differs")
        if kind == "L":
            require(size == len(raw) <= CHUNK, "Exact bounded literal fragment required")
            children = ()
        else:
            children = _children(raw)
        proof[identifier] = {"kind": kind, "bytes": size, "children": children}
        if contents is not None:
            contents[identifier] = (kind, raw, size)
    for item in proof.values():
        if item["children"]:
            require(all(x in proof for x in item["children"]), "Canonical fragment child missing")
            require(
                sum(proof[x]["bytes"] for x in item["children"]) == item["bytes"],
                "Canonical concatenation byte count differs",
            )
    seen, active, heights = set(), set(), {}
    for root in roots:
        stack = [(root, False)]
        while stack:
            identifier, closing = stack.pop()
            require(identifier in proof, "Canonical state root missing")
            children = proof[identifier]["children"]
            if closing:
                height = 1 + max((heights[x] for x in children), default=0)
                require(height <= MAX_GRAPH_DEPTH, "Canonical fragment depth exceeds bound")
                heights[identifier] = height
                active.remove(identifier)
                seen.add(identifier)
            elif identifier not in seen:
                require(identifier not in active, "Canonical fragment cycle refused")
                require(len(active) < MAX_GRAPH_DEPTH, "Canonical fragment depth exceeds bound")
                active.add(identifier)
                stack.append((identifier, True))
                stack.extend((child, False) for child in reversed(children))
    require(seen == set(proof), "Unregistered canonical fragment outside complete journal roots")
    return proof


def chunks(db, root, *, proof=None, contents=None, invocation=None):
    """Bounded fragment stream; exact ordering never comes from SQL inference."""
    require(valid_id(root), "Exact canonical root locator required")
    if invocation is not None:
        require(
            type(invocation) is VerifiedInvocationGraph, "Exact fresh invocation graph required"
        )
        yield from invocation.chunks(db, root)
        return
    active, total, stack = set(), 0, [(root, None, None)]
    while stack:
        identifier, start, closing_size = stack.pop()
        if start is not None:
            require(total - start == closing_size, "Reconstructed canonical byte count differs")
            active.remove(identifier)
            continue
        require(identifier not in active, "Canonical fragment cycle refused")
        require(len(active) < MAX_GRAPH_DEPTH, "Canonical fragment depth exceeds bound")
        row = None if contents is None else contents.get(identifier)
        if row is None:
            row = db.execute(
                "SELECT kind,payload,bytes FROM state_nodes WHERE id=?", (identifier,)
            ).fetchone()
        require(row is not None, "Canonical fragment unavailable")
        kind, raw, size = tuple(row)
        require(
            kind in {"L", "C"}
            and type(raw) is bytes
            and type(size) is int
            and 0 < size <= MAX_BYTES
            and node_id(kind, raw, size) == identifier,
            "Canonical fragment integrity differs",
        )
        if kind == "L":
            require(size == len(raw) <= CHUNK, "Exact bounded literal fragment required")
            children = ()
        elif proof is not None and identifier in proof:
            # This exact node hash was checked above; its ordered descriptor
            # comes from the complete byte-verified graph in this invocation.
            children = proof[identifier]["children"]
        else:
            children = _children(raw)
        if proof is not None:
            require(
                proof.get(identifier) == {"kind": kind, "bytes": size, "children": children},
                "Verified canonical fragment descriptor changed",
            )
        if kind == "L":
            total += size
            yield raw
        else:
            active.add(identifier)
            stack.append((identifier, total, size))
            stack.extend((child, None, None) for child in reversed(children))


def decode(db, root, *, proof=None, contents=None, invocation=None):
    result = bytearray()
    for raw in chunks(db, root, proof=proof, contents=contents, invocation=invocation):
        require(len(result) + len(raw) <= MAX_BYTES, "Reconstructed state exceeds explicit bound")
        result.extend(raw)
    return bytes(result)
