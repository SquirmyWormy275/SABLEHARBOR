"""Complete history verification with bounded, freshly read selected states."""

import hashlib
import json
import os
import sqlite3
import stat
import threading
import weakref
from pathlib import Path

from .history_locators import UnsupportedLayout, locate_command, prepare_locations, read_ranges
from .serialized_json import canonical_bytes, canonical_projection, update_object
from .store import DomainError, canonical

_update_object = update_object
_MEMOS = weakref.WeakKeyDictionary()
_MEMO_LOCK = threading.RLock()
_META = ("revision", "actor", "recorded_at", "command_id", "hash", "previous_hash", "request_hash")


def _integrity(message="History integrity failure"):
    return DomainError(message, code="INTEGRITY", status=500)


def _stamp(path):
    """Fresh physical identity; restoring mtime does not restore ctime_ns."""
    path = Path(path)
    if path != path.resolve() or any(p.is_symlink() for p in [path, *path.parents]):
        raise _integrity("Unaliased ordinary journal path required")
    values = []
    for suffix in ("", "-wal", "-shm", "-journal"):
        member = Path(str(path) + suffix)
        try:
            info = member.lstat()
        except FileNotFoundError:
            if not suffix:
                raise _integrity("History database unavailable") from None
            values.append(None)
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise _integrity("Ordinary unlinked journal members required")
        values.append(
            (
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_size,
                info.st_nlink,
                info.st_mtime_ns,
                info.st_ctime_ns,
            )
        )
    parents = tuple((p.stat().st_dev, p.stat().st_ino, p.stat().st_mode) for p in path.parents)
    return tuple(values), parents


def _meta(row):
    return hashlib.sha256(canonical({name: row[name] for name in _META}).encode()).digest()


def _activity(row, command, raw):
    return {
        name: row[name] for name in ("actor", "recorded_at", "command_id", "hash", "revision")
    } | {
        "command": command
        if command.get("kind") == "artifact.inspection.record" and len(raw) <= 32768
        else {"kind": command.get("kind")}
    }


def _fields(row, state_bytes, command_bytes):
    return {
        name: canonical(row[name]).encode()
        for name in ("actor", "recorded_at", "previous_hash", "command_id")
    } | {"state": state_bytes, "command": command_bytes}


def _verify_row(row, fields, count, previous):
    hasher = hashlib.sha256()
    update_object(hasher, fields)
    if (
        row["revision"] != count
        or row["previous_hash"] != previous
        or hasher.hexdigest() != row["hash"]
        or hashlib.sha256(fields["command"]).hexdigest() != row["request_hash"]
    ):
        raise _integrity()


def _entry(row, state, command):
    return {
        name: row[name]
        for name in ("actor", "recorded_at", "previous_hash", "command_id", "hash", "revision")
    } | {"state": state, "command": command}


def _scan(
    db,
    engagement,
    current,
    wanted,
    fd,
    *,
    row_validator=None,
    previous_integrity=None,
    projection_fields=None,
    event_table="events",
    first_revision=0,
    previous_hash="",
    rolling_seed=None,
    prefix_digests=(),
    initial_latest=None,
    initial_latest_canonical=None,
):
    if (
        event_table not in {"events", "event_tail"}
        or type(first_revision) is not int
        or first_revision < 0
    ):
        raise _integrity("Exact internal history table/boundary required")
    if len(prefix_digests) != first_revision or (first_revision and rolling_seed is None):
        raise _integrity("Complete verified prefix digest seed required")
    rolling = hashlib.sha256(b"[") if rolling_seed is None else rolling_seed.copy()
    previous, count = previous_hash, first_revision
    selected, prefixes, all_prefixes, activity, metadata, expected = {}, {}, [], [], {}, {}
    all_prefixes.extend(prefix_digests)
    last = initial_latest
    last_canonical = initial_latest_canonical
    last_raw = None
    last_meta = None
    locations = {}
    state_integrity = {}
    try:
        rowids = {
            row[0]
            for row in db.execute(
                f"SELECT rowid FROM {event_table} WHERE engagement=?", (engagement,)
            )
        }
        prepared = prepare_locations(db, fd, rowids)
    except (UnsupportedLayout, OSError, sqlite3.Error):
        prepared, locations = None, None
    sql = f"SELECT rowid AS locator_rowid,* FROM {event_table} WHERE engagement=? ORDER BY revision"
    if previous_integrity is not None:
        # Freshly stream every historical byte. A known-identical canonical
        # representation needs neither TEXT conversion nor canonical decoding.
        sql = (
            "SELECT rowid AS locator_rowid,engagement,revision,command_id,request_hash,"
            "actor,recorded_at,previous_hash,hash,CAST(state AS BLOB) AS state,"
            f"CAST(command AS BLOB) AS command FROM {event_table} "
            "WHERE engagement=? ORDER BY revision"
        )
    for row in db.execute(sql, (engagement,)):
        rowid = row["locator_rowid"]
        raw_state = row["state"] if type(row["state"]) is bytes else row["state"].encode()
        raw_state_sha = hashlib.sha256(raw_state).hexdigest()
        raw_command = row["command"] if type(row["command"]) is bytes else row["command"].encode()
        command_text = raw_command.decode("utf-8")
        old = (
            None if previous_integrity is None else previous_integrity["state_integrity"].get(rowid)
        )
        reusable = (
            old is not None
            and old["bytes"] == len(raw_state)
            and old["sha256"] == raw_state_sha
            and old["canonical_raw"] is True
            and old["header"] is not None
            and previous_integrity["metadata"].get(rowid) == _meta(row)
        )
        state = None
        selected_state = count in wanted or count == current["revision"]
        if (
            not reusable
            and row_validator is not None
            and projection_fields is not None
            and not selected_state
        ):
            state_bytes, state = canonical_projection(raw_state.decode("utf-8"), projection_fields)
        else:
            state_bytes = raw_state if reusable else canonical_bytes(raw_state.decode("utf-8"))
        command = json.loads(command_text)
        command_bytes = canonical_bytes(command_text)
        fields = _fields(row, state_bytes, command_bytes)
        _verify_row(row, fields, count, previous)
        if selected_state or (row_validator is not None and not reusable and state is None):
            state = json.loads(raw_state)
        if row_validator is not None:
            # Invocation-local validation sees the same exact transactional row
            # whose full event/request hashes were just recomputed. Failure
            # aborts the scan and cannot publish its incomplete integrity memo.
            if reusable and state is None:
                row_validator(row, None, old["header"])
            else:
                row_validator(row, state)
        header = None
        if row_validator is not None:
            if reusable and state is None:
                header = old["header"]
            else:
                # Only typed identity/clock/binding integrity descriptors.
                # No evidence, parsed document or examination result survives.
                header = {name: state[name] for name in ("id", "mode", "simulated_at")} | {
                    "revision": state.get("revision"),
                    "company_binding_sha256": hashlib.sha256(
                        canonical(state.get("company_source_binding")).encode()
                    ).hexdigest(),
                    "scope_sha256": hashlib.sha256(
                        canonical(state.get("scope")).encode()
                    ).hexdigest(),
                }
        state_integrity[rowid] = {
            "bytes": len(raw_state),
            "sha256": raw_state_sha,
            "canonical_raw": raw_state == state_bytes,
            "header": header,
        }
        if count:
            rolling.update(b",")
        update_object(
            rolling,
            fields
            | {"hash": canonical(row["hash"]).encode(), "revision": canonical(count).encode()},
        )
        prefix = rolling.copy()
        prefix.update(b"]")
        all_prefixes.append(prefix.hexdigest())
        if count in wanted or count == current["revision"]:
            entry = _entry(row, state, command)
            if count in wanted:
                selected[count], prefixes[count] = entry, all_prefixes[-1]
            if count == current["revision"]:
                last = entry
                last_canonical = state_bytes
                last_raw = raw_state
        activity.append(_activity(row, command, command_bytes))
        physical = raw_command
        expected[rowid] = (len(physical), hashlib.sha256(physical).hexdigest())
        if prepared is not None:
            try:
                old_ranges = (
                    None
                    if previous_integrity is None or previous_integrity.get("locations") is None
                    else previous_integrity["locations"].get(rowid)
                )
                old_command = (
                    None
                    if previous_integrity is None
                    else previous_integrity["expected"].get(rowid)
                )
                old_bytes = None if old_ranges is None else read_ranges(fd, old_ranges)
                if (
                    reusable
                    and old_command == expected[rowid]
                    and old_bytes is not None
                    and len(old_bytes) == expected[rowid][0]
                    and hashlib.sha256(old_bytes).hexdigest() == expected[rowid][1]
                ):
                    locations[rowid] = old_ranges
                else:
                    locations[rowid] = locate_command(fd, prepared, rowid, expected[rowid])
            except (UnsupportedLayout, OSError):
                prepared, locations = None, None
        metadata[rowid] = _meta(row)
        last_meta = {name: row[name] for name in _META}
        previous = row["hash"]
        count += 1
    if (
        last is None
        or current["revision"] != count - 1
        or (
            current["state"].encode() != last_raw
            and canonical_bytes(current["state"]) != last_canonical
        )
    ):
        raise _integrity("History/current state mismatch")
    unfinished = rolling.copy()
    rolling.update(b"]")
    return {
        "count": count,
        "latest": last,
        "selected": selected,
        "prefix_sha256": prefixes,
        "history_sha256": rolling.hexdigest(),
        "activity": activity,
    }, {
        "count": count,
        "prefixes": tuple(all_prefixes),
        "history_sha256": rolling.hexdigest(),
        "metadata": metadata,
        "expected": expected,
        "locations": locations,
        "current_raw_sha256": hashlib.sha256(current["state"].encode()).hexdigest(),
        "state_integrity": state_integrity,
        "unfinished_history_hash": unfinished,
        "last_meta": last_meta,
    }


def scan_validated_history(
    db,
    path,
    engagement,
    *,
    revisions,
    row_validator,
    previous_integrity=None,
    projection_fields=None,
    suffix=None,
    keep_metadata=False,
):
    """One full fresh cursor; caller owns the consistent read/source transaction.

    This returns an unpublished candidate containing only integrity metadata,
    digests, physical locators and typed identity/clock integrity descriptors.
    It holds no complete state, command, source body or examination result.
    """
    if (
        not isinstance(revisions, (list, tuple, set))
        or len(revisions) > 16
        or any(type(r) is not int or r < 0 for r in revisions)
        or not callable(row_validator)
    ):
        raise DomainError("Bounded revisions and invocation-local row validator required")
    path = Path(path)
    before = _stamp(path)
    current = db.execute(
        "SELECT revision,state FROM engagements WHERE id=?", (engagement,)
    ).fetchone()
    if current is None:
        raise _integrity("Retained current engagement unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        identity = os.fstat(fd)
        if (identity.st_dev, identity.st_ino) != before[0][0][:2]:
            raise _integrity("Journal inode changed during validation")
        result, candidate = _scan(
            db,
            engagement,
            current,
            set(revisions),
            fd,
            row_validator=row_validator,
            previous_integrity=previous_integrity,
            projection_fields=projection_fields,
            **({} if suffix is None else suffix),
        )
        if _stamp(path) != before:
            raise DomainError("Journal changed during retained validation", status=409)
    finally:
        os.close(fd)
    if candidate["locations"] is None and not keep_metadata:
        candidate = None
    return result, candidate, before


def publish_validated_history(store, actor, engagement, candidate, expected_stamp):
    """Publish metadata only to this exact constructed Store after fresh closure.

    The retained loader invokes this only after its complete scope, source,
    membership and code/config checks succeeded. If construction or any journal
    write changed file/sidecar identity, discard the optimization; the next Key
    read performs its ordinary fresh full scan. No content is transplanted.
    """
    if candidate is None or _stamp(store.db_path) != expected_stamp:
        return False
    with store.connect() as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        store._authorize(db, actor, engagement)
        # Authorization's first SELECT establishes SQLite's actual read
        # transaction and ordinary empty-sidecar lifecycle, as inspect_history
        # already does. No external change between these reads is normalized.
        active_stamp = _stamp(store.db_path)
        current = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement,)
        ).fetchone()
        if (
            current is None
            or current["revision"] != candidate["count"] - 1
            or hashlib.sha256(current["state"].encode()).hexdigest()
            != candidate["current_raw_sha256"]
            or _stamp(store.db_path) != active_stamp
        ):
            return False
    if _stamp(store.db_path) != expected_stamp:
        return False
    published = {**candidate, "stamp": expected_stamp}
    with _MEMO_LOCK:
        entries = _MEMOS.setdefault(store, {})
        if len(entries) >= 8 and engagement not in entries:
            entries.clear()
        entries[engagement] = published
    return True


def _memo_read(db, fd, engagement, current, wanted, memo):
    if current["revision"] != memo["count"] - 1:
        raise DomainError("Engagement changed during history inspection", status=409)
    selected, prefixes, activity, last, previous, count = {}, {}, [], None, "", 0
    last_canonical = None
    last_raw = None
    for row in db.execute(
        "SELECT rowid AS locator_rowid,revision,actor,recorded_at,command_id,"
        "hash,previous_hash,request_hash FROM events WHERE engagement=? ORDER BY revision",
        (engagement,),
    ):
        rowid = row["locator_rowid"]
        if (
            row["revision"] != count
            or row["previous_hash"] != previous
            or _meta(row) != memo["metadata"].get(rowid)
        ):
            raise _integrity()
        raw = read_ranges(fd, memo["locations"][rowid])
        length, sha256 = memo["expected"][rowid]
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != sha256:
            raise _integrity("Original journal command bytes differ")
        command_text = raw.decode("utf-8")
        command, command_bytes = json.loads(command_text), canonical_bytes(command_text)
        if hashlib.sha256(command_bytes).hexdigest() != row["request_hash"]:
            raise _integrity()
        if count in wanted or count == current["revision"]:
            state_text = db.execute(
                "SELECT state FROM events WHERE engagement=? AND revision=?", (engagement, count)
            ).fetchone()[0]
            raw_state = state_text.encode()
            descriptor = memo.get("state_integrity", {}).get(rowid)
            known_canonical = (
                descriptor is not None
                and descriptor["canonical_raw"] is True
                and descriptor["bytes"] == len(raw_state)
                and descriptor["sha256"] == hashlib.sha256(raw_state).hexdigest()
            )
            state_canonical = raw_state if known_canonical else canonical_bytes(state_text)
            _verify_row(
                row,
                _fields(
                    row,
                    state_canonical,
                    command_bytes,
                ),
                count,
                previous,
            )
            entry = _entry(row, json.loads(state_text), command)
            if count in wanted:
                selected[count], prefixes[count] = entry, memo["prefixes"][count]
            if count == current["revision"]:
                last = entry
                last_canonical = state_canonical
                last_raw = raw_state
        activity.append(_activity(row, command, command_bytes))
        previous, count = row["hash"], count + 1
    if (
        count != memo["count"]
        or last is None
        or (
            current["state"].encode() != last_raw
            and canonical_bytes(current["state"]) != last_canonical
        )
    ):
        raise _integrity("History/current state mismatch")
    return {
        "count": count,
        "latest": last,
        "selected": selected,
        "prefix_sha256": prefixes,
        "history_sha256": memo["history_sha256"],
        "activity": activity,
    }


def inspect_history(store, actor, engagement_id, *, revisions=()):
    """Verify all history while retaining only explicitly requested states.

    The memo holds only digests and physical byte locators. Every command and
    selected/current state is freshly read from the original file. Use requires
    unchanged device/inode/size/mode/link/mtime/ctime identities for the database
    and WAL/journal/SHM sidecars. Authorization is checked in the consistent read
    transaction and again before return. Unsupported layouts use complete SQL
    verification. No evidence, complete state, command or outcome survives in
    the memo; identity/clock descriptors never replace source examination.
    """
    sealed_reader = getattr(store, "inspect_sealed_history", None)
    if sealed_reader is not None:
        return sealed_reader(actor, engagement_id, revisions=revisions)
    if (
        not isinstance(revisions, (list, tuple, set))
        or len(revisions) > 16
        or any(type(r) is not int or r < 0 for r in revisions)
    ):
        raise DomainError("Bounded nonnegative history revisions required")
    wanted = set(revisions)
    path = Path(store.db_path)
    before = _stamp(path)
    typed_boundary = getattr(store, "_retained_typed_stamp", before)
    if typed_boundary != before:
        raise DomainError("Retained typed history requires fresh validation", status=409)
    with _MEMO_LOCK:
        memo = _MEMOS.get(store, {}).get(engagement_id)
    if memo is not None and memo["stamp"] != before:
        memo = None
    candidate = None
    with store.connect() as db:
        db.execute("BEGIN")
        store._authorize(db, actor, engagement_id)
        active_before = _stamp(path)
        current = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            file_info = os.fstat(fd)
            if (file_info.st_dev, file_info.st_ino) != active_before[0][0][:2]:
                raise _integrity("Journal inode changed during inspection")
            if memo is not None and not any(
                info is not None and info[3] for info in active_before[0][1::2]
            ):
                result = _memo_read(db, fd, engagement_id, current, wanted, memo)
            else:
                result, candidate = _scan(db, engagement_id, current, wanted, fd)
                if candidate["locations"] is None:
                    candidate = None
            if _stamp(path) != active_before:
                raise DomainError("Journal changed during history inspection", status=409)
        finally:
            os.close(fd)
    with store.connect() as db:
        store._authorize(db, actor, engagement_id)
        if (
            db.execute("SELECT revision FROM engagements WHERE id=?", (engagement_id,)).fetchone()[
                "revision"
            ]
            != result["count"] - 1
        ):
            raise DomainError("Engagement changed during history inspection", status=409)
    after = _stamp(path)
    if after != before or getattr(store, "_retained_typed_stamp", before) != typed_boundary:
        raise DomainError("Journal changed during history inspection", status=409)
    if candidate is not None:
        candidate["stamp"] = after
        with _MEMO_LOCK:
            entries = _MEMOS.setdefault(store, {})
            if len(entries) >= 8 and engagement_id not in entries:
                entries.clear()
            entries[engagement_id] = candidate
    return result
