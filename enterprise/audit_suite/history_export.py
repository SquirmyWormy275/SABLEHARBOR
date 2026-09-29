"""Verified bounded full-history JSON without materializing every historical state."""

import io
import json
from contextlib import closing

from .store import DomainError, canonical, digest

MAX_EVENT_BYTES = 100 * 1024 * 1024


def history_json(store, actor, engagement_id, *, revision, max_bytes, project=None):
    """Retain the complete selected prefix, or reject it; never silently truncate."""
    if type(revision) is not int or revision < 0 or type(max_bytes) is not int or max_bytes < 2:
        raise DomainError(
            "History export exceeds the available archive limit", code="EXPORT_LIMIT", status=413
        )
    stream = io.BytesIO()
    stream.write(b"[")
    with closing(store.connect()) as db, db:
        db.execute("BEGIN")
        store._authorize(db, actor, engagement_id)
        oversized = db.execute(
            "SELECT 1 FROM events WHERE engagement=? AND revision<=? "
            "AND length(CAST(state AS BLOB)) + length(CAST(command AS BLOB)) > ? LIMIT 1",
            (engagement_id, revision, MAX_EVENT_BYTES),
        ).fetchone()
        if oversized is not None:
            raise DomainError(
                "An audit history event exceeds the export processing limit; "
                "no partial export was retained",
                code="EXPORT_LIMIT",
                status=413,
            )
        previous, count = "", 0
        for row in db.execute(
            "SELECT * FROM events WHERE engagement=? AND revision<=? ORDER BY revision",
            (engagement_id, revision),
        ):
            record = {
                "actor": row["actor"],
                "recorded_at": row["recorded_at"],
                "previous_hash": row["previous_hash"],
                "state": json.loads(row["state"]),
                "command": json.loads(row["command"]),
                "command_id": row["command_id"],
            }
            if (
                row["revision"] != count
                or previous != row["previous_hash"]
                or digest(record) != row["hash"]
                or digest(record["command"]) != row["request_hash"]
            ):
                raise DomainError("History integrity failure", code="INTEGRITY", status=500)
            previous = row["hash"]
            entry = {**record, "hash": previous, "revision": count}
            if project is not None:
                entry = project(entry)
            encoded = canonical(entry).encode()
            if stream.tell() + len(encoded) + (1 if count else 0) + 1 > max_bytes:
                raise DomainError(
                    "Complete audit history exceeds the available archive limit; "
                    "no partial export was retained",
                    code="EXPORT_LIMIT",
                    status=413,
                )
            if count:
                stream.write(b",")
            stream.write(encoded)
            count += 1
        if count != revision + 1:
            raise DomainError("History prefix is incomplete", code="INTEGRITY", status=500)
    # Do not return bytes under a membership revoked during the streamed read.
    store.membership(actor, engagement_id)
    stream.write(b"]")
    return stream.getvalue()
