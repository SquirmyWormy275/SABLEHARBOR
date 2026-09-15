"""Bounded-state history inspection preserving the public history list digest."""

import hashlib
import json

from .store import DomainError, canonical, digest


def inspect_history(store, actor, engagement_id, *, revisions=()):
    """Verify all events, retaining only requested states and compact activity metadata.

    Prefix digests are byte-identical to digest(Store.history(... )[:revision+1]).
    Command hashes cover the retained command envelope, not unavailable external inputs.
    """
    if (
        not isinstance(revisions, (list, tuple, set))
        or len(revisions) > 16
        or any(type(r) is not int or r < 0 for r in revisions)
    ):
        raise DomainError("Bounded nonnegative history revisions required")
    wanted = set(revisions)
    selected, prefixes, activity = {}, {}, []
    rolling = hashlib.sha256(b"[")
    previous, last, count = "", None, 0
    with store.connect() as db:
        db.execute("BEGIN")
        store._authorize(db, actor, engagement_id)
        current = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        for row in db.execute(
            "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement_id,)
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
            entry = {**record, "hash": row["hash"], "revision": count}
            if count:
                rolling.update(b",")
            rolling.update(canonical(entry).encode())
            if count in wanted:
                selected[count] = entry
                prefix = rolling.copy()
                prefix.update(b"]")
                prefixes[count] = prefix.hexdigest()
            activity.append(
                {
                    "actor": row["actor"],
                    "recorded_at": row["recorded_at"],
                    "command_id": row["command_id"],
                    "command": {"kind": record["command"].get("kind")},
                    "hash": row["hash"],
                    "revision": count,
                }
            )
            previous, last = row["hash"], entry
            count += 1
        if (
            last is None
            or current["revision"] != count - 1
            or json.loads(current["state"]) != last["state"]
        ):
            raise DomainError("History/current state mismatch", code="INTEGRITY", status=500)
    # A new connection observes current permission after the consistent read transaction.
    with store.connect() as db:
        store._authorize(db, actor, engagement_id)
        revision = db.execute(
            "SELECT revision FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()["revision"]
        if revision != count - 1:
            raise DomainError("Engagement changed during history inspection", status=409)
    rolling.update(b"]")
    return {
        "count": count,
        "latest": last,
        "selected": selected,
        "prefix_sha256": prefixes,
        "history_sha256": rolling.hexdigest(),
        "activity": activity,
    }
