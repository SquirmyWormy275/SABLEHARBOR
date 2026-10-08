"""Optional byte locators for fresh reads of a quiescent SQLite event journal.

SQLite stores the command after its potentially enormous state field. Reading
that last column walks every overflow page. This module indexes physical ranges
only; commands, states, evidence and outcomes are never retained by the index.
Every indexed command must match an independently read SQL command's exact raw
digest during construction. Callers must bind every use to unchanged main-file
and sidecar identities and recheck them before releasing any result.
"""

from __future__ import annotations

import hashlib
import os


class UnsupportedLayout(ValueError):
    pass


def _varint(data, position):
    value = 0
    for index in range(9):
        if position >= len(data):
            raise UnsupportedLayout("Incomplete SQLite varint")
        byte = data[position]
        position += 1
        value = (value << (8 if index == 8 else 7)) | (byte if index == 8 else byte & 127)
        if index == 8 or byte < 128:
            return value, position
    raise UnsupportedLayout("SQLite varint")


def _length(serial):
    if serial in (0, 8, 9):
        return 0
    if 1 <= serial <= 6:
        return (1, 2, 3, 4, 6, 8)[serial - 1]
    if serial == 7:
        return 8
    if serial >= 12:
        return (serial - 12) // 2
    raise UnsupportedLayout("Reserved SQLite serial type")


def read_ranges(fd, ranges):
    parts = []
    for offset, length in ranges:
        raw = os.pread(fd, length, offset)
        if len(raw) != length:
            raise UnsupportedLayout("Incomplete original command range")
        parts.append(raw)
    return b"".join(parts)


def prepare_locations(db, fd, rowids):
    """Return rowid -> physical ranges, or decline the optional optimization.

    Only small internal/leaf table pages are read here. Overflow pointers are
    followed immediately after SQL freshly reads each row, while those original
    pages are hot. No stored schema or original document is executed.
    """
    db_path = db.execute("PRAGMA database_list").fetchone()[2]
    for suffix in ("-wal", "-journal"):
        sidecar = str(db_path) + suffix
        if os.path.exists(sidecar) and os.stat(sidecar).st_size:
            # A normal read transaction can create empty WAL/SHM files. Any
            # actual WAL/journal payload requires ordinary transactional reads.
            raise UnsupportedLayout("Physical locators require a quiescent main file")
    header = os.pread(fd, 100, 0)
    if (
        len(header) != 100
        or header[:16] != b"SQLite format 3\0"
        or header[20] != 0
        or header[56:60] != b"\0\0\0\1"
    ):
        raise UnsupportedLayout("Unsupported SQLite encoding/header")
    size = int.from_bytes(header[16:18], "big")
    if size == 1:
        size = 65536
    if size < 512 or size > 65536 or size & (size - 1):
        raise UnsupportedLayout("Unsupported SQLite page size")
    total = os.fstat(fd).st_size
    if total % size:
        raise UnsupportedLayout("Incomplete SQLite page file")
    columns = db.execute("PRAGMA table_info(events)").fetchall()
    if [row[1] for row in columns] != [
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
    ]:
        raise UnsupportedLayout("Unsupported event column order")
    root = db.execute("SELECT rootpage,type FROM sqlite_master WHERE name='events'").fetchone()
    if root is None or root[1] != "table":
        raise UnsupportedLayout("Ordinary events table required")
    pending, seen, cells = [(root[0], "/")], set(), {}
    while pending:
        number, prefix = pending.pop()
        if number in seen or not 1 <= number <= total // size:
            raise UnsupportedLayout("Invalid or repeated table page")
        seen.add(number)
        page = os.pread(fd, size, (number - 1) * size)
        if len(page) != size:
            raise UnsupportedLayout("Incomplete table page")
        base = 100 if number == 1 else 0
        kind = page[base]
        if kind not in (5, 13):
            raise UnsupportedLayout("Ordinary rowid table required")
        count = int.from_bytes(page[base + 3 : base + 5], "big")
        pointer_start = base + (12 if kind == 5 else 8)
        if pointer_start + count * 2 > size:
            raise UnsupportedLayout("Invalid cell pointer array")
        for index in range(count):
            offset = int.from_bytes(
                page[pointer_start + index * 2 : pointer_start + index * 2 + 2], "big"
            )
            if offset < pointer_start + count * 2 or offset >= size:
                raise UnsupportedLayout("Invalid cell offset")
            if kind == 5:
                if offset + 4 > size:
                    raise UnsupportedLayout("Incomplete internal cell")
                child = int.from_bytes(page[offset : offset + 4], "big")
                pending.append((child, prefix + f"{index:03x}/"))
                continue
            payload, position = _varint(page, offset)
            rowid, position = _varint(page, position)
            if rowid not in rowids:
                continue
            if rowid in cells:
                raise UnsupportedLayout("Repeated selected rowid")
            maximum, minimum = size - 35, ((size - 12) * 32 // 255) - 23
            local = payload if payload <= maximum else minimum + (payload - minimum) % (size - 4)
            if local > maximum:
                local = minimum
            if position + local + (4 if payload > local else 0) > size:
                raise UnsupportedLayout("Incomplete local payload")
            record = page[position : position + local]
            header_bytes, cursor = _varint(record, 0)
            if header_bytes > len(record):
                raise UnsupportedLayout("Record header exceeds local payload")
            types = []
            while cursor < header_bytes:
                serial, cursor = _varint(record, cursor)
                types.append(serial)
            if cursor != header_bytes or len(types) != 10 or types[-1] < 13 or types[-1] % 2 != 1:
                raise UnsupportedLayout("Unsupported command record type")
            start = header_bytes + sum(_length(serial) for serial in types[:-1])
            length = _length(types[-1])
            if start + length != payload:
                raise UnsupportedLayout("Command field boundary differs")
            ranges = []
            if start < local:
                amount = min(length, local - start)
                ranges.append(((number - 1) * size + position + start, amount))
            remaining_start = max(start, local) - local
            remaining_end = payload - local
            cells[rowid] = {
                "first": int.from_bytes(page[position + local : position + local + 4], "big")
                if payload > local
                else 0,
                "length": length,
                "start": remaining_start,
                "end": remaining_end,
                "ranges": ranges,
            }
        if kind == 5:
            child = int.from_bytes(page[base + 8 : base + 12], "big")
            pending.append((child, prefix + f"{count:03x}/"))
    if set(cells) != set(rowids):
        raise UnsupportedLayout("Selected command rowid membership differs")
    return {"page_size": size, "page_count": total // size, "cells": cells}


def locate_command(fd, prepared, rowid, expected):
    """Derive only ranges; verify fresh original bytes against the SQL row."""
    size, limit = prepared["page_size"], prepared["page_count"]
    cell = prepared["cells"][rowid]
    length, sha256 = expected
    if cell["length"] != length:
        raise UnsupportedLayout("Original command length differs from SQL")
    ranges = list(cell["ranges"])
    number, index, seen = cell["first"], 0, set()
    while index * (size - 4) < cell["end"]:
        if number in seen or not 1 <= number <= limit:
            raise UnsupportedLayout("Invalid or repeated overflow page")
        seen.add(number)
        offset = (number - 1) * size
        pointer = os.pread(fd, 4, offset)
        if len(pointer) != 4:
            raise UnsupportedLayout("Incomplete original overflow pointer")
        begin = max(cell["start"], index * (size - 4))
        end = min(cell["end"], (index + 1) * (size - 4))
        if end > begin:
            ranges.append((offset + 4 + begin - index * (size - 4), end - begin))
        number = int.from_bytes(pointer, "big")
        index += 1
    if number != 0:
        raise UnsupportedLayout("Unexpected final overflow pointer")
    ranges = tuple(ranges)
    raw = read_ranges(fd, ranges)
    if len(raw) != length or hashlib.sha256(raw).hexdigest() != sha256:
        raise UnsupportedLayout("Original command byte locator differs from SQL")
    return ranges
