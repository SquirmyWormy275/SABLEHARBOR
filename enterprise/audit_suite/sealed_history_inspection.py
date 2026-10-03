"""Fresh composed history over a previously fully validated immutable prefix."""

import os

from .history_inspection import _memo_read, _stamp, scan_validated_history
from .sealed_history_store import _require
from .serialized_json import canonical_bytes


def publish_prefix(store, candidate, expected_stamp):
    """Only a complete typed-native validation may publish this integrity seed."""
    _require(
        candidate is not None
        and candidate["count"] == store.prefix["revision"] + 1
        and candidate["last_meta"]["hash"] == store.prefix["last_hash"]
        and candidate["current_raw_sha256"] == store.prefix["current_state_sha256"]
        and store.check_prefix() == expected_stamp,
        "Complete exact-prefix validation is required before memo publication",
    )
    # Digests, typed identity/clock descriptors, byte locators and hash state
    # only: never source bodies, event states, commands or examination outcomes.
    store._prefix_integrity = candidate


def prefix_read(store, wanted):
    store.check_prefix()
    proof = store._prefix_integrity
    _require(
        proof is not None and proof["locations"] is not None,
        "Validated ordinary command locators required for interactive sealed history",
    )
    with store.prefix_connection() as db:
        current = db.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (store.prefix["engagement"],)
        ).fetchone()
        fd = os.open(store.prefix_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            _require(
                (info.st_dev, info.st_ino) == store._prefix_stamp[0][0][:2],
                "Sealed prefix inode changed during selected read",
            )
            result = _memo_read(db, fd, store.prefix["engagement"], current, wanted, proof)
            result["_latest_canonical_bytes"] = canonical_bytes(current["state"])
        finally:
            os.close(fd)
    store.check_prefix()
    return result


def scan_composed(store, db, *, revisions, row_validator, previous_integrity=None):
    """Caller holds one tail read/source transaction and fresh authorization."""
    _require(
        isinstance(revisions, (list, tuple, set))
        and len(revisions) <= 16
        and all(type(r) is int and r >= 0 for r in revisions),
        "Bounded nonnegative composed-history revisions required",
    )
    wanted = set(revisions)
    prefix = prefix_read(store, {r for r in wanted if r <= store.prefix["revision"]})
    seed = store._prefix_integrity
    if store.state_codec is not None:
        from .codec_history_inspection import scan_codec

        identity = _stamp(store.db_path)
        tail, candidate = scan_codec(
            store,
            db,
            wanted=wanted,
            row_validator=row_validator,
            previous_integrity=previous_integrity,
            prefix=prefix,
        )
        _require(_stamp(store.db_path) == identity, "Tail changed during codec validation")
    else:
        tail, candidate, identity = scan_validated_history(
            db,
            store.db_path,
            store.prefix["engagement"],
            revisions=[r for r in wanted if r > store.prefix["revision"]],
            row_validator=row_validator,
            previous_integrity=previous_integrity,
            projection_fields=(
                "id",
                "mode",
                "simulated_at",
                "company_source_binding",
                "artifacts",
                "scope",
                "revision",
            ),
            suffix={
                "event_table": "event_tail",
                "first_revision": seed["count"],
                "previous_hash": store.prefix["last_hash"],
                "rolling_seed": seed["unfinished_history_hash"],
                "prefix_digests": seed["prefixes"],
                "initial_latest": prefix["latest"],
                "initial_latest_canonical": prefix["_latest_canonical_bytes"],
            },
            keep_metadata=True,
        )
    current = tail["latest"]["state"]
    if candidate["count"] == seed["count"]:
        # A copied current header is still freshly checked. It cannot acquire
        # native receipt/scope authority from Python bool/int dictionary equality.
        row_validator(seed["last_meta"], current)
    store.check_prefix()
    return (
        tail
        | {
            "selected": prefix["selected"] | tail["selected"],
            "prefix_sha256": prefix["prefix_sha256"] | tail["prefix_sha256"],
            "activity": prefix["activity"] + tail["activity"],
        },
        candidate,
        identity,
    )


def inspect_composed(store, actor, engagement, *, revisions=()):
    """Selected public history remains original bytes; no new fact cache."""
    _require(engagement == store.prefix["engagement"], "Exact retained engagement required")
    reader = getattr(store, "_typed_composed_reader", None)
    _require(callable(reader), "Fresh complete native-tail validation required")
    result = reader(actor, revisions)
    store.check_prefix()
    _require(
        _stamp(store.db_path) == store._retained_typed_stamp[1],
        "Tail changed after fresh typed history validation",
    )
    return result
