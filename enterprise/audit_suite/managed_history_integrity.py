"""Root-admitted integrity catalogue and managed Store append checkpoints.

This is an opt-in Main implementation. It never treats an input JSON object as
Root authority, never persists source bodies/states/answers, and never resumes
hashlib from a digest. Full canonical history-array inspection stays explicit.
"""

from contextlib import contextmanager
from collections import OrderedDict
from datetime import UTC, datetime
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import stat
import threading

from .history_integrity_reference import (
    FRAME_FIELDS, MAX_SAFE_INTEGER, identity, integer, reference_for_frame,
    require, sha, validate_frame, validate_reference,
)
from .store import canonical, digest

BASE_SCHEMA = "SH_ROOT_ACCEPTED_HISTORY_INTEGRITY_BASE_V1"
CHECKPOINT_SCHEMA = "SH_MANAGED_STORE_HISTORY_INTEGRITY_CHECKPOINT_V1"
FIELDS = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
          "st_size", "st_mtime_ns", "st_ctime_ns")
MAX_CATALOGUE_BYTES = 16 * 1024**2
MAX_FRAMES = 100000
CURRENT_VALIDATION_FIELDS = (
    "id", "mode", "simulated_at", "company_source_binding", "artifacts",
    "scope", "revision", "phase", "evidence_acquisition",
)
RUNTIME_UPGRADE_MODULES = frozenset({
    "managed_history_integrity.py", "persistent_company_service.py",
    "retained_explanation_service.py",
})


def validate_runtime_source_upgrade(pin, *, base_pin, base, config):
    """A separately Root-admitted Source upgrade never rewrites history IDs."""
    admission = read_pin(pin)
    fields = {"schema", "base", "historical_retained_configuration", "current_code_pins",
        "changed_code_pin_names", "Root_source_review", "Root_actual_adoption",
        "actual_runtime_source_upgrade_accepted", "base_and_checkpoints_rewritten",
        "new_semantic_replay_claimed"}
    require(type(admission) is dict and set(admission) == fields
            and admission["schema"] == "SH_ROOT_ACTUAL_MANAGED_HISTORY_RUNTIME_SOURCE_UPGRADE_ADMISSION_V1"
            and admission["base"] == base_pin
            and admission["actual_runtime_source_upgrade_accepted"] is True
            and admission["base_and_checkpoints_rewritten"] is False
            and admission["new_semantic_replay_claimed"] is False,
            "Explicit actual Root Source-upgrade admission for this unchanged base required")
    historical = read_pin(admission["historical_retained_configuration"])
    require(type(historical) is dict and set(historical) == set(config)
            and type(historical.get("code_pins")) is dict
            and type(config.get("code_pins")) is dict
            and digest(historical["code_pins"]) == base["source_map_sha256"]
            and historical["history_integrity"]
            == {"base": base_pin, "ledger_directory": config["history_integrity"]["ledger_directory"]}
            and admission["current_code_pins"] == config["code_pins"]
            and set(historical["code_pins"]) == set(config["code_pins"]),
            "Exact historical base map and fresh configured current map required")
    for name in config["code_pins"]:
        sha(historical["code_pins"][name]); sha(config["code_pins"][name])
    changed = sorted(name for name in config["code_pins"]
                     if historical["code_pins"][name] != config["code_pins"][name])
    require(changed and set(changed) <= RUNTIME_UPGRADE_MODULES
            and admission["changed_code_pin_names"] == changed,
            "Only the selected exact managed-validation Source deltas are allowed")
    for name in config:
        if name not in {"code_pins", "history_integrity", "authority_head", "session_revocations"}:
            require(historical[name] == config[name],
                    "Source upgrade cannot change normal retained configuration meaning")
    review = read_pin(admission["Root_source_review"])
    adoption = read_pin(admission["Root_actual_adoption"])
    require(type(review) is dict and type(adoption) is dict
            and review.get("schema") == "SH_ROOT_MANAGED_VALIDATION_PROJECTION_SOURCE_REVIEW_V1"
            and review.get("runtime_source_upgrade_sources_accepted") is True
            and review.get("current_code_pins") == config["code_pins"]
            and adoption.get("schema") == "SH_ROOT_ACTUAL_MANAGED_VALIDATION_PROJECTION_ADOPTION_V1"
            and adoption.get("actual_runtime_source_upgrade_adopted") is True
            and adoption.get("current_code_pins") == config["code_pins"]
            and adoption.get("selected_source_review") == admission["Root_source_review"],
            "Actual selected Root Source review and Main adoption must join the current map")
    return [pin, admission["historical_retained_configuration"],
            admission["Root_source_review"], admission["Root_actual_adoption"]]


def metadata(path):
    value = Path(path).lstat()
    return {key: getattr(value, key) for key in FIELDS}


def file_pin(path):
    path = Path(path)
    before = metadata(path)
    require(stat.S_ISREG(before["st_mode"]) and before["st_nlink"] == 1
            and before["st_uid"] == os.getuid()
            and stat.S_IMODE(before["st_mode"]) == 0o600
            and path.is_absolute() and path == path.resolve()
            and not any(value.is_symlink() for value in (path, *path.parents)),
            "Private ordinary managed integrity file required")
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    require(metadata(path) == before, "Managed integrity file changed during SHA closure")
    return {"path": str(path), "sha256": value, "bytes": before["st_size"], "metadata": before}


def read_pin(pin):
    require(type(pin) is dict and set(pin) == {"path", "sha256"}, "Exact private pin required")
    sha(pin["sha256"])
    observed = file_pin(pin["path"])
    require(observed["sha256"] == pin["sha256"] and observed["bytes"] <= MAX_CATALOGUE_BYTES,
            "Selected managed integrity pin/size differs")
    raw = Path(pin["path"]).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"]
            and metadata(pin["path"]) == observed["metadata"], "Managed pin changed while reading")
    return json.loads(raw)


def write_new(directory, name, value):
    path = Path(directory) / name
    raw = (canonical(value) + "\n").encode()
    require(len(raw) <= MAX_CATALOGUE_BYTES, "Managed checkpoint byte limit")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def frame_vector(frames):
    return hashlib.sha256(canonical(frames).encode()).hexdigest()


def validate_frames(frames, engagement):
    require(type(frames) is list and 1 <= len(frames) <= MAX_FRAMES, "Bounded full frame catalogue required")
    previous, previous_real, commands = "", 0, set()
    for revision, row in enumerate(frames):
        validate_frame(row, engagement=engagement, revision=revision,
                       previous_event_sha256=previous)
        require(row["command_id"] not in commands and row["recorded_at"] >= previous_real,
                "Managed catalogue command or chronology differs")
        commands.add(row["command_id"])
        previous, previous_real = row["event_sha256"], row["recorded_at"]
    return frames


def validate_base(base, *, expected_engagement, expected_mode, replay, acceptance, image_admission=None):
    required = {"schema", "engagement_id", "mode", "base_revision", "accepted_replay",
                "Root_replay_acceptance", "images", "frames", "frame_vector_sha256",
                "custody", "known_prefix_sha256", "born_binding_sha256", "source_map_sha256",
                "metadata_inventory_is_not_a_new_full_replay", "node_inventory", "image_provenance"}
    require(type(base) is dict and set(base) == required and base["schema"] == BASE_SCHEMA,
            "Exact Root-admitted base catalogue required")
    require(type(expected_engagement) is str and type(expected_mode) is str
            and base["engagement_id"] == expected_engagement and base["mode"] == expected_mode
            and expected_mode in {"CLEAN", "MESSY"}, "Foreign base engagement/mode")
    identity(expected_engagement)
    integer(base["base_revision"])
    sha(base["born_binding_sha256"])
    sha(base["source_map_sha256"])
    require(acceptance.get("schema") == "SH_ROOT_ACTUAL_CORRECTED_NATIVE_FULL_REPLAY_ACCEPTANCE_V1"
            and acceptance.get("actual_9e_complete_replay_and_genuine_wait0_accepted") is True
            and acceptance.get("actual_independent_fieldwork_replay_accepted") is True,
            "Actual Root accepted 9e replay and genuine wait0 required")
    require({k: acceptance["actual_proof"][k] for k in ("path", "sha256")} == base["accepted_replay"],
            "Root acceptance does not select this actual replay")
    require(replay.get("schema") == "SH_INDEPENDENT_CORRECTED_NATIVE_PAIRED_FIELDWORK_REPLAY_V1",
            "Exact genuinely accepted corrected replay schema required")
    mode = replay["modes"][expected_mode]
    require(mode["engagement_id"] == expected_engagement
            and mode["final_revision"] == base["base_revision"], "Accepted replay base boundary differs")
    require(base["metadata_inventory_is_not_a_new_full_replay"] is True,
            "Inventory must remain qualified to the genuine prior replay")
    validate_frames(base["frames"], expected_engagement)
    require(len(base["frames"]) == base["base_revision"] + 1
            and frame_vector(base["frames"]) == base["frame_vector_sha256"]
            and base["frames"][-1]["event_sha256"] == mode["last_event_sha256"]
            and base["frames"][-1]["state_sha256"] == mode["final_state_sha256"],
            "Accepted immutable history catalogue boundary/vector differs")
    # The current 9e receipt actually published only its complete final digest.
    require(base["known_prefix_sha256"] == {str(base["base_revision"]): mode["history_sha256"]},
            "Only actually published 9e canonical prefix digests may seed this catalogue")
    require(type(base["images"]) is dict and set(base["images"]) == {"prefix", "tail"},
            "Exact admitted ordinary image pair required")
    for value in base["images"].values():
        validate_image_descriptor(value)
    validate_image_provenance(base, acceptance, image_admission)
    validate_custody(base["custody"])
    validate_node_inventory(base["node_inventory"])
    return base


def accepted_image(value, acceptance):
    return any(type(row) is dict and row.get("path") == value["path"]
        and row.get("sha256") == value["sha256"] and row.get("bytes") == value["bytes"]
        and row.get("metadata9") == [value["metadata"][key] for key in FIELDS]
        for row in acceptance.get("fresh_refs", []))


def validate_image_provenance(base, acceptance, admission):
    provenance = base["image_provenance"]
    require(type(provenance) is dict and set(provenance) == {"kind", "admission"}
            and type(provenance["kind"]) is str, "Exact image provenance required")
    if provenance["kind"] == "EXACT_ACCEPTED_REPLAY_IMAGES":
        require(provenance["admission"] is None and admission is None
                and all(accepted_image(value, acceptance) for value in base["images"].values()),
                "Whole image SHA/length/physical identity is absent from actual Root replay closure")
        return
    require(provenance["kind"] == "ROOT_ADMITTED_MAIN_DERIVATIVE"
            and type(provenance["admission"]) is dict
            and set(provenance["admission"]) == {"path", "sha256"},
            "Exact separately Root-admitted derivative image provenance required")
    sha(provenance["admission"]["sha256"])
    keys = {"schema", "accepted_replay", "Root_replay_acceptance", "accepted_immutable_images",
            "images", "frame_vector_sha256", "born_binding_sha256", "source_map_sha256",
            "source_derivative_admission", "actual_image_and_frame_derivative_closure_accepted",
            "new_full_semantic_replay_claimed"}
    require(type(admission) is dict and set(admission) == keys
            and admission["schema"] == "SH_ROOT_ACTUAL_MANAGED_HISTORY_IMAGE_DERIVATIVE_ADMISSION_V1"
            and admission["accepted_replay"] == base["accepted_replay"]
            and admission["Root_replay_acceptance"] == base["Root_replay_acceptance"]
            and admission["images"] == base["images"]
            and admission["frame_vector_sha256"] == base["frame_vector_sha256"]
            and admission["born_binding_sha256"] == base["born_binding_sha256"]
            and admission["source_map_sha256"] == base["source_map_sha256"]
            and admission["actual_image_and_frame_derivative_closure_accepted"] is True
            and admission["new_full_semantic_replay_claimed"] is False,
            "Actual derivative image/frame/born/Source acceptance differs")
    require(type(admission["accepted_immutable_images"]) is dict
            and set(admission["accepted_immutable_images"]) == {"prefix", "tail"},
            "Exact genuinely accepted parent image pair required")
    for value in admission["accepted_immutable_images"].values():
        validate_image_descriptor(value)
        require(accepted_image(value, acceptance), "Derivative parent image is absent from actual Root replay closure")
    require(type(admission["source_derivative_admission"]) is dict
            and set(admission["source_derivative_admission"]) == {"path", "sha256"},
            "Separate selected derivative Source admission required")
    sha(admission["source_derivative_admission"]["sha256"])


def validate_image_descriptor(value):
    require(type(value) is dict and set(value) == {"path", "sha256", "bytes", "metadata"}
            and type(value["path"]) is str and Path(value["path"]).is_absolute(),
            "Exact admitted image descriptor required")
    sha(value["sha256"])
    integer(value["bytes"], positive=True)
    require(type(value["metadata"]) is dict and set(value["metadata"]) == set(FIELDS)
            and all(type(item) is int and item >= 0 for item in value["metadata"].values())
            and value["metadata"]["st_size"] == value["bytes"]
            and value["metadata"]["st_nlink"] == 1
            and stat.S_ISREG(value["metadata"]["st_mode"])
            and stat.S_IMODE(value["metadata"]["st_mode"]) == 0o600,
            "Exact private image metadata required")
    return value


def validate_custody(value):
    require(type(value) is dict and set(value) == {"files", "custody"}
            and all(type(value[key]) is dict and len(value[key]) <= MAX_FRAMES for key in value),
            "Bounded integrity-only original/custody descriptors required")
    for path, item in value["files"].items():
        require(type(path) is str and Path(path).is_absolute()
                and type(item) is dict and set(item) == {"sha256", "bytes"},
                "No body/answer fields allowed in original integrity metadata")
        sha(item["sha256"]); integer(item["bytes"])
    for command, item in value["custody"].items():
        identity(command)
        require(type(item) is dict and set(item) == {"receipt_sha256", "native_id", "native_metadata_sha256"},
                "No receipt/source bodies allowed in custody metadata")
        sha(item["receipt_sha256"]); sha(item["native_metadata_sha256"])
        require(type(item["native_id"]) in (list, tuple) and len(item["native_id"]) == 5,
                "Exact normal five-part Native identity required")
        for field in item["native_id"][:4]: identity(field)
        integer(item["native_id"][4], positive=True)
    return value


class IntegrityCatalogue:
    """Integrity metadata only; no parsed state, command payload, evidence or answer."""

    def __init__(self, base, base_sha256):
        self.base = base
        self.base_sha256 = sha(base_sha256)
        self.engagement = base["engagement_id"]
        self.frames = [dict(row) for row in base["frames"]]
        self.checkpoint_sha256 = self.base_sha256
        self.sequence = 0
        self.introducing_checkpoint = {}
        self.images = base["images"]
        self.custody = base["custody"]
        self.known_prefixes = dict(base["known_prefix_sha256"])
        self.node_inventory = base["node_inventory"]

    def apply_checkpoint(self, body, checkpoint_sha256, verify_signature):
        required = {"schema", "sequence", "accepted_base_sha256", "previous_checkpoint_sha256",
                    "engagement_id", "kind", "frames_before", "added_frames", "images",
                    "custody", "authority_head", "full_revocations", "node_inventory", "signature"}
        require(type(body) is dict and set(body) == required and body["schema"] == CHECKPOINT_SCHEMA,
                "Exact managed Store checkpoint required")
        require(body["accepted_base_sha256"] == self.base_sha256
                and body["previous_checkpoint_sha256"] == self.checkpoint_sha256
                and body["engagement_id"] == self.engagement
                and type(body["sequence"]) is int and body["sequence"] == self.sequence + 1
                and type(body["frames_before"]) is int and body["frames_before"] == len(self.frames),
                "Foreign, missing, reordered or rolled-back managed checkpoint")
        integer(body["sequence"], positive=True)
        require(body["kind"] in {"AUDIT_APPEND", "AUTH_TRANSITION"}, "Unrecognized managed transition")
        require(type(body["added_frames"]) is list
                and len(body["added_frames"]) == (1 if body["kind"] == "AUDIT_APPEND" else 0),
                "Only one genuine ordinary append or zero-frame auth transition may checkpoint")
        verify_signature({key: value for key, value in body.items() if key != "signature"}, body["signature"])
        frames = self.frames + body["added_frames"]
        validate_frames(frames, self.engagement)
        require(type(body["images"]) is dict and set(body["images"]) == {"prefix", "tail"}
                and body["images"]["prefix"] == self.images["prefix"], "Immutable prefix changed in transition")
        for value in body["images"].values():
            validate_image_descriptor(value)
        require(type(body["authority_head"]) is dict and set(body["authority_head"]) == {"path", "sha256"}
                and type(body["authority_head"]["path"]) is str
                and type(body["full_revocations"]) is dict,
                "Exact signed public authority and full revocation pins required")
        sha(body["authority_head"]["sha256"])
        for key, value in body["full_revocations"].items():
            require(type(key) is str and key.endswith(".json"),
                    "Exact signed session-revocation filename required")
            sha(key[:-5])
            sha(value)
        validate_custody(body["custody"])
        for group in ("files", "custody"):
            require(all(canonical(body["custody"][group].get(key)) == canonical(value) for key, value in self.custody[group].items()),
                    "Previously certified historical original/custody descriptor changed")
        # Validate every candidate field before changing any accepted state.
        # A refused signed checkpoint must not partly advance the catalogue.
        validate_node_inventory(body["node_inventory"])
        sha(checkpoint_sha256)
        for row in body["added_frames"]:
            self.introducing_checkpoint[row["revision"]] = sha(checkpoint_sha256)
        self.frames, self.images, self.custody = frames, body["images"], body["custody"]
        self.sequence, self.checkpoint_sha256 = body["sequence"], sha(checkpoint_sha256)
        self.node_inventory = body["node_inventory"]

    def reference(self, revision):
        integer(revision)
        require(revision < len(self.frames), "Recorded revision unavailable")
        return reference_for_frame(self.frames[revision], accepted_base_sha256=self.base_sha256,
            checkpoint_sha256=self.introducing_checkpoint.get(revision, self.base_sha256),
            base_revision=self.base["base_revision"])

    def validate_reference(self, value):
        validate_reference(value, engagement=self.engagement, accepted_base_sha256=self.base_sha256)
        require(canonical(value) == canonical(self.reference(value["revision"])),
                "Foreign checkpoint or changed selected recorded-revision reference")
        return value

    def checkpoint_fields(self, *, kind, frames_after, images, custody, authority_head,
                          full_revocations, node_metadata, transaction_committed):
        require(transaction_committed is True, "No certificate before a genuine Store commit")
        require(type(frames_after) is list and frames_after[:len(self.frames)] == self.frames,
                "Actual Store transition rewrote historical frames")
        added = frames_after[len(self.frames):]
        require(kind in {"AUDIT_APPEND", "AUTH_TRANSITION"}
                and len(added) == (1 if kind == "AUDIT_APPEND" else 0),
                "Unconfirmed or foreign Store transition delta")
        return {"schema": CHECKPOINT_SCHEMA, "sequence": self.sequence + 1,
                "accepted_base_sha256": self.base_sha256,
                "previous_checkpoint_sha256": self.checkpoint_sha256,
                "engagement_id": self.engagement, "kind": kind,
                "frames_before": len(self.frames), "added_frames": added,
                "images": images, "custody": custody, "authority_head": authority_head,
                "full_revocations": full_revocations, "node_inventory": validate_node_inventory(node_metadata)}


@contextmanager
def writer_lock(path):
    before = metadata(path)
    require(stat.S_ISREG(before["st_mode"]) and before["st_nlink"] == 1
            and before["st_uid"] == os.getuid(), "Exact owned ordinary room writer lock required")
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require({key: getattr(os.fstat(fd), key) for key in FIELDS} == before == metadata(path),
                "Retained room lock physical identity changed")
        yield
    finally:
        os.close(fd)


def audit_frame_inventory(store, db):
    """Actual ordered metadata inventory; never a new semantic/full-flat replay."""
    rows = []
    if store.compact_prefix is not None:
        query = "SELECT * FROM sealed_prefix.prefix_frames ORDER BY revision"
        for row in db.execute(query):
            command = store.compact_prefix.decode(db, row["command_root"], row["command_bytes"],
                row["command_sha256"], schema="sealed_prefix")
            rows.append({"engagement_id": row["engagement"], "revision": row["revision"],
                "command_id": row["command_id"], "request_sha256": row["request_hash"],
                "event_sha256": row["hash"], "previous_event_sha256": row["previous_hash"],
                "actor": row["actor"], "recorded_at": row["recorded_at"],
                "command_kind": json.loads(command)["kind"], "state_storage": "CANONICAL_CODEC_GRAPH",
                "state_root_sha256": row["state_root"], "state_sha256": row["state_sha256"],
                "state_bytes": row["state_bytes"]})
    else:
        # Original ordinary prefix is selected and small; hashes are inventory,
        # not a claim of new historical semantic validation.
        for row in db.execute("SELECT * FROM sealed_prefix.events ORDER BY revision"):
            raw = row["state"].encode()
            rows.append({"engagement_id": row["engagement"], "revision": row["revision"],
                "command_id": row["command_id"], "request_sha256": row["request_hash"],
                "event_sha256": row["hash"], "previous_event_sha256": row["previous_hash"],
                "actor": row["actor"], "recorded_at": row["recorded_at"],
                "command_kind": json.loads(row["command"])["kind"], "state_storage": "RAW_CANONICAL_JSON",
                "state_root_sha256": None, "state_sha256": hashlib.sha256(raw).hexdigest(),
                "state_bytes": len(raw)})
    for row in db.execute("SELECT * FROM main.event_frames ORDER BY revision"):
        value = store._state_descriptor(row["state"])
        require(set(value) == {"root", "bytes", "sha256"}, "Exact real codec frame descriptor required")
        command = json.loads(row["command"])
        require(digest(command) == row["request_hash"], "Actual canonical request hash differs")
        rows.append({"engagement_id": row["engagement"], "revision": row["revision"],
            "command_id": row["command_id"], "request_sha256": row["request_hash"],
            "event_sha256": row["hash"], "previous_event_sha256": row["previous_hash"],
            "actor": row["actor"], "recorded_at": row["recorded_at"],
            "command_kind": command["kind"], "state_storage": "CANONICAL_CODEC_GRAPH",
            "state_root_sha256": value["root"], "state_sha256": value["sha256"],
            "state_bytes": value["bytes"]})
    validate_frames(rows, store.prefix["engagement"])
    return rows


def node_inventory(db):
    """Integrity metadata only: never retain fragment payloads or decoded states."""
    rolling, count, maximum = hashlib.sha256(b"["), 0, 0
    for row in db.execute("SELECT rowid,id,kind,bytes FROM main.state_nodes ORDER BY rowid"):
        values = list(row)
        require(type(values[0]) is int and values[0] > maximum, "Node row order differs")
        sha(values[1])
        require(values[2] in {"L", "C"}, "Node kind differs")
        integer(values[3], positive=True)
        if count:
            rolling.update(b",")
        rolling.update(canonical(values).encode())
        maximum, count = values[0], count + 1
    rolling.update(b"]")
    return {"sha256": rolling.hexdigest(), "count": count, "maximum_rowid": maximum}


def validate_node_inventory(value):
    require(type(value) is dict and set(value) == {"sha256", "count", "maximum_rowid"},
            "Exact node integrity inventory required")
    sha(value["sha256"])
    integer(value["count"], positive=True)
    integer(value["maximum_rowid"], positive=True)
    return value


def verify_new_nodes(db, before, roots):
    """Hash every physical old/new payload, then validate the new graph delta.

    This bounded physical-byte pass intentionally retains old-node tamper
    checks; it does not reconstruct every old logical historical state.
    """
    from .canonical_state_codec import CHUNK, MAX_BYTES, MAX_GRAPH_DEPTH, _children, node_id
    rolling, count = hashlib.sha256(b"["), 0
    nodes = {}
    for row in db.execute("SELECT rowid,id,kind,payload,bytes FROM main.state_nodes ORDER BY rowid"):
        rowid, identifier, kind, payload, size = tuple(row)
        require(type(payload) is bytes and kind in {"L", "C"}
                and type(size) is int and 0 < size <= MAX_BYTES
                and node_id(kind, payload, size) == identifier,
                "Actual stored graph node byte hash/type differs during trusted transition")
        if rowid <= before["maximum_rowid"]:
            if count:
                rolling.update(b",")
            rolling.update(canonical([rowid, identifier, kind, size]).encode())
            count += 1
            continue
        children = () if kind == "L" else _children(payload)
        if kind == "L":
            require(size == len(payload) <= CHUNK, "New bounded literal differs")
        else:
            values = [db.execute("SELECT bytes FROM state_nodes WHERE id=?", (child,)).fetchone()
                      for child in children]
            require(all(value is not None for value in values)
                    and sum(value[0] for value in values) == size, "New exact child inventory differs")
        nodes[identifier] = children
    rolling.update(b"]")
    require(count == before["count"] and rolling.hexdigest() == before["sha256"],
            "Trusted write changed old node integrity metadata")
    seen, active, stack = set(), set(), [(root, False) for root in roots]
    while stack:
        root, closing = stack.pop()
        if root not in nodes or root in seen:
            continue
        if closing:
            active.remove(root)
            seen.add(root)
        else:
            require(root not in active and len(active) < MAX_GRAPH_DEPTH, "New graph cycle/depth refused")
            active.add(root)
            stack.append((root, True))
            stack.extend((child, False) for child in reversed(nodes[root]))
    require(seen == set(nodes), "Unregistered newly emitted graph node refused")
    return node_inventory(db)


class _TransactionNodeMemo:
    """Bounded raw codec tuples/proof from FRESH main-node rows in one read.

    This object is local to the selected read's reserved connection scope.
    Every miss validates actual bytes; normal chunks independently rehashes
    hits and keeps its complete ordering/length/cycle/depth checks. This is
    not a complete verified graph, an answer cache or a persisted proof.
    """
    MAX_PAYLOAD_BYTES = 32 * 1024**2
    MAX_NODES = 65536

    def __init__(self, db):
        require(db.in_transaction, "Actual reserved node-memo transaction required")
        self.db, self.changes = db, db.total_changes
        self.rows, self.proof = OrderedDict(), {}
        self.payload_bytes = 0
        self._context = None
        self._invalidated = False

    def active(self):
        @contextmanager
        def scope():
            require(self.db is not None and self.db.in_transaction
                    and self.db.total_changes == self.changes and not self._invalidated,
                    "One exact readonly node-memo connection/transaction required")
            try:
                yield self
            finally:
                self._invalidated = True
                self.rows.clear()
                self.proof.clear()
                self.payload_bytes = 0
                self.db = None
        require(self._context is None, "Node memo cannot be reopened or shared")
        self._context = scope()
        return self._context

    def get(self, identifier):
        from .canonical_state_codec import CHUNK, MAX_BYTES, _children, node_id, valid_id
        live = (self._context is not None
                and inspect.getgeneratorstate(self._context.gen) == inspect.GEN_SUSPENDED
                and self.db is not None and self.db.in_transaction
                and self.db.total_changes == self.changes and not self._invalidated)
        if not live:
            self._invalidated = True
        require(live and valid_id(identifier), "Closed/changed/foreign node-memo read refused")
        cached = self.rows.get(identifier)
        if cached is not None:
            self.rows.move_to_end(identifier)
            return cached
        row = self.db.execute("SELECT kind,payload,bytes FROM main.state_nodes WHERE id=?", (identifier,)).fetchone()
        require(row is not None, "Fresh historical state node unavailable")
        kind, payload, size = tuple(row)
        require(kind in {"L", "C"} and type(payload) is bytes and type(size) is int
                and 0 < size <= MAX_BYTES and node_id(kind, payload, size) == identifier,
                "Fresh historical node byte hash/type/length differs")
        if kind == "L":
            require(len(payload) == size <= CHUNK, "Exact historical literal bytes required")
            children = ()
        else:
            children = _children(payload)
        value = (kind, payload, size)
        # A single uncached oversize payload is refused; canonical node payloads
        # are normally <=64KiB literals or <=8.7KiB ordered child descriptors.
        require(len(payload) <= self.MAX_PAYLOAD_BYTES, "Historical memo payload bound exceeded")
        while self.rows and (self.payload_bytes + len(payload) > self.MAX_PAYLOAD_BYTES
                             or len(self.rows) >= self.MAX_NODES):
            key, prior = self.rows.popitem(last=False)
            self.payload_bytes -= len(prior[1])
            self.proof.pop(key)
        self.rows[identifier] = value
        self.proof[identifier] = {"kind": kind, "bytes": size, "children": children}
        self.payload_bytes += len(payload)
        return value


class ManagedHistoryRuntime:
    """Protected normal Store issuer; loaded only from exact selected Main config.

    Data retained on this object are pins, frame descriptors and custody hashes.
    Complete selected state/native bytes exist only inside a protected call.
    """

    def __init__(self, room, choice, *, owned_writer_fd=None):
        require(type(choice) is dict and set(choice) in (
                    {"base", "ledger_directory"},
                    {"base", "ledger_directory", "runtime_source_admission"}),
                "Exact Root-selected managed history configuration required")
        self.room, self.store = room, room.sealed_store
        self.base_pin = choice["base"]
        self.directory = Path(choice["ledger_directory"])
        require(self.directory == self.store.manifest_path.parent / "MANAGED_HISTORY_INTEGRITY"
                and self.directory.is_dir() and not self.directory.is_symlink()
                and stat.S_IMODE(self.directory.stat().st_mode) == 0o700
                and self.directory.stat().st_uid == os.getuid(), "Exact private integrity namespace required")
        self.writer_path = room.root.parent / "room.lock"
        self.owned_writer_fd = owned_writer_fd
        self._writer_local = threading.local()
        self.force_full = False
        self._issuing = False
        self._verified_stamps = None
        self._startup_completed = False
        base = read_pin(self.base_pin)
        replay = read_pin(base["accepted_replay"])
        acceptance = read_pin(base["Root_replay_acceptance"])
        provenance = base["image_provenance"]
        require(type(provenance) is dict and set(provenance) == {"kind", "admission"}
                and type(provenance["kind"]) is str, "Exact selected image provenance required")
        image_admission = (None if provenance["kind"] == "EXACT_ACCEPTED_REPLAY_IMAGES"
                           else read_pin(provenance["admission"]))
        if image_admission is not None:
            read_pin(image_admission["source_derivative_admission"])
        validate_base(base, expected_engagement=room.engagement, expected_mode=room.binding["mode"],
                      replay=replay, acceptance=acceptance, image_admission=image_admission)
        self._derivative_pins = ([] if image_admission is None else
            [provenance["admission"], image_admission["source_derivative_admission"]])
        require(base["born_binding_sha256"] == room.binding_sha256,
                "Certificate born binding differs from selected normal room")
        self.choice = json.loads(canonical(choice))
        self._source_upgrade_pins = []
        if "runtime_source_admission" in choice:
            self._source_upgrade_pins = validate_runtime_source_upgrade(
                choice["runtime_source_admission"], base_pin=self.base_pin, base=base, config=room.config)
        else:
            require(base["source_map_sha256"] == digest(room.config["code_pins"]),
                    "Root certificate runtime Source pin inventory differs")
        self.catalogue = IntegrityCatalogue(base, self.base_pin["sha256"])
        self._checkpoint_pins = {}
        for path in sorted(self.directory.glob("CHECKPOINT-*.json")):
            require(path.name == f"CHECKPOINT-{self.catalogue.sequence + 1:08d}.json",
                    "Managed checkpoint namespace is incomplete or foreign")
            pin = file_pin(path)
            body = read_pin({key: pin[key] for key in ("path", "sha256")})
            self.catalogue.apply_checkpoint(body, pin["sha256"], self.store.authority.verify_history_checkpoint)
            self._checkpoint_pins[pin["sha256"]] = {key: pin[key] for key in ("path", "sha256")}
        require(not (self.directory / "UNCERTIFIED_MUTATION.json").exists(),
                "Unconfirmed actual Store mutation requires separate Root reconciliation")
        require({path.name for path in self.directory.iterdir()}
                == {Path(pin["path"]).name for pin in self._checkpoint_pins.values()},
                "Unexpected file in protected managed integrity namespace")
        self.store._managed_history_integrity = self

    @property
    def force_full(self):
        return self._live_token(getattr(self._writer_local, "full_token", None))

    @force_full.setter
    def force_full(self, value):
        require(type(value) is bool, "Internal full-verification flag required")
        self._writer_local.full_token = self._flag_token(value)

    @property
    def _issuing(self):
        return self._live_token(getattr(self._writer_local, "issuer_token", None))

    @_issuing.setter
    def _issuing(self, value):
        require(type(value) is bool, "Internal trusted-issuer flag required")
        self._writer_local.issuer_token = self._flag_token(value)

    def _live_token(self, token):
        if type(token) is not dict or token.get("thread") != threading.get_ident():
            return False
        context = token.get("context")
        outer = token.get("outer")
        return (context is not None and inspect.getgeneratorstate(context.gen) == inspect.GEN_SUSPENDED
            and type(outer) is dict and outer.get("thread") == threading.get_ident()
            and inspect.getgeneratorstate(outer["context"].gen) == inspect.GEN_SUSPENDED)

    def _flag_token(self, value):
        if value is False:
            return None
        token = getattr(self._writer_local, "current_context", None)
        require(self._live_token(token), "Internal issuer requires its actual active protected invocation")
        return token

    def certificate_closure(self):
        """Fresh ordinary bytes, never rely on a stale parsed certificate alone."""
        for pin in (self.base_pin, self.catalogue.base["accepted_replay"],
                    self.catalogue.base["Root_replay_acceptance"], *self._derivative_pins,
                    *self._source_upgrade_pins,
                    *self._checkpoint_pins.values()):
            observed = file_pin(pin["path"])
            require(observed["sha256"] == pin["sha256"], "Selected integrity certificate bytes changed")
        require({path.name for path in self.directory.iterdir()}
                == {Path(pin["path"]).name for pin in self._checkpoint_pins.values()},
                "Unknown checkpoint or unconfirmed mutation requires Root reconciliation")

    def bootstrap(self):
        """Fresh bounded birth/current closure; not a new full historical replay."""
        from .sealed_retained_service import _birth
        with self.locked():
            from .history_inspection import _stamp
            prefix_stamp, outside = self.store.check_prefix(), _stamp(self.store.db_path)
            self.room.check_pins()
            self.certificate_closure()
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("PRAGMA query_only=ON")
                self.verify_image(db)
                initial = self._read_entry(db, 0)
                with self.store.prefix_connection() as prefix:
                    prefix.execute("BEGIN")
                    _birth(self.room, initial["state"], prefix)
            require(self.store.check_prefix() == prefix_stamp and _stamp(self.store.db_path) == outside,
                    "Journal changed during selected birth closure")
            return self.validate_current(self.room.binding["identities"]["operator"], self.room.engagement)

    def complete_startup(self):
        require(getattr(getattr(self.room, "engine", None), "store", None) is self.store
                and getattr(self.store, "_managed_history_integrity", None) is self
                and self.room.config.get("history_integrity")
                == self.choice,
                "Completed genuine configured managed Engine/Store required")
        with self.locked():
            self.validate_current(self.room.binding["identities"]["operator"], self.room.engagement)
            self.room.check_pins()
            self._startup_completed = True

    def locked(self):
        # A flag is a lease of THIS actual suspended context generator. If an
        # entry/cleanup BaseException closes that generator, it cannot confer
        # a later same-thread bypass even while a caller holds an outer RLock.
        token = {"thread": threading.get_ident(), "context": None, "outer": None}

        @contextmanager
        def scope():
            with self.room._integrity_lock:
                previous = getattr(self._writer_local, "current_context", None)
                outer = getattr(self._writer_local, "outer_context", None)
                depth = getattr(self._writer_local, "depth", 0)
                nested = self._live_token(outer)
                try:
                    token["outer"] = outer if nested else token
                    self._writer_local.current_context = token
                    self._writer_local.depth = depth + 1 if nested else 1
                    if nested:
                        yield
                    else:
                        self._writer_local.outer_context = token
                        with self._outer_writer_lock():
                            yield
                finally:
                    self._writer_local.current_context = previous
                    self._writer_local.depth = depth if nested else 0
                    if not nested:
                        self._writer_local.outer_context = None

        context = scope()
        token["context"] = context
        return context

    @contextmanager
    def _outer_writer_lock(self):
        if self.owned_writer_fd is None:
            with writer_lock(self.writer_path):
                yield
        else:
            require(type(self.owned_writer_fd) is int and self.owned_writer_fd >= 0,
                    "Owned writer descriptor required")
            expected = metadata(self.writer_path)
            require({key: getattr(os.fstat(self.owned_writer_fd), key) for key in FIELDS} == expected,
                    "Root-owned lifetime writer descriptor differs")
            # Re-lock the SAME open file description; never open a conflicting
            # second descriptor or release the Root viewer's lifetime lock.
            fcntl.flock(self.owned_writer_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def _images(self):
        return {"prefix": file_pin(self.store.prefix_path), "tail": file_pin(self.store.db_path)}

    def verify_image(self, db):
        require(db.in_transaction, "Reserved actual image transaction required")
        self.certificate_closure()
        stamps = (metadata(self.store.prefix_path), metadata(self.store.db_path))
        require(not any(Path(str(self.store.prefix_path) + suffix).exists()
                        for suffix in ("-wal", "-shm", "-journal")),
                "Unsettled immutable prefix sidecar refused")
        # During the trusted post-commit issuer window, the new event is separately
        # checked below. This flag is never taken from JSON or an HTTP payload.
        if self._issuing:
            return None
        # Normal WAL-mode BEGIN creates its own empty WAL/SHM. Require the
        # exact connection's outside image to be quiescent, then permit only
        # its empty WAL and ordinary private SHM under the held writer lock.
        outside = db._request_outer_stamp
        require(not any(outside[0][1:]), "Preexisting unsettled tail sidecar refused")
        for suffix, size in (("-wal", 0), ("-shm", 32768), ("-journal", None)):
            path = Path(str(self.store.db_path) + suffix)
            if path.exists():
                info = metadata(path)
                require(size is not None and info["st_size"] == size
                        and stat.S_ISREG(info["st_mode"]) and info["st_nlink"] == 1
                        and info["st_uid"] == os.getuid() and not path.is_symlink(),
                        "Only this owned quiescent read's ordinary empty sidecar is permitted")
        if stamps != self._verified_stamps:
            observed = self._images()
            for key in ("prefix", "tail"):
                expected = self.catalogue.images[key]
                require(observed[key]["path"] == expected["path"]
                        and observed[key]["sha256"] == expected["sha256"]
                        and observed[key]["bytes"] == expected["bytes"]
                        and observed[key]["metadata"] == expected["metadata"],
                        "Unrecognized current image; never extend stale whole-tail certificate")
            require(audit_frame_inventory(self.store, db) == self.catalogue.frames,
                "Complete fresh codec/frame descriptor inventory differs")
            require(node_inventory(db) == self.catalogue.node_inventory,
                    "Complete fresh stored-node descriptor inventory differs")
            self._verified_stamps = stamps
        require((metadata(self.store.prefix_path), metadata(self.store.db_path)) == stamps,
                "Image changed during managed integrity closure")
        return None

    def _source_closure(self, current):
        from .sealed_retained_service import _close_sources, _current, _sources
        from .company_store import _time
        _current(self.room, current)
        require(_time(current["simulated_at"]) >= _time(self.room.binding["initial_simulated_at"]),
                "Current selected simulated clock precedes born fieldwork clock")
        with self.room.world.locked():
            native, journal = _sources(self.room)
            proof = {"files": self.catalogue.custody["files"], "custody": {
                key: value | {"native_id": tuple(value["native_id"])}
                for key, value in self.catalogue.custody["custody"].items()}}
            files = self.room._verify_integrity_descriptors(proof, native, journal)
            custody = dict(proof["custody"])
            self.room.verify_artifacts(current, native, journal=journal, files=files, custody=custody)
            _close_sources(self.room, files)
        return {"files": {str(path): {"sha256": value[1], "bytes": value[2]}
                           for path, value in files.items()}, "custody": custody}

    def _read_current_entry(self, db, revision, *, validation_only=False):
        """Fresh primary current bytes and certified codec metadata, no graph decode.

        The whole current image/frame/node catalogue was checked in this held
        transaction, or its genuine Store write is in the protected issuer
        window after verify_new_nodes. No state/body is retained on the runtime.
        Explicit historical revisions keep their original reconstruction path.
        """
        from .canonical_state_codec import CHUNK, MAX_BYTES, _children, node_id
        from .serialized_json import canonical_bytes, canonical_projection, update_object
        require(type(validation_only) is bool, "Explicit internal current-validation mode required")
        require(db.in_transaction and revision == len(self.catalogue.frames) - 1,
                "Reserved actual latest-current transaction required")
        frame = self.catalogue.frames[revision]
        current = db.execute("SELECT id,revision,state FROM main.engagements WHERE id=?",
                             (self.room.engagement,)).fetchone()
        row = db.execute("SELECT engagement,revision,command_id,request_hash,actor,recorded_at,previous_hash,hash,state,command FROM main.event_frames WHERE engagement=? AND revision=?",
                         (self.room.engagement, revision)).fetchone()
        require(current is not None and row is not None and current["id"] == self.room.engagement
                and type(current["revision"]) is int and current["revision"] == revision,
                "Fresh primary latest-current row unavailable or foreign")
        header = {"engagement_id": row["engagement"], "revision": row["revision"],
            "command_id": row["command_id"], "request_sha256": row["request_hash"],
            "event_sha256": row["hash"], "previous_event_sha256": row["previous_hash"],
            "actor": row["actor"], "recorded_at": row["recorded_at"]}
        require(all(header[key] == frame[key] for key in header)
                and frame["state_storage"] == "CANONICAL_CODEC_GRAPH",
                "Exact current event-frame/certificate header differs")
        descriptor = self.store._state_descriptor(row["state"])
        require(set(descriptor) == {"root", "bytes", "sha256"}
                and descriptor == {"root": frame["state_root_sha256"],
                    "bytes": frame["state_bytes"], "sha256": frame["state_sha256"]},
                "Exact latest graph descriptor/certificate differs")
        node = db.execute("SELECT kind,payload,bytes FROM main.state_nodes WHERE id=?",
                          (descriptor["root"],)).fetchone()
        require(node is not None, "Latest stored root node unavailable")
        kind, payload, size = tuple(node)
        require(kind in {"L", "C"} and type(payload) is bytes and type(size) is int
                and 0 < size <= MAX_BYTES and size == descriptor["bytes"]
                and node_id(kind, payload, size) == descriptor["root"],
                "Fresh stored latest-root node byte hash/type/length differs")
        if kind == "L":
            require(len(payload) == size <= CHUNK, "Exact bounded latest literal root required")
        else:
            children = _children(payload)
            sizes = [db.execute("SELECT bytes FROM main.state_nodes WHERE id=?", (child,)).fetchone()
                     for child in children]
            require(all(value is not None and type(value[0]) is int and value[0] > 0 for value in sizes)
                    and sum(value[0] for value in sizes) == size,
                    "Exact current root child membership/length differs")
        require(type(current["state"]) is str and type(row["command"]) is str,
                "Exact current raw UTF-8 state and command required")
        if validation_only:
            raw, state = canonical_projection(current["state"], CURRENT_VALIDATION_FIELDS)
        else:
            raw = canonical_bytes(current["state"])
        require(type(current["state"]) is str and raw == current["state"].encode()
                and len(raw) == frame["state_bytes"]
                and hashlib.sha256(raw).hexdigest() == frame["state_sha256"],
                "Fresh canonical primary current state bytes/hash differ")
        command_raw = canonical_bytes(row["command"])
        require(type(row["command"]) is str and command_raw == row["command"].encode()
                and hashlib.sha256(command_raw).hexdigest() == frame["request_sha256"],
                "Fresh canonical current command/request differs")
        if not validation_only:
            state = json.loads(current["state"])
        command = json.loads(row["command"])
        require(command["kind"] == frame["command_kind"], "Current command kind differs")
        record = {key: row[key] for key in ("actor", "recorded_at", "previous_hash", "command_id")}
        event = hashlib.sha256()
        update_object(event, {key: canonical(value).encode() for key, value in record.items()}
                      | {"state": raw, "command": command_raw})
        require(event.hexdigest() == frame["event_sha256"],
                "Fresh selected actual current event differs")
        require(state["id"] == self.room.engagement and state["mode"] == self.room.binding["mode"]
                and state["scope"] == self.room.binding["scope"]
                and type(state["revision"]) is int and state["revision"] == revision,
                "Fresh selected current identity/scope/revision differs")
        return record | {"state": state, "command": command, "hash": frame["event_sha256"], "revision": revision}

    def _read_historical_tail_entry(self, db, revision, node_memo=None):
        """Direct real codec frame and freshly reconstructed historical bytes."""
        from .canonical_state_codec import decode
        from .serialized_json import canonical_bytes, update_object
        require(db.in_transaction, "Reserved actual historical entry read required")
        frame = self.catalogue.frames[revision]
        row = db.execute("SELECT engagement,revision,command_id,request_hash,actor,recorded_at,previous_hash,hash,state,command FROM main.event_frames WHERE engagement=? AND revision=?",
                         (self.room.engagement, revision)).fetchone()
        require(row is not None, "Selected real historical frame unavailable")
        header = {"engagement_id": row["engagement"], "revision": row["revision"],
            "command_id": row["command_id"], "request_sha256": row["request_hash"],
            "event_sha256": row["hash"], "previous_event_sha256": row["previous_hash"],
            "actor": row["actor"], "recorded_at": row["recorded_at"]}
        require(all(header[key] == frame[key] for key in header)
                and frame["state_storage"] == "CANONICAL_CODEC_GRAPH",
                "Exact historical frame/certificate header differs")
        descriptor = self.store._state_descriptor(row["state"])
        require(set(descriptor) == {"root", "bytes", "sha256"}
                and descriptor == {"root": frame["state_root_sha256"],
                    "bytes": frame["state_bytes"], "sha256": frame["state_sha256"]},
                "Exact historical graph descriptor/certificate differs")
        if node_memo is None:
            raw = decode(db, descriptor["root"])
        else:
            require(type(node_memo) is _TransactionNodeMemo and node_memo.db is db,
                    "Exact same-connection historical node memo required")
            raw = decode(db, descriptor["root"], proof=node_memo.proof, contents=node_memo)
        require(len(raw) == frame["state_bytes"]
                and hashlib.sha256(raw).hexdigest() == frame["state_sha256"],
                "Fresh reconstructed full historical state hash/length differs")
        text = raw.decode("utf-8")
        require(canonical_bytes(text) == raw and type(row["command"]) is str,
                "Actual historical bytes must retain exact canonical representation")
        command_raw = canonical_bytes(row["command"])
        require(command_raw == row["command"].encode()
                and hashlib.sha256(command_raw).hexdigest() == frame["request_sha256"],
                "Fresh canonical historical request differs")
        state, command = json.loads(text), json.loads(row["command"])
        require(command["kind"] == frame["command_kind"], "Historical command kind differs")
        record = {key: row[key] for key in ("actor", "recorded_at", "previous_hash", "command_id")}
        event = hashlib.sha256()
        update_object(event, {key: canonical(value).encode() for key, value in record.items()}
                      | {"state": raw, "command": command_raw})
        require(event.hexdigest() == frame["event_sha256"], "Fresh selected actual historical event differs")
        require(state["id"] == self.room.engagement and state["mode"] == self.room.binding["mode"]
                and state["scope"] == self.room.binding["scope"]
                and type(state["revision"]) is int and state["revision"] == revision,
                "Fresh selected historical identity/scope/revision differs")
        return record | {"state": state, "command": command, "hash": frame["event_sha256"], "revision": revision}

    def _read_entry(self, db, revision, *, node_memo=None, validation_only=False):
        require(type(validation_only) is bool and (not validation_only
                or revision == len(self.catalogue.frames) - 1),
                "Validation projection is restricted to the actual current revision")
        integer(revision)
        require(revision < len(self.catalogue.frames), "Selected revision unavailable")
        if (revision == len(self.catalogue.frames) - 1 and self.store.state_codec is not None
                and revision > self.store.prefix["revision"]
                and self.catalogue.frames[revision]["state_storage"] == "CANONICAL_CODEC_GRAPH"):
            return self._read_current_entry(db, revision, validation_only=validation_only)
        if (self.store.state_codec is not None and revision > self.store.prefix["revision"]
                and self.catalogue.frames[revision]["state_storage"] == "CANONICAL_CODEC_GRAPH"):
            return self._read_historical_tail_entry(db, revision, node_memo=node_memo)
        row = db.execute("SELECT * FROM events WHERE engagement=? AND revision=?",
                         (self.room.engagement, revision)).fetchone()
        require(row is not None, "Selected real event unavailable")
        state, command = json.loads(row["state"]), json.loads(row["command"])
        frame = self.catalogue.frames[revision]
        raw = canonical(state).encode()
        require(len(raw) == frame["state_bytes"]
                and hashlib.sha256(raw).hexdigest() == frame["state_sha256"]
                and digest(command) == frame["request_sha256"], "Fresh selected state/request differs")
        record = {key: row[key] for key in ("actor", "recorded_at", "previous_hash", "command_id")}
        require(digest(record | {"state": state, "command": command}) == frame["event_sha256"],
                "Fresh selected actual event differs")
        require(state["id"] == self.room.engagement and state["mode"] == self.room.binding["mode"]
                and state["scope"] == self.room.binding["scope"]
                and type(state["revision"]) is int and state["revision"] == revision,
                "Fresh selected identity/scope/revision differs")
        return record | {"state": state, "command": command, "hash": frame["event_sha256"], "revision": revision}

    def selected(self, actor, engagement, *, revisions=()):
        return self._select(actor, engagement, revisions=revisions, validation_only=False)

    def validate_current(self, actor, engagement):
        """Internal fresh integrity closure; no partial state is a public inspection."""
        return self._select(actor, engagement, revisions=(), validation_only=True)

    def _select(self, actor, engagement, *, revisions, validation_only):
        require(type(validation_only) is bool and (not validation_only or not revisions),
                "Internal validation cannot substitute for selected historical inspection")
        require(engagement == self.room.engagement and type(revisions) in (tuple, list, set)
                and len(revisions) <= 16, "Exact bounded selected integrity request required")
        for revision in revisions:
            integer(revision)
        with self.locked():
            from .history_inspection import _stamp
            prefix_stamp, outside = self.store.check_prefix(), _stamp(self.store.db_path)
            self.room.check_pins()
            self.certificate_closure()
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("PRAGMA query_only=ON")
                self.store._authorize(db, actor, engagement)
                self.verify_image(db)
                latest_revision = len(self.catalogue.frames) - 1
                wanted = set(revisions) | {latest_revision}
                with _TransactionNodeMemo(db).active() as node_memo:
                    entries = {revision: self._read_entry(db, revision, node_memo=node_memo,
                                                         validation_only=validation_only)
                               for revision in wanted}
                latest = entries[latest_revision]
                self._source_closure(latest["state"])
                activity = []
                # Ordinary link inventory needs actors/kinds/event identities.
                # Only actual inspection commands need their bounded payload,
                # and those are read FRESH; no payload survives this method.
                for frame in self.catalogue.frames:
                    command = {"kind": frame["command_kind"]}
                    if frame["command_kind"] == "artifact.inspection.record":
                        saved = db.execute("SELECT command FROM events WHERE engagement=? AND revision=?",
                            (engagement, frame["revision"])).fetchone()
                        command = json.loads(saved[0])
                        require(digest(command) == frame["request_sha256"], "Inspection command changed")
                    activity.append({"revision": frame["revision"], "actor": frame["actor"],
                        "command_id": frame["command_id"], "recorded_at": frame["recorded_at"],
                        "hash": frame["event_sha256"], "command": command})
                self.store._authorize(db, actor, engagement)
                self.verify_image(db)
            self.room.check_pins()
            self.certificate_closure()
            require(self.store.check_prefix() == prefix_stamp and _stamp(self.store.db_path) == outside,
                    "Selected journal changed before private response publication")
            self.store._retained_typed_stamp = (prefix_stamp, outside)
            known = {revision: self.catalogue.known_prefixes[str(revision)] for revision in wanted
                     if str(revision) in self.catalogue.known_prefixes}
            result = {"count": len(self.catalogue.frames), "latest": latest,
                      "selected": {revision: entries[revision] for revision in revisions},
                      "prefix_sha256": known, "activity": activity,
                      "selected_integrity_reference": {revision: self.catalogue.reference(revision)
                                                       for revision in revisions},
                      "history_integrity_kind": "ROOT_BASE_AND_MANAGED_STORE_CHAIN",
                      "complete_history_sha256_computed_by_this_call": False}
            if str(latest_revision) in self.catalogue.known_prefixes:
                result["history_sha256"] = self.catalogue.known_prefixes[str(latest_revision)]
            # Unknown legacy array digest is OMITTED, never null or another SHA.
            return result

    def validate_reference(self, value):
        with self.locked():
            self.certificate_closure()
            self.catalogue.validate_reference(value)
            checkpoint = value["checkpoint_sha256"]
            if value["kind"] == "MANAGED_STORE_CHECKPOINT":
                require(checkpoint in self._checkpoint_pins, "Foreign managed introducing checkpoint")
                body = read_pin(self._checkpoint_pins[checkpoint])
                self.store.authority.verify_history_checkpoint(
                    {key: value for key, value in body.items() if key != "signature"}, body["signature"])
        return value

    def mutate(self, operation, *, kind, command=None):
        """Only adapters around genuine normal Store commit may enter this issuer."""
        with self.locked():
            require(not self._issuing, "Nested or abandoned managed issuer")
            from .company_store import _time
            validated_before = self.validate_current(self.room.binding["identities"]["operator"], self.room.engagement)
            before_simulated_at = _time(validated_before["latest"]["state"]["simulated_at"])
            del validated_before  # Only the clock scalar survives this same protected issuer call.
            before = self._images()
            committed = False
            try:
                self._issuing = True
                result = operation()  # Existing Store context manager commits before return.
                committed = True
                after = self._images()
                if after == before:
                    return result  # Genuine duplicate/no-write; no fictional new checkpoint.
                with self.store.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("PRAGMA query_only=ON")
                    actual = audit_frame_inventory(self.store, db)
                    require(actual[:len(self.catalogue.frames)] == self.catalogue.frames,
                            "Managed command rewrote historical metadata")
                    added = actual[len(self.catalogue.frames):]
                    require(len(added) == (1 if kind == "AUDIT_APPEND" else 0),
                            "Actual Store return does not confirm expected frame delta")
                    if kind == "AUDIT_APPEND":
                        require(command is not None and added[0]["command_id"] == command["command_id"]
                                and added[0]["request_sha256"] == digest(command),
                                "Committed frame does not join actual requested command")
                    nodes = verify_new_nodes(db, self.catalogue.node_inventory,
                        [row["state_root_sha256"] for row in added
                         if row["state_storage"] == "CANONICAL_CODEC_GRAPH"])
                    # _read_entry uses the actual new inventory, not returned/projected state.
                    saved_frames = self.catalogue.frames
                    self.catalogue.frames = actual
                    try:
                        latest = self._read_entry(db, len(actual) - 1, validation_only=True)
                        if added:
                            require(before_simulated_at <= _time(latest["state"]["simulated_at"]),
                                    "Genuine append simulated clock regressed")
                        custody = self._source_closure(latest["state"])
                    finally:
                        self.catalogue.frames = saved_frames
                    self.store.verify_projection(db)  # Fresh signed public credentials/identity.
                    self.store.session_authority.check_revocations(self.store.prefix["sha256"], self.room.engagement)
                    head = self.store.authority_head
                    revocations = dict(self.store.session_authority.known_revocations)
                closed = self._images()
                require(closed == after, "Image changed during actual append certification")
                fields = self.catalogue.checkpoint_fields(kind=kind, frames_after=actual, images=closed,
                    custody=custody, authority_head=head, full_revocations=revocations,
                    node_metadata=nodes, transaction_committed=committed)
                body = fields | {"signature": self.store.authority.sign_history_checkpoint(fields)}
                pin = write_new(self.directory, f"CHECKPOINT-{self.catalogue.sequence + 1:08d}.json", body)
                self.catalogue.apply_checkpoint(body, pin["sha256"], self.store.authority.verify_history_checkpoint)
                self._checkpoint_pins[pin["sha256"]] = pin
                self._verified_stamps = (closed["prefix"]["metadata"], closed["tail"]["metadata"])
                return result
            except BaseException:
                # A method can commit then raise before returning. A changed
                # actual image still needs reconciliation; never mislabel it
                # as rollback or silently extend the old certificate.
                changed = True
                if not committed:
                    try:
                        changed = self._images() != before
                    except BaseException:
                        changed = True
                if committed or changed:
                    # Preserve a real unconfirmed post-commit state, never retry or
                    # pretend the data mutation rolled back after a certificate error.
                    marker = self.directory / "UNCERTIFIED_MUTATION.json"
                    if not marker.exists():
                        write_new(self.directory, marker.name, {"schema": "SH_UNCERTIFIED_ACTUAL_STORE_MUTATION_V1",
                            "UTC": datetime.now(UTC).isoformat(), "genuine_Store_return_before_failure": committed,
                            "actual_image_changed_or_closure_unknown": changed,
                            "automatic_retry": False, "Root_reconciliation_required": True})
                raise
            finally:
                self._issuing = False

    def full_public_history(self, actor, revisions):
        """The original complete array algorithm remains explicit, exact and expensive."""
        from .sealed_retained_service import finish_startup, read_sealed, verify_sealed
        with self.locked():
            self.force_full = True
            try:
                verify_sealed(self.room)
                finish_startup(self.room)
                result = read_sealed(self.room, actor, revisions)
                # Only the unchanged full algorithm's genuine computed values
                # may become known metadata in this lifetime. No hash context,
                # evidence or parsed state is persisted or fabricated.
                require(result["latest"]["revision"] == len(self.catalogue.frames) - 1
                        and result["latest"]["hash"] == self.catalogue.frames[-1]["event_sha256"],
                        "Explicit full history differs from selected managed chain")
                for revision, value in result["prefix_sha256"].items():
                    integer(revision)
                    sha(value)
                    require(str(revision) not in self.catalogue.known_prefixes
                            or self.catalogue.known_prefixes[str(revision)] == value,
                            "Actually computed legacy array SHA differs from accepted known value")
                    self.catalogue.known_prefixes[str(revision)] = value
                return result
            finally:
                self.force_full = False
                self.store._typed_composed_reader = lambda actor, revisions: self.full_public_history(actor, revisions)

    def legacy_prefix_sha256(self, actor, engagement, revision):
        """Compatibility for an explicitly selected stored V1 record only."""
        require(engagement == self.room.engagement, "Foreign legacy record engagement")
        integer(revision)
        with self.locked():
            self.selected(actor, engagement, revisions=[revision])
            if str(revision) not in self.catalogue.known_prefixes:
                self.full_public_history(actor, [revision])
            return sha(self.catalogue.known_prefixes[str(revision)])


def artifact_namespace_inventory(root):
    """Whole physical original bytes -> integrity descriptors, never stored bodies."""
    directory = Path(root) / "artifacts"
    before = metadata(directory)
    require(stat.S_ISDIR(before["st_mode"]) and stat.S_IMODE(before["st_mode"]) == 0o700
            and before["st_uid"] == os.getuid() and directory == directory.resolve(),
            "Exact private original namespace required")
    paths = sorted(directory.iterdir())
    require(len(paths) <= MAX_FRAMES, "Original integrity namespace count limit")
    names = [path.name for path in paths]
    files = {}
    for path in paths:
        sha(path.name)
        value = file_pin(path)
        require(value["sha256"] == path.name and value["bytes"] <= 2 * 1024**3,
                "Original filename/whole bytes/length differs")
        files[str(path)] = {"sha256": value["sha256"], "bytes": value["bytes"]}
    require(metadata(directory) == before and sorted(path.name for path in directory.iterdir()) == names,
            "Complete original namespace changed during census")
    return files


def collect_root_history_metadata(room, *, held_writer_fd, root_authorized=False):
    """Root-only bounded inventory for a future selected base, NO new replay.

    The operator supplies the already pinned normal Source/born binding
    boundary and standalone SealedHistoryStore. It need not construct an
    interactive RetainedWorkroom or reconstruct all historical raw states.
    No HTTP route calls this function; no base/ledger is automatically issued.
    """
    require(root_authorized is True, "Separate actual Root metadata-inventory authorization required")
    from .sealed_history_store import SealedHistoryStore
    from .sealed_retained_service import _birth, _close_sources, _current, _sources
    from .fresh_sec003_procedure import NATIVE_ID
    from .company_store import CompanyStore, _time
    store = room.sealed_store
    require(type(store) is SealedHistoryStore and store.state_codec is not None
            and getattr(store, "_managed_history_integrity", None) is None,
            "Exact standalone normal codec Store without an installed certificate required")
    require(type(held_writer_fd) is int and held_writer_fd >= 0
            and {key: getattr(os.fstat(held_writer_fd), key) for key in FIELDS}
            == metadata(room.root.parent / "room.lock"), "Actual owned writer descriptor differs")
    fcntl.flock(held_writer_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with room._integrity_lock:
        room.check_pins()
        if hasattr(room, "check_history_metadata_sources"):
            room.check_history_metadata_sources()
        for path in (store.prefix_path, store.db_path):
            require(not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")),
                    "Root census starts from settled physical images only")
        images = {"prefix": file_pin(store.prefix_path), "tail": file_pin(store.db_path)}
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("PRAGMA query_only=ON")
            frames = audit_frame_inventory(store, db)
            nodes = node_inventory(db)
            row = db.execute("SELECT revision,state FROM main.engagements WHERE id=?", (room.engagement,)).fetchone()
            require(row is not None and row["revision"] == len(frames) - 1, "Current census boundary differs")
            raw = row["state"].encode()
            require(hashlib.sha256(raw).hexdigest() == frames[-1]["state_sha256"]
                    and len(raw) == frames[-1]["state_bytes"], "Current raw header/state hash differs")
            current = json.loads(raw)
            require(canonical(current).encode() == raw and current["id"] == room.engagement
                    and current["mode"] == room.binding["mode"] and current["scope"] == room.binding["scope"],
                    "Typed census engagement/mode/born scope differs")
            _current(room, current)
            with store.prefix_connection() as prefix:
                prefix.execute("BEGIN")
                initial = json.loads(prefix.execute("SELECT state FROM events WHERE revision=0").fetchone()[0])
                _birth(room, initial, prefix)
            with room.world.locked():
                native, journal = _sources(room)
                from .persistent_company_service import time_to_iso
                now = _time(time_to_iso())
                files = artifact_namespace_inventory(room.root)
                custody = {}
                selected_count = 0
                for command_id, receipt in journal.items():
                    require(type(receipt) is dict and set(receipt) == {"source", "principal_id", "engagement_id",
                            "collected_at", "simulated_as_of", "command_id", "content_bytes"},
                            "Exact historical normal collection receipt fields required")
                    if receipt["engagement_id"] != room.engagement or receipt["principal_id"] != room.binding["identities"]["auditor"]:
                        continue
                    source = receipt["source"]
                    key = tuple(source[name] for name in NATIVE_ID)
                    value = native.get(key)
                    require(value is not None and source == CompanyStore._metadata(value)
                            and all(source[name] == room.selected[name] for name in room.selected)
                            and receipt["command_id"] == command_id and type(source["version"]) is int
                            and source["version"] > 0 and type(receipt["content_bytes"]) is int
                            and receipt["content_bytes"] >= 0
                            and _time(source["available_at"]) <= _time(receipt["simulated_as_of"])
                            <= _time(current["simulated_at"])
                            and _time(source["imported_at"]) <= _time(receipt["collected_at"]) <= now,
                            "Exact historical Native receipt/identity/clock join differs")
                    path = str(room.root / "artifacts" / source["sha256"])
                    require(files.get(path) == {"sha256": source["sha256"], "bytes": receipt["content_bytes"]},
                            "Historical auditor receipt original is absent or byte-mismatched")
                    custody[command_id] = {"receipt_sha256": digest(receipt), "native_id": key,
                        "native_metadata_sha256": digest(CompanyStore._metadata(value))}
                    selected_count += 1
                descriptors = {"files": files, "custody": custody}
                originals = room._verify_integrity_descriptors(descriptors, native, journal)
                room.verify_artifacts(current, native, journal=journal, files=originals, custody=custody)
                _close_sources(room, originals)
                require(artifact_namespace_inventory(room.root) == files, "Original namespace closing census differs")
        closed = {"prefix": file_pin(store.prefix_path), "tail": file_pin(store.db_path)}
        room.check_pins()
        if hasattr(room, "check_history_metadata_sources"):
            room.check_history_metadata_sources()
        require(images == closed, "Census physical image changed")
        actual_map_sha = digest(room.config["code_pins"])
        prospective_map_sha = digest(getattr(room, "history_metadata_source_map", room.config["code_pins"]))
        return {"schema": "SH_ROOT_READONLY_HISTORY_INTEGRITY_METADATA_INVENTORY_V1",
            "mode": room.binding["mode"], "engagement_id": room.engagement, "revision": len(frames) - 1,
            "images": images, "frames": frames, "frame_vector_sha256": frame_vector(frames),
            "node_inventory": nodes, "custody": descriptors,
            "born_binding_sha256": room.binding_sha256, "source_map_sha256": prospective_map_sha,
            "actual_configuration_source_map_sha256": actual_map_sha,
            "prospective_runtime_source_map_sha256": prospective_map_sha,
            "actual_configuration_adoption_claimed": False,
            "selected_historical_auditor_receipts": selected_count,
            "new_full_semantic_replay_claimed": False, "certificate_issued": False}


def build_root_selected_base(inventory, *, accepted_replay, Root_replay_acceptance,
                             image_provenance, root_authorized=False):
    """Pure final assembly after Root closes actual inventory/image provenance."""
    require(root_authorized is True, "Separate actual Root base-issuance authorization required")
    replay, acceptance = read_pin(accepted_replay), read_pin(Root_replay_acceptance)
    require(type(inventory) is dict and set(inventory) == {"schema", "mode", "engagement_id", "revision",
            "images", "frames", "frame_vector_sha256", "node_inventory", "custody", "born_binding_sha256",
            "source_map_sha256", "selected_historical_auditor_receipts", "new_full_semantic_replay_claimed", "certificate_issued"}
            | {"actual_configuration_source_map_sha256", "prospective_runtime_source_map_sha256", "actual_configuration_adoption_claimed"}
            and inventory["schema"] == "SH_ROOT_READONLY_HISTORY_INTEGRITY_METADATA_INVENTORY_V1"
            and inventory["new_full_semantic_replay_claimed"] is False and inventory["certificate_issued"] is False
            and inventory["actual_configuration_adoption_claimed"] is False
            and inventory["source_map_sha256"] == inventory["prospective_runtime_source_map_sha256"],
            "Actual qualified metadata inventory required")
    mode = replay["modes"][inventory["mode"]]
    base = {"schema": BASE_SCHEMA, "engagement_id": inventory["engagement_id"], "mode": inventory["mode"],
        "base_revision": inventory["revision"], "accepted_replay": accepted_replay,
        "Root_replay_acceptance": Root_replay_acceptance, "images": inventory["images"],
        "frames": inventory["frames"], "frame_vector_sha256": inventory["frame_vector_sha256"],
        "custody": inventory["custody"], "known_prefix_sha256": {str(inventory["revision"]): mode["history_sha256"]},
        "born_binding_sha256": inventory["born_binding_sha256"], "source_map_sha256": inventory["source_map_sha256"],
        "metadata_inventory_is_not_a_new_full_replay": True, "node_inventory": inventory["node_inventory"],
        "image_provenance": image_provenance}
    admission = None if image_provenance["kind"] == "EXACT_ACCEPTED_REPLAY_IMAGES" else read_pin(image_provenance["admission"])
    validate_base(base, expected_engagement=inventory["engagement_id"], expected_mode=inventory["mode"],
        replay=replay, acceptance=acceptance, image_admission=admission)
    return base
