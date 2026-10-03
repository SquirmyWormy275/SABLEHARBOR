"""Private typed/native closure for the opt-in sealed journal composition.

The immutable original is fully reverified on every new application lifetime.
Only integrity descriptors survive that scan. Every subsequent invocation
freshly checks all historical native originals and receipts, the immutable
prefix identities, and every mutable tail row under a reserved transaction.
"""

import json
import math
import time

from .company_store import _time
from .fresh_sec003_procedure import require
from .history_inspection import _stamp, scan_validated_history
from .persistent_company_journey import native_rows
from .sealed_history_inspection import publish_prefix, scan_composed
from .source_library_audit import EMPTY_WORKROOM, file_sha, private_file, quiescent_read
from .store import digest

PROJECTION = (
    "id",
    "mode",
    "simulated_at",
    "company_source_binding",
    "artifacts",
    "scope",
    "revision",
)


def _sources(room):
    from .persistent_company_service import time_to_iso

    room.world.verify()
    native = native_rows(room.world.database)
    now = _time(time_to_iso())
    require(
        _time(room.world.initialization["initialized_at"]) <= now
        and all(_time(r["imported_at"]) <= now for r in native.values()),
        "Company real import clock is in the future",
    )
    with quiescent_read(room.world.database) as db:
        journal = {
            r["command_id"]: json.loads(r["receipt"])
            for r in db.execute("SELECT command_id,receipt FROM collections")
        }
    return native, journal


def _validator(room, native, journal, files, custody, *, terminal=None):
    previous_clock = None if terminal is None else _time(terminal["simulated_at"])
    previous_real = 0 if terminal is None else terminal["recorded_at"]
    verified = set()

    def validate(event, state, prior_header=None):
        nonlocal previous_clock, previous_real
        if prior_header is not None:
            require(
                prior_header["scope_sha256"] == digest(room.binding["scope"])
                and prior_header["company_binding_sha256"] in {digest(None), digest(room.selected)},
                "Previously verified exact scope/source descriptor differs",
            )
            state = {k: prior_header[k] for k in ("id", "mode", "simulated_at", "revision")} | {
                "scope": room.binding["scope"],
                "artifacts": [],
                "company_source_binding": (
                    None
                    if prior_header["company_binding_sha256"] == digest(None)
                    else room.selected
                ),
            }
        real = event["recorded_at"]
        clock = _time(state["simulated_at"])
        require(
            type(real) in (int, float)
            and math.isfinite(real)
            and previous_real <= real <= time.time()
            and (previous_clock is None or previous_clock <= clock),
            "Workroom actual/simulated clock chronology changed",
        )
        require(
            type(state.get("revision")) is int
            and state["revision"] == event["revision"]
            and state["id"] == room.engagement
            and state["mode"] == room.binding["mode"]
            and type(state.get("scope")) is dict
            and digest(state["scope"]) == digest(room.binding["scope"]),
            "Historical retained identity/revision/mode/scope differs",
        )
        binding = state.get("company_source_binding")
        require(
            binding is None or (type(binding) is dict and digest(binding) == digest(room.selected)),
            "Historical exact native company binding differs",
        )
        if terminal is not None:
            require(binding is not None, "Activated retained tail lost its company binding")
        room.verify_artifacts(
            state, native, verified=verified, journal=journal, files=files, custody=custody
        )
        previous_clock, previous_real = clock, real

    return validate


def _birth(room, initial, db):
    identities = room._verify_memberships(db)
    require(
        initial["created_by"] == identities["operator"]
        and digest(initial["scope"]) == digest(room.binding["scope"])
        and initial["mode"] == room.binding["mode"]
        and _time(initial["simulated_at"]) == _time(room.binding["initial_simulated_at"])
        and type(room.binding["task_count"]) is int
        and room.binding["task_count"] == len(initial["tasks"]) > 0
        and room.binding["zero_workroom_counts"] == {k: 0 for k in EMPTY_WORKROOM}
        and all(type(room.binding["zero_workroom_counts"][k]) is int for k in EMPTY_WORKROOM)
        and all(type(initial[k]) is list and not initial[k] for k in EMPTY_WORKROOM)
        and all(
            t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN" for t in initial["tasks"]
        ),
        "Original fresh-workroom birth binding differs",
    )


def _current(room, state):
    require(
        state.get("company_source_binding") == room.selected
        and state.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION"
        and state["phase"] in {"READY", "ACTIVE", "CLOSED"},
        "Retained workroom must have its activated exact source binding",
    )


def _close_sources(room, files):
    from .persistent_company_service import same_file_identity

    room.world.verify()
    for path, (identity, sha, size) in files.items():
        private_file(path)
        require(
            same_file_identity(path.stat(), identity)
            and path.stat().st_size == size
            and file_sha(path) == sha,
            "Historical retained original changed during validation",
        )


def _descriptors(files, custody):
    return {
        "files": {
            str(p): {"sha256": sha, "bytes": size} for p, (_identity, sha, size) in files.items()
        },
        "custody": custody,
    }


def verify_sealed(room):
    """Complete cold original replay before any interactive memo is published."""
    store = room.sealed_store
    prefix_stamp, outside = store.check_prefix(), _stamp(store.db_path)
    # Reserve the ordinary tail writer throughout prefix/source/birth closure.
    # The immutable original is never initialized, chmodded or modified.
    with store.connect() as tail:
        tail.execute("BEGIN IMMEDIATE")
        tail.execute("PRAGMA query_only=ON")
        inside = _stamp(store.db_path)
        store.verify_projection(tail)
        with room.world.locked():
            native, journal = _sources(room)
            files, custody = {}, {}
            with store.prefix_connection() as prefix:
                prefix.execute("BEGIN")
                require(
                    prefix.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                    "Original prefix SQLite integrity failed",
                )
                result, candidate, _identity = scan_validated_history(
                    prefix,
                    store.prefix_path,
                    room.engagement,
                    revisions=[0],
                    row_validator=_validator(room, native, journal, files, custody),
                    projection_fields=PROJECTION,
                )
                _birth(room, result["selected"][0]["state"], prefix)
                _current(room, result["latest"]["state"])
            _close_sources(room, files)
        # Candidate is not exposed to other calls before all source, authority,
        # config/code and both outside/inside file closure checks succeed.
        room.check_pins()
        require(
            store.check_prefix() == prefix_stamp and _stamp(store.db_path) == inside,
            "Sealed bootstrap changed during complete validation",
        )
    require(_stamp(store.db_path) == outside, "Tail changed during bootstrap closure")
    room._pending_prefix = candidate, prefix_stamp
    room._pending_prefix_custody = _descriptors(files, custody)


def finish_startup(room):
    store = room.sealed_store
    candidate, stamp = room._pending_prefix
    publish_prefix(store, candidate, stamp)
    room._prefix_custody = room._pending_prefix_custody
    room._tail_integrity = None
    store._typed_composed_reader = lambda actor, revisions: read_sealed(room, actor, revisions)
    try:
        read_sealed(room, room.binding["identities"]["operator"], ())
    except BaseException:
        store._prefix_integrity = None
        raise
    del room._pending_prefix
    del room._pending_prefix_custody


def read_sealed(room, actor, revisions):
    """Fresh original custody and complete small-tail replay per invocation."""
    with room._integrity_lock:
        room.check_pins()
        store = room.sealed_store
        prefix_stamp, outside = store.check_prefix(), _stamp(store.db_path)
        previous = room._tail_integrity
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("PRAGMA query_only=ON")
            inside = _stamp(store.db_path)
            store._authorize(db, actor, room.engagement)
            store.verify_projection(db)
            # Birth checks the original prefix memberships. Current authority
            # comes from exact signed transitions, already freshly validated
            # by verify_projection/_authorize. A legitimate instructor downgrade
            # denies private Key access without blocking the learner's history.
            with room.world.locked():
                native, journal = _sources(room)
                base = room._prefix_custody
                files = room._verify_integrity_descriptors(base, native, journal)
                custody = dict(base["custody"])
                if previous is not None:
                    files.update(room._verify_integrity_descriptors(previous, native, journal))
                    custody.update(previous["custody"])
                terminal = store._prefix_integrity["last_meta"] | {
                    "simulated_at": store._prefix_integrity["state_integrity"][
                        max(
                            store._prefix_integrity["state_integrity"],
                            key=lambda key: store._prefix_integrity["state_integrity"][key][
                                "header"
                            ]["revision"],
                        )
                    ]["header"]["simulated_at"]
                }
                history, candidate, _identity = scan_composed(
                    store,
                    db,
                    revisions=revisions,
                    row_validator=_validator(
                        room, native, journal, files, custody, terminal=terminal
                    ),
                    previous_integrity=None if previous is None else previous["history"],
                )
                _current(room, history["latest"]["state"])
                _close_sources(room, files)
            store._authorize(db, actor, room.engagement)
            room.check_pins()
            require(
                store.check_prefix() == prefix_stamp and _stamp(store.db_path) == inside,
                "Journal changed during complete native-tail validation",
            )
        require(_stamp(store.db_path) == outside, "Tail changed during protected closure")
        room.check_pins()
        require(store.check_prefix() == prefix_stamp, "Original prefix changed before publication")
        room._tail_integrity = {
            "history": candidate,
            "stamp": outside,
            **_descriptors(files, custody),
        }
        store._retained_typed_stamp = (prefix_stamp, outside)
        return history
