"""Opt-in complete private packet streamed directly into compressed event frames.

No writable full-journal SQLite or full extraction is needed. Explicit original
event state/command bytes and user-authored text remain unchanged. This excludes
identity/session tables and neighboring private Key/signing files; it cannot
promise arbitrary user-authored audit text contains no secrets. The original
SQLite packet format remains unchanged in retained_review_packet.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import struct
import subprocess
import time
import uuid
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _time
from .history_inspection import _stamp
from .private_publication import publish
from .retained_review_packet import _artifacts, _index, _parent, file_digest
from .serialized_json import canonical_bytes, canonical_projection, update_object
from .source_library_audit import private_file
from .store import DomainError, canonical, digest

SCHEMA = "SH_PRIVATE_COMPLETE_COMPRESSED_EVENT_PACKET_V1"
FORMAT = "EXACT_RAW_EVENT_FRAMES_ZSTD_V1"
MAGIC = b"SH_COMPLETE_RAW_AUDIT_EVENTS_V1\n"
LENGTHS = struct.Struct(">QQQ")
META = {"revision", "actor", "recorded_at", "previous_hash", "command_id", "hash", "request_hash"}
MAX_STATE, MAX_COMMAND, MAX_META = 2 * 1024**3, 16 * 1024**2, 65536
FLAGS = {
    "identity_session_tables_copied": False,
    "instructor_key_files_copied": False,
    "source_company_write": False,
    "audit_event_write": False,
    "professional_acceptance": "NOT_ASSERTED",
    "overall_grade": "NOT_PROVIDED",
}
PARAMETERS = ["-q", "-T1", "-3", "--long=30"]


def require(condition, message):
    if not condition:
        raise DomainError(message, code="INTEGRITY", status=503)


def _json(raw):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DomainError("Malformed packet JSON", code="INTEGRITY", status=503) from error


def _canonical(raw, fields=None):
    try:
        return (
            canonical_bytes(raw.decode())
            if fields is None
            else canonical_projection(raw.decode(), fields)
        )
    except (ValueError, UnicodeError, RecursionError, TypeError) as error:
        raise DomainError(
            "Malformed original canonical JSON", code="INTEGRITY", status=503
        ) from error


def _tool(path):
    path = Path(path).absolute()
    before = path.stat()
    require(
        path == path.resolve()
        and not any(x.is_symlink() for x in [path, *path.parents])
        and stat.S_ISREG(before.st_mode)
        and before.st_nlink == 1,
        "Ordinary unaliased compression executable required",
    )
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    version = (
        subprocess.run([str(path), "--version"], check=True, capture_output=True, timeout=10)
        .stdout.decode()
        .strip()
    )
    after = path.stat()
    require(
        all(
            getattr(before, k) == getattr(after, k)
            for k in (
                "st_dev",
                "st_ino",
                "st_size",
                "st_mode",
                "st_nlink",
                "st_mtime_ns",
                "st_ctime_ns",
            )
        ),
        "Compression executable changed",
    )
    return {"sha256": sha, "bytes": before.st_size, "version": version}


@contextmanager
def _pipe(path, pin, member, *, writing):
    require(_tool(path) == pin, "Compression implementation differs from explicit pin")
    private_file(member)
    with Path(member).open("wb" if writing else "rb") as file:
        process = subprocess.Popen(
            [str(path), *PARAMETERS] if writing else [str(path), "-q", "-d", "--long=30"],
            stdin=subprocess.PIPE if writing else file,
            stdout=file if writing else subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        stream = process.stdin if writing else process.stdout
        try:
            yield stream
            stream.close()
            require(process.wait() == 0, "Complete compressed frame stream failed")
            if writing:
                file.flush()
                os.fsync(file.fileno())
            require(_tool(path) == pin, "Compression implementation changed during stream")
        finally:
            stream.close()
            if process.poll() is None:
                process.terminate()
                process.wait()


def _read(stream, size):
    result = bytearray()
    while len(result) < size:
        raw = stream.read(min(size - len(result), 1024 * 1024))
        require(bool(raw), "Truncated complete event frame")
        result.extend(raw)
    return bytes(result)


def _frames(stream):
    require(_read(stream, len(MAGIC)) == MAGIC, "Exact compressed journal magic required")
    while True:
        metadata, state, command = LENGTHS.unpack(_read(stream, LENGTHS.size))
        if (metadata, state, command) == (0, 0, 0):
            require(stream.read(1) == b"", "Unregistered trailing compressed journal bytes")
            return
        require(
            0 < metadata <= MAX_META and 0 < state <= MAX_STATE and 0 < command <= MAX_COMMAND,
            "Explicit bounded complete event frame lengths required",
        )
        raw = _read(stream, metadata)
        value = _json(raw)
        require(
            type(value) is dict and set(value) == META and canonical(value).encode() == raw,
            "Exact canonical event metadata fields required",
        )
        yield value, _read(stream, state), _read(stream, command)


def _checked(metadata, raw_state, raw_command, revision, previous, engagement, scope):
    require(
        type(metadata["revision"]) is int
        and metadata["revision"] == revision
        and metadata["previous_hash"] == previous
        and type(metadata["recorded_at"]) in (int, float)
        and math.isfinite(metadata["recorded_at"])
        and metadata["recorded_at"] > 0
        and metadata["recorded_at"] <= time.time()
        and type(metadata["actor"]) is str
        and 1 <= len(metadata["actor"]) <= 128
        and type(metadata["command_id"]) is str
        and 1 <= len(metadata["command_id"]) <= 128
        and all(
            type(metadata[k]) is str and re.fullmatch(r"[a-f0-9]{64}", metadata[k])
            for k in ("hash", "request_hash")
        ),
        "Typed original event metadata required",
    )
    state_bytes, state = _canonical(
        raw_state,
        ("id", "revision", "artifacts", "scope", "simulated_at", "mode", "company_source_binding"),
    )
    command_bytes = _canonical(raw_command)
    require(
        type(state) is dict
        and type(state.get("revision")) is int
        and state["revision"] == revision
        and state.get("id") == engagement,
        "Exact typed selected-engagement event state required",
    )
    state_scope = digest(state.get("scope"))
    require(scope is None or state_scope == scope, "Recorded retained scope changed")
    fields = {
        k: canonical(metadata[k]).encode()
        for k in ("actor", "recorded_at", "previous_hash", "command_id")
    }
    fields |= {"state": state_bytes, "command": command_bytes}
    event_hash = hashlib.sha256()
    update_object(event_hash, fields)
    require(
        event_hash.hexdigest() == metadata["hash"]
        and hashlib.sha256(command_bytes).hexdigest() == metadata["request_hash"],
        "Complete original event/request hash disagreement",
    )
    return fields, state, state_scope


def _inventory(registry, state, revision, recorded_at):
    seen = set()
    require(type(state.get("artifacts")) is list, "Original artifact inventory required")
    for item in state["artifacts"]:
        require(
            type(item) is dict and type(item.get("id")) is str and item["id"] not in seen,
            "Unique historical artifact identities required",
        )
        seen.add(item["id"])
        require(
            type(item.get("bytes")) is int and item["bytes"] >= 0,
            "Strict original artifact byte count required",
        )
        source = item.get("source", {})
        require(type(source) is dict, "Typed original source declaration required")
        if source.get("kind") == "COLLECTED_COMPANY_SOURCE":
            receipt = source.get("receipt")
            native = None if type(receipt) is not dict else receipt.get("source")
            binding = state.get("company_source_binding")
            require(
                type(native) is dict
                and type(binding) is dict
                and all(type(binding.get(k)) is str and binding[k] for k in ("company", "branch"))
                and all(
                    native.get(k) == binding[k]
                    for k in binding
                    if k in {"company", "branch", "system", "record", "origin"}
                )
                and type(native.get("version")) is int
                and native["version"] > 0
                and type(receipt.get("content_bytes")) is int
                and receipt["content_bytes"] == item["bytes"]
                and native.get("sha256") == item.get("sha256")
                and receipt.get("engagement_id") == state["id"]
                and all(
                    type(native.get(k)) is str and native[k]
                    for k in ("company", "branch", "system", "record")
                )
                and all(
                    type(receipt.get(k)) is str and receipt[k]
                    for k in ("command_id", "principal_id")
                )
                and _time(native.get("available_at")) >= _time(native.get("event_at"))
                and _time(native.get("available_at"))
                <= _time(receipt.get("simulated_as_of"))
                <= _time(state.get("simulated_at"))
                and _time(native.get("imported_at"))
                <= _time(receipt.get("collected_at"))
                <= _time(datetime.fromtimestamp(recorded_at, UTC).isoformat()),
                "Typed declared original collection custody required",
            )
        old = registry.get(item["id"])
        if old is not None:
            require(
                all(old["item"].get(k) == item.get(k) for k in ("sha256", "bytes", "engagement_id"))
                and digest(old["item"].get("source", {})) == digest(source),
                "Historical original artifact identity changed",
            )
        registry[item["id"]] = {
            "item": item,
            "first_revision": revision if old is None else old["first_revision"],
            "last_revision": revision,
        }


def _chronology(state, previous):
    """Intrinsic documentary clocks/bindings; no external company authority claim."""
    if "simulated_at" in state:
        clock = state["simulated_at"]
        require(type(clock) is str, "Typed simulated documentary clock required")
        clock = _time(clock)
        require(
            previous.get("simulated_at", clock) <= clock,
            "Simulated documentary clock moved backwards",
        )
        previous["simulated_at"] = clock
    else:
        require("simulated_at" not in previous, "Simulated documentary clock disappeared")
    if "mode" in state:
        require(
            type(state["mode"]) is str and state["mode"] in {"CLEAN", "MESSY"},
            "Typed paired-workroom mode required",
        )
        require(previous.get("mode", state["mode"]) == state["mode"], "Workroom mode changed")
        previous["mode"] = state["mode"]
    else:
        require("mode" not in previous, "Workroom mode disappeared")
    binding = state.get("company_source_binding")
    require(binding is None or type(binding) is dict, "Typed native company binding required")
    if binding is not None:
        signature = digest(binding)
        require(previous.get("binding", signature) == signature, "Native company binding changed")
        previous["binding"] = signature
    else:
        require("binding" not in previous, "Activated native company binding disappeared")


def _listed(registry, engagement):
    # Latest known quarantine/recursive status remains explicit. An original
    # absent from current state is still indexed from its actual historical row.
    universe = {"artifacts": [value["item"] for value in registry.values()]}
    return _artifacts(universe, engagement)


def _html(state, included, withheld):
    return (
        _index(state, included, withheld)
        .decode()
        .replace("history.sqlite3", "history.frames.zst")
        .replace(
            "SQLite database, not an abbreviated history.json", "lossless compressed frame stream"
        )
        .replace("Complete immutable event journal", "Complete compressed event journal")
    ).encode()


def _write(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _file_identity(path):
    private_file(path)
    value = path.stat()
    return tuple(
        getattr(value, key)
        for key in (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mode",
            "st_nlink",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    )


def export_packet(
    engine, actor, engagement_id, output, *, retained_room=None, zstd_path="/usr/bin/zstd"
):
    """Export exact original event fields without any giant writable journal copy."""
    if retained_room is not None:
        require(
            retained_room.engine is engine and retained_room.engagement == engagement_id,
            "Exact retained packet workroom required",
        )
        retained_room.refresh_integrity(actor)
    require(
        engine.store.membership(actor, engagement_id) == "instruct",
        "Instructor membership required",
    )
    output = _parent(output, engine.store.root)
    stage = output.parent / ("." + output.name + "-staging-" + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    (stage / "files").mkdir(mode=0o700)
    compressed = stage / "history.frames.zst"
    _write(compressed, b"")
    tool = _tool(zstd_path)
    rolling, previous, count, scope, registry, raw_bytes = hashlib.sha256(b"["), "", 0, None, {}, 0
    commands, recorded_at, chronology = set(), 0, {}
    outside = _stamp(engine.store.db_path)
    with closing(engine.store.connect()) as source:
        source.execute("BEGIN IMMEDIATE")
        source.execute("PRAGMA query_only=ON")
        inside = _stamp(engine.store.db_path)
        engine.store._authorize(source, actor, engagement_id, {"instruct"})
        current = source.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        require(current is not None, "Selected workroom required")
        current_raw = current["state"].encode()
        with _pipe(zstd_path, tool, compressed, writing=True) as stream:
            stream.write(MAGIC)
            for row in source.execute(
                "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement_id,)
            ):
                metadata = {k: row[k] for k in META}
                state_raw, command_raw = row["state"].encode(), row["command"].encode()
                fields, projected, scope = _checked(
                    metadata, state_raw, command_raw, count, previous, engagement_id, scope
                )
                require(
                    metadata["command_id"] not in commands
                    and metadata["recorded_at"] >= recorded_at,
                    "Unique ordered original commands and clocks required",
                )
                commands.add(metadata["command_id"])
                recorded_at = metadata["recorded_at"]
                _chronology(projected, chronology)
                _inventory(registry, projected, count, metadata["recorded_at"])
                header = canonical(metadata).encode()
                require(
                    len(header) <= MAX_META
                    and len(state_raw) <= MAX_STATE
                    and len(command_raw) <= MAX_COMMAND,
                    "Export event frame exceeds explicit bounds",
                )
                stream.write(LENGTHS.pack(len(header), len(state_raw), len(command_raw)))
                stream.write(header)
                stream.write(state_raw)
                stream.write(command_raw)
                raw_bytes += LENGTHS.size + len(header) + len(state_raw) + len(command_raw)
                if count:
                    rolling.update(b",")
                update_object(
                    rolling,
                    fields
                    | {
                        "hash": canonical(metadata["hash"]).encode(),
                        "revision": canonical(count).encode(),
                    },
                )
                previous, latest_raw, count = metadata["hash"], state_raw, count + 1
            stream.write(LENGTHS.pack(0, 0, 0))
        require(
            count == current["revision"] + 1 and _canonical(latest_raw) == _canonical(current_raw),
            "Exact typed terminal/current canonical bytes differ",
        )
        state = _json(current_raw)
        require(
            type(state["revision"]) is int and state["revision"] == count - 1,
            "Typed current revision required",
        )
        _write(stage / "engagement.json", current_raw)
        included, withheld = _listed(registry, engagement_id)
        copied, originals = set(), {}
        for item in included:
            source_path = engine.artifacts.root / item["sha256"]
            identity = _file_identity(source_path)
            raw = engine.artifacts.read(registry[item["id"]]["item"])
            require(_file_identity(source_path) == identity, "Original changed during packet read")
            originals[source_path] = (identity, item["sha256"])
            if item["sha256"] not in copied:
                _write(stage / "files" / item["sha256"], raw)
                copied.add(item["sha256"])
        _write(stage / "index.html", _html(state, included, withheld))
        engine.store._authorize(source, actor, engagement_id, {"instruct"})
        require(_stamp(engine.store.db_path) == inside, "Audit changed during complete compression")
    require(_stamp(engine.store.db_path) == outside, "Audit changed during export closure")
    if retained_room is not None:
        retained_room.refresh_integrity(actor)
    rolling.update(b"]")
    files = {
        p.relative_to(stage).as_posix(): file_digest(p) for p in stage.rglob("*") if p.is_file()
    }
    manifest = {
        "schema": SCHEMA,
        "audience": "INSTRUCTOR_ONLY",
        "history_format": FORMAT,
        "engagement_id": engagement_id,
        "revision": state["revision"],
        "state_sha256": digest(state),
        "selected_raw_sha256": hashlib.sha256(current_raw).hexdigest(),
        "history_events": count,
        "history_sha256": rolling.hexdigest(),
        "history_terminal_event_sha256": previous,
        "uncompressed_frame_bytes": raw_bytes + len(MAGIC) + LENGTHS.size,
        "compression": {"algorithm": "ZSTD", "parameters": PARAMETERS, "executable": tool},
        "files": files,
        "included_artifacts": included,
        "omitted_artifacts": withheld,
        "historical_artifact_occurrences": {
            k: {n: v[n] for n in ("first_revision", "last_revision")} for k, v in registry.items()
        },
        **FLAGS,
    }
    _write(stage / "manifest.json", (canonical(manifest) + "\n").encode())
    pin = file_digest(stage / "manifest.json")
    # Fully verify staged output and fresh authority before any publication.
    verify_packet(stage, pin, zstd_path=zstd_path)
    if retained_room is not None:
        # Staged verification can take time. Close over the exact validated
        # history again, including every native and historical retained file.
        retained_room.close_protected_read(actor, retained_room.integrity_stamp())
    with closing(engine.store.connect()) as source:
        source.execute("BEGIN IMMEDIATE")
        engine.store._authorize(source, actor, engagement_id, {"instruct"})
        latest = source.execute(
            "SELECT revision,state FROM engagements WHERE id=?", (engagement_id,)
        ).fetchone()
        require(
            latest["revision"] == current["revision"] and latest["state"].encode() == current_raw,
            "Selected audit changed before packet publication",
        )
        if retained_room is not None:
            retained_room.check_pins()
            engine.store.check_prefix()
        for path, (identity, sha) in originals.items():
            require(
                _file_identity(path) == identity
                and file_digest(path) == sha
                and _file_identity(path) == identity,
                "Retained original changed before complete packet publication",
            )
        publish(stage, output)
    return {"path": str(output), "manifest_sha256": pin, **manifest}


def verify_packet(path, expected_manifest_sha256, *, zstd_path="/usr/bin/zstd"):
    """Fail closed with a bounded domain refusal for malformed private inputs."""
    try:
        return _verify_packet(path, expected_manifest_sha256, zstd_path=zstd_path)
    except (
        OSError,
        ValueError,
        UnicodeError,
        RecursionError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ) as error:
        raise DomainError(
            "Malformed or unavailable complete packet", code="INTEGRITY", status=503
        ) from error


def _verify_packet(path, expected_manifest_sha256, *, zstd_path="/usr/bin/zstd"):
    """Standalone immutable streaming verification, with no Store or extraction."""
    root = Path(path).absolute()
    require(
        root == root.resolve()
        and not any(p.is_symlink() for p in [root, *root.parents])
        and root.is_dir()
        and stat.S_IMODE(root.stat().st_mode) == 0o700,
        "Private ordinary packet directory required",
    )
    require(
        type(expected_manifest_sha256) is str
        and re.fullmatch(r"[a-f0-9]{64}", expected_manifest_sha256)
        and file_digest(root / "manifest.json") == expected_manifest_sha256,
        "External exact packet manifest pin required",
    )
    manifest = _json((root / "manifest.json").read_bytes())
    keys = {
        "schema",
        "audience",
        "history_format",
        "engagement_id",
        "revision",
        "state_sha256",
        "selected_raw_sha256",
        "history_events",
        "history_sha256",
        "history_terminal_event_sha256",
        "uncompressed_frame_bytes",
        "compression",
        "files",
        "included_artifacts",
        "omitted_artifacts",
        "historical_artifact_occurrences",
    } | set(FLAGS)
    require(
        type(manifest) is dict
        and set(manifest) == keys
        and manifest["schema"] == SCHEMA
        and manifest["audience"] == "INSTRUCTOR_ONLY"
        and manifest["history_format"] == FORMAT
        and all(type(manifest[k]) is type(v) and manifest[k] == v for k, v in FLAGS.items())
        and type(manifest["revision"]) is int
        and manifest["revision"] >= 0
        and type(manifest["history_events"]) is int
        and manifest["history_events"] == manifest["revision"] + 1
        and type(manifest["uncompressed_frame_bytes"]) is int
        and manifest["uncompressed_frame_bytes"] > 0,
        "Exclusive typed compressed packet schema required",
    )
    compression = manifest["compression"]
    require(
        type(compression) is dict
        and set(compression) == {"algorithm", "parameters", "executable"}
        and compression["algorithm"] == "ZSTD"
        and compression["parameters"] == PARAMETERS,
        "Exact compression contract required",
    )
    require(
        type(manifest["files"]) is dict
        and {"engagement.json", "index.html", "history.frames.zst"} <= set(manifest["files"])
        and all(
            type(k) is str
            and (
                k in {"engagement.json", "index.html", "history.frames.zst"}
                or re.fullmatch(r"files/[a-f0-9]{64}", k)
            )
            and type(v) is str
            and re.fullmatch(r"[a-f0-9]{64}", v)
            for k, v in manifest["files"].items()
        ),
        "Exact packet file names and hashes required",
    )
    members = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        folder = Path(directory)
        require(stat.S_IMODE(folder.stat().st_mode) == 0o700, "Private packet directory required")
        for name in dirs:
            require(
                folder / name == root / "files" and not (folder / name).is_symlink(),
                "Unknown packet directory",
            )
        for name in files:
            member = folder / name
            private_file(member)
            members.add(member.relative_to(root).as_posix())
    require(
        members == set(manifest["files"]) | {"manifest.json"},
        "Exact closed packet membership required",
    )
    for name, pin in manifest["files"].items():
        require(file_digest(root / name) == pin, "Packet member digest differs")
    require(
        0 < (root / "engagement.json").stat().st_size <= MAX_STATE,
        "Bounded complete selected state required",
    )
    selected_raw = (root / "engagement.json").read_bytes()
    selected = _json(selected_raw)
    require(
        type(selected) is dict
        and type(selected.get("id")) is str
        and selected["id"] == manifest["engagement_id"]
        and type(selected.get("revision")) is int
        and selected["revision"] == manifest["revision"]
        and digest(selected) == manifest["state_sha256"]
        and hashlib.sha256(selected_raw).hexdigest() == manifest["selected_raw_sha256"],
        "Exact typed selected state required",
    )
    rolling, previous, count, scope, registry = hashlib.sha256(b"["), "", 0, None, {}
    commands, recorded_at, terminal, chronology = set(), 0, None, {}
    raw_bytes = len(MAGIC) + LENGTHS.size
    with _pipe(
        zstd_path, compression["executable"], root / "history.frames.zst", writing=False
    ) as stream:
        for metadata, state_raw, command_raw in _frames(stream):
            fields, projected, scope = _checked(
                metadata, state_raw, command_raw, count, previous, manifest["engagement_id"], scope
            )
            require(
                metadata["command_id"] not in commands and metadata["recorded_at"] >= recorded_at,
                "Unique ordered original commands and clocks required",
            )
            commands.add(metadata["command_id"])
            recorded_at = metadata["recorded_at"]
            _chronology(projected, chronology)
            _inventory(registry, projected, count, metadata["recorded_at"])
            raw_bytes += (
                LENGTHS.size + len(canonical(metadata).encode()) + len(state_raw) + len(command_raw)
            )
            if count:
                rolling.update(b",")
            update_object(
                rolling,
                fields
                | {
                    "hash": canonical(metadata["hash"]).encode(),
                    "revision": canonical(count).encode(),
                },
            )
            previous, terminal, count = metadata["hash"], fields["state"], count + 1
    rolling.update(b"]")
    require(
        count == manifest["history_events"]
        and previous == manifest["history_terminal_event_sha256"]
        and rolling.hexdigest() == manifest["history_sha256"]
        and raw_bytes == manifest["uncompressed_frame_bytes"]
        and terminal == _canonical(selected_raw),
        "Complete terminal/selected typed bytes or history boundary differs",
    )
    included, withheld = _listed(registry, manifest["engagement_id"])
    occurrence = {
        k: {n: v[n] for n in ("first_revision", "last_revision")} for k, v in registry.items()
    }
    require(
        canonical(occurrence) == canonical(manifest["historical_artifact_occurrences"])
        and canonical(included) == canonical(manifest["included_artifacts"])
        and canonical(withheld) == canonical(manifest["omitted_artifacts"]),
        "Exact all-history original membership required",
    )
    names = {"engagement.json", "index.html", "history.frames.zst"} | {
        "files/" + x["sha256"] for x in included
    }
    require(
        set(manifest["files"]) == names
        and (root / "index.html").read_bytes() == _html(selected, included, withheld),
        "Exact complete packet originals and offline index required",
    )
    for item in included:
        require(
            (root / "files" / item["sha256"]).stat().st_size == item["bytes"],
            "Original byte size differs",
        )
    require(
        file_digest(root / "manifest.json") == expected_manifest_sha256,
        "Manifest changed during verification",
    )
    for name, pin in manifest["files"].items():
        require(file_digest(root / name) == pin, "Member changed during verification")
    return {
        "verified": True,
        "engagement_id": selected["id"],
        "revision": selected["revision"],
        "history_events": count,
        "uncompressed_frame_bytes": raw_bytes,
        "compressed_journal_bytes": (root / "history.frames.zst").stat().st_size,
        "manifest_sha256": expected_manifest_sha256,
        "extraction_required": False,
        "source_company_write": False,
        "audit_event_write": False,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Stream-verify a complete compressed private audit packet"
    )
    parser.add_argument("packet", type=Path)
    parser.add_argument("manifest_sha256")
    parser.add_argument("--zstd", default="/usr/bin/zstd")
    arguments = parser.parse_args()
    print(
        canonical(
            verify_packet(arguments.packet, arguments.manifest_sha256, zstd_path=arguments.zstd)
        )
    )
