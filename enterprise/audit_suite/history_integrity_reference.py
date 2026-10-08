"""Private integrity references, never evidence/answer or global-array SHA caches.

Only a Root-selected immutable base and genuine managed Store transitions may
provide these references. An object received from HTTP cannot certify history.
The public full-history inspection and export algorithms remain separate.
"""

import math
import re

from .store import DomainError, canonical

MAX_SAFE_INTEGER = 2**53 - 1
REFERENCE_SCHEMA = "SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1"
REFERENCE_ALGORITHM = "SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1"
REFERENCE_FIELDS = frozenset({
    "schema", "kind", "algorithm", "engagement_id", "revision",
    "selected_event_sha256", "selected_request_sha256", "state_storage",
    "selected_state_root_sha256", "selected_state_sha256", "selected_state_bytes",
    "accepted_base_sha256", "checkpoint_sha256",
})
FRAME_FIELDS = frozenset({
    "engagement_id", "revision", "command_id", "request_sha256", "event_sha256",
    "previous_event_sha256", "actor", "recorded_at", "command_kind",
    "state_storage", "state_root_sha256", "state_sha256", "state_bytes",
})


def require(value, message):
    if value is not True:
        raise DomainError(message, code="INTEGRITY", status=503)


def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "Exact SHA256 required")
    return value


def integer(value, *, positive=False):
    require(type(value) is int and (1 if positive else 0) <= value <= MAX_SAFE_INTEGER,
            "Exact safe integer required")
    return value


def identity(value):
    require(type(value) is str and 1 <= len(value) <= 256, "Exact bounded identity required")
    return value


def validate_reference(value, *, engagement=None, revision=None, state_sha256=None,
                       event_sha256=None, accepted_base_sha256=None,
                       checkpoint_sha256=None):
    require(type(value) is dict and set(value) == REFERENCE_FIELDS,
            "Exact selected integrity-reference fields required")
    require(type(value["schema"]) is str and type(value["algorithm"]) is str
            and type(value["kind"]) is str and type(value["state_storage"]) is str
            and value["schema"] == REFERENCE_SCHEMA
            and value["algorithm"] == REFERENCE_ALGORITHM
            and value["kind"] in {"ROOT_ACCEPTED_BASE", "MANAGED_STORE_CHECKPOINT"},
            "Selected integrity-reference kind/algorithm differs")
    identity(value["engagement_id"])
    integer(value["revision"])
    integer(value["selected_state_bytes"], positive=True)
    for key in ("selected_event_sha256", "selected_request_sha256", "selected_state_sha256",
                "accepted_base_sha256", "checkpoint_sha256"):
        sha(value[key])
    if value["state_storage"] == "CANONICAL_CODEC_GRAPH":
        sha(value["selected_state_root_sha256"])
    else:
        require(value["state_storage"] == "RAW_CANONICAL_JSON"
                and value["selected_state_root_sha256"] is None,
                "Exact raw-state or graph-root rule required")
    if value["kind"] == "ROOT_ACCEPTED_BASE":
        require(value["checkpoint_sha256"] == value["accepted_base_sha256"],
                "Root base reference must identify that exact accepted base")
    joins = {"engagement_id": engagement, "revision": revision,
             "selected_state_sha256": state_sha256, "selected_event_sha256": event_sha256,
             "accepted_base_sha256": accepted_base_sha256,
             "checkpoint_sha256": checkpoint_sha256}
    for key, expected in joins.items():
        if expected is not None:
            require(canonical(value[key]) == canonical(expected),
                    "Selected integrity-reference " + key + " differs")
    return value


def same_reference(left, right):
    validate_reference(left)
    validate_reference(right)
    return canonical(left) == canonical(right)


def validate_store_reference(store, value):
    """Authenticate a stored V2 reference against this genuine current ledger."""
    validate_reference(value)
    runtime = getattr(store, "_managed_history_integrity", None)
    require(runtime is not None, "Selected managed integrity runtime required for V2 record")
    runtime.validate_reference(value)
    return value


def validate_frame(row, *, engagement, revision, previous_event_sha256):
    require(type(row) is dict and set(row) == FRAME_FIELDS, "Exact integrity frame fields required")
    require(row["engagement_id"] == engagement and type(row["revision"]) is int
            and row["revision"] == revision, "Integrity frame identity/revision differs")
    integer(row["revision"])
    identity(row["command_id"])
    identity(row["actor"])
    identity(row["command_kind"])
    require(type(row["recorded_at"]) in (int, float)
            and 0 <= row["recorded_at"] <= MAX_SAFE_INTEGER
            and (type(row["recorded_at"]) is int or math.isfinite(row["recorded_at"])),
            "Actual finite frame timestamp required")
    require(row["previous_event_sha256"] == previous_event_sha256,
            "Integrity frame chain predecessor differs")
    sha(row["event_sha256"])
    sha(row["request_sha256"])
    sha(row["state_sha256"])
    integer(row["state_bytes"], positive=True)
    if row["state_storage"] == "CANONICAL_CODEC_GRAPH":
        sha(row["state_root_sha256"])
    else:
        require(row["state_storage"] == "RAW_CANONICAL_JSON"
                and row["state_root_sha256"] is None, "Integrity frame root/storage differs")
    return row


def reference_for_frame(frame, *, accepted_base_sha256, checkpoint_sha256, base_revision):
    sha(accepted_base_sha256)
    sha(checkpoint_sha256)
    integer(base_revision)
    kind = "ROOT_ACCEPTED_BASE" if frame["revision"] <= base_revision else "MANAGED_STORE_CHECKPOINT"
    value = {"schema": REFERENCE_SCHEMA, "kind": kind, "algorithm": REFERENCE_ALGORITHM,
             "engagement_id": frame["engagement_id"], "revision": frame["revision"],
             "selected_event_sha256": frame["event_sha256"],
             "selected_request_sha256": frame["request_sha256"],
             "state_storage": frame["state_storage"],
             "selected_state_root_sha256": frame["state_root_sha256"],
             "selected_state_sha256": frame["state_sha256"],
             "selected_state_bytes": frame["state_bytes"],
             "accepted_base_sha256": accepted_base_sha256,
             "checkpoint_sha256": accepted_base_sha256 if kind == "ROOT_ACCEPTED_BASE" else checkpoint_sha256}
    return validate_reference(value)


def inspect_selected_integrity(store, actor, engagement, *, revisions):
    """Private selected integrity mode; never computes an unknown array digest inline."""
    runtime = getattr(store, "_managed_history_integrity", None)
    if runtime is not None:
        return runtime.selected(actor, engagement, revisions=revisions)
    # Unselected/default lifetimes retain exact existing full semantics.
    from .history_inspection import inspect_history
    return inspect_history(store, actor, engagement, revisions=revisions)
