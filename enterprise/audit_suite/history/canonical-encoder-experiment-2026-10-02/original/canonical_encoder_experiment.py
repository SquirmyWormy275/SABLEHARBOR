"""Unadopted encoder experiment; exact canonical node format is unchanged."""

import sqlite3

from . import _canonical_fragmenter_native as splitter
from .canonical_state_codec import CHUNK, FANOUT, MAX_BYTES, node_id, require
from .store import canonical


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
                else self.put("C", canonical([x[0] for x in chunk]).encode(), sum(x[1] for x in chunk))
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
                    type(kind) is str and type(payload) is bytes and type(size) is int
                    and (kind, payload, size) == self.pending[identifier],
                    "Existing canonical fragment differs",
                )
                found.add(identifier)
            require(found == set(block), "Requested canonical fragment missing after insertion")


def encode(db, value):
    raw = canonical(value).encode()
    require(0 < len(raw) <= MAX_BYTES, "Canonical state byte length differs or exceeds bound")
    encoder, start, parts = BufferedEncoder(db), 0, []
    for end in splitter.boundaries(raw):
        require(type(end) is int and start < end <= len(raw) and end - start <= CHUNK,
                "Strict bounded byte offsets required")
        parts.append(encoder.put("L", raw[start:end], end-start))
        start = end
    require(start == len(raw), "Exact complete canonical byte coverage required")
    root, size = encoder.concat(parts)
    require(size == len(raw), "Canonical state byte length differs")
    encoder.flush()
    return root, size
