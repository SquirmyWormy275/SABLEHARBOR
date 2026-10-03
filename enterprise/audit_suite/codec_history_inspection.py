"""Fresh graph proofs with bounded unchanged-frame integrity descriptors.

Only exact root/flat hash/length, row metadata, typed custody/clock headers and
hash contexts survive an invocation. All graph bytes and every command are read
freshly. A new or changed frame recomputes its actual full canonical state,
event and request hashes. No evidence, state JSON or examination outcome is
memoized. The caller separately closes source/native/current authority checks.
"""

import hashlib
import json

from .canonical_state_codec import VerifiedInvocationGraph, decode
from .history_inspection import _activity, _entry, _fields, _meta, _verify_row
from .sealed_history_store import _require
from .serialized_json import canonical_bytes, canonical_projection, update_object
from .store import canonical

PROJECTION = (
    "id",
    "mode",
    "simulated_at",
    "company_source_binding",
    "artifacts",
    "scope",
    "revision",
)


def _header(state):
    return {name: state[name] for name in ("id", "mode", "simulated_at")} | {
        "revision": state.get("revision"),
        "company_binding_sha256": hashlib.sha256(
            canonical(state.get("company_source_binding")).encode()
        ).hexdigest(),
        "scope_sha256": hashlib.sha256(canonical(state.get("scope")).encode()).hexdigest(),
    }


def scan_codec(store, db, *, wanted, row_validator, previous_integrity, prefix):
    """One reserved read transaction and its already freshly verified graph."""
    graph = getattr(db, "_codec_invocation", None)
    _require(type(graph) is VerifiedInvocationGraph, "Fresh invocation graph required")
    graph.check(db)
    seed = store._prefix_integrity
    current = db.execute(
        "SELECT revision,state FROM engagements WHERE id=?", (store.prefix["engagement"],)
    ).fetchone()
    _require(
        current is not None and type(current["revision"]) is int,
        "Exact current codec state required",
    )
    rolling = seed["unfinished_history_hash"].copy()
    previous, count = store.prefix["last_hash"], seed["count"]
    selected, prefixes, activity, metadata, expected, integrity, contexts = (
        {},
        {},
        [],
        {},
        {},
        {},
        {},
    )
    all_prefixes = list(seed["prefixes"])
    last, last_canonical, last_raw, last_meta = (
        prefix["latest"],
        prefix["_latest_canonical_bytes"],
        None,
        None,
    )
    contiguous = previous_integrity is not None and "codec_contexts" in previous_integrity
    seen_commands = {row["command_id"] for row in prefix["activity"]}
    rows = db.execute(
        "SELECT rowid AS locator_rowid,* FROM main.event_frames "
        "WHERE engagement=? ORDER BY revision",
        (store.prefix["engagement"],),
    )
    for row in rows:
        rowid = row["locator_rowid"]
        _require(
            row["command_id"] not in seen_commands,
            "Original prefix/tail command identity overlaps",
        )
        seen_commands.add(row["command_id"])
        descriptor = store._state_descriptor(row["state"])
        _require(
            descriptor["root"] in graph._proof
            and graph._proof[descriptor["root"]]["bytes"] == descriptor["bytes"],
            "Exact freshly verified codec root byte count differs",
        )
        old = (
            None if previous_integrity is None else previous_integrity["state_integrity"].get(rowid)
        )
        command_text = row["command"]
        _require(type(command_text) is str, "Exact raw codec command required")
        raw_command = command_text.encode()
        command_bytes = canonical_bytes(command_text)
        command = json.loads(command_text)
        _require(type(command) is dict, "Exact codec command object required")
        raw_command_descriptor = (len(raw_command), hashlib.sha256(raw_command).hexdigest())
        command_sha = hashlib.sha256(command_bytes).hexdigest()
        _require(
            type(row["revision"]) is int
            and row["revision"] == count
            and row["engagement"] == store.prefix["engagement"]
            and row["previous_hash"] == previous
            and command_sha == row["request_hash"],
            "Codec revision/engagement/chain/request differs",
        )
        reusable = (
            old is not None
            and old.get("codec_descriptor") == descriptor
            and old["bytes"] == descriptor["bytes"]
            and old["sha256"] == descriptor["sha256"]
            and old["canonical_raw"] is True
            and old["header"] is not None
            and previous_integrity["metadata"].get(rowid) == _meta(row)
            and previous_integrity["expected"].get(rowid) == raw_command_descriptor
        )
        selected_state = count in wanted or count == current["revision"]
        state, raw_state, state_bytes = None, None, None
        if not reusable or not contiguous or selected_state:
            raw_state = decode(db, descriptor["root"], invocation=graph)
            _require(
                len(raw_state) == descriptor["bytes"]
                and hashlib.sha256(raw_state).hexdigest() == descriptor["sha256"],
                "Actual full flat codec digest differs",
            )
            if reusable:
                state_bytes = raw_state
            elif not selected_state:
                state_bytes, state = canonical_projection(raw_state.decode("utf-8"), PROJECTION)
            else:
                state_bytes = canonical_bytes(raw_state.decode("utf-8"))
            _require(state_bytes == raw_state, "Exact canonical codec frame required")
        if contiguous and reusable:
            context = previous_integrity["codec_contexts"].get(rowid)
            _require(context is not None, "Prior actual canonical frame hash context unavailable")
            rolling = context.copy()
            # The old event hash was actually computed from these exact freshly
            # verified root bytes, canonical command and unchanged typed row.
        else:
            contiguous = False
            fields = _fields(row, state_bytes, command_bytes)
            _verify_row(row, fields, count, previous)
            if count:
                rolling.update(b",")
            update_object(
                rolling,
                fields
                | {"hash": canonical(row["hash"]).encode(), "revision": canonical(count).encode()},
            )
        if selected_state:
            state = json.loads(raw_state)
        if state is None and reusable:
            row_validator(row, None, old["header"])
            header = old["header"]
        else:
            if state is None:
                state = json.loads(raw_state)
            row_validator(row, state)
            header = _header(state)
        integrity[rowid] = {
            "bytes": descriptor["bytes"],
            "sha256": descriptor["sha256"],
            "canonical_raw": True,
            "header": header,
            "codec_descriptor": dict(descriptor),
        }
        contexts[rowid] = rolling.copy()
        close = rolling.copy()
        close.update(b"]")
        all_prefixes.append(close.hexdigest())
        if selected_state:
            entry = _entry(row, state, command)
            if count in wanted:
                selected[count], prefixes[count] = entry, all_prefixes[-1]
            if count == current["revision"]:
                last, last_canonical, last_raw = entry, state_bytes, raw_state
        activity.append(_activity(row, command, command_bytes))
        metadata[rowid], expected[rowid] = _meta(row), raw_command_descriptor
        last_meta = {
            name: row[name]
            for name in (
                "revision",
                "actor",
                "recorded_at",
                "command_id",
                "hash",
                "previous_hash",
                "request_hash",
            )
        }
        previous, count = row["hash"], count + 1
    _require(
        last is not None
        and current["revision"] == count - 1
        and (
            current["state"].encode() == last_raw
            or canonical_bytes(current["state"]) == last_canonical
        ),
        "Codec history/current typed state mismatch",
    )
    graph.check(db)
    unfinished = rolling.copy()
    rolling.update(b"]")
    result = {
        "count": count,
        "latest": last,
        "selected": selected,
        "prefix_sha256": prefixes,
        "history_sha256": rolling.hexdigest(),
        "activity": activity,
    }
    candidate = {
        "count": count,
        "prefixes": tuple(all_prefixes),
        "history_sha256": rolling.hexdigest(),
        "metadata": metadata,
        "expected": expected,
        "locations": None,
        "current_raw_sha256": hashlib.sha256(current["state"].encode()).hexdigest(),
        "state_integrity": integrity,
        "unfinished_history_hash": unfinished,
        "last_meta": last_meta,
        "codec_contexts": contexts,
    }
    return result, candidate
