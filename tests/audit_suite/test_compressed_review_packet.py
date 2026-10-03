"""Streamed complete journals, genuine original collections and strict privacy."""

import hashlib
import json
import struct
import subprocess
from pathlib import Path

import pytest

from enterprise.audit_suite.compressed_review_packet import export_packet, verify_packet
from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, write
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError, Store, canonical, digest
from tests.audit_suite.test_full_scope_company_pair import acquire

pytest_plugins = ["tests.audit_suite.test_full_scope_company_pair"]
REPO = Path(__file__).resolve().parents[2]


def _accept_runtime(pair, tmp_path):
    runtime = tmp_path / "NEUTRAL-RUNTIME.json"
    write(
        runtime,
        {
            "schema": RUNTIME_SCHEMA,
            "verdict": RUNTIME_VERDICT,
            "source_execution_authorized": True,
            "runtime_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/persistent_company_journey.py"
            ),
            "adapter_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/source_library_audit.py"
            ),
            "accepted_baseline_pins": pair.world.pins,
            "engineering_fixture_not_actual_independent_acceptance": True,
        },
    )
    pair.world.accept_runtime(runtime, file_sha(runtime))


def test_company_before_two409_ordinary_originals_complete_stream_and_standalone_cli(
    pair, tmp_path
):
    _accept_runtime(pair, tmp_path)
    for mode, room in pair.rooms.items():
        assert len(acquire(room)) == 1
        for index in range(80):
            state = room.state()
            room.engine.command(
                room.auditor,
                room.engagement,
                {
                    "command_id": f"actual-{mode}-note-{index}",
                    "expected_revision": state["revision"],
                    "kind": "note.create",
                    "payload": {
                        "title": "Actual literal note",
                        "text": "Unredacted raw history: 雪😀=-0.0\n"
                        + ("actual journal text\n" * 950),
                    },
                },
            )
        current = room.state()
        original_sha = file_sha(room.engine.store.db_path)
        before = {p: file_sha(p) for p in room.engine.store.root.rglob("*") if p.is_file()}
        # These neighboring private members must never be copied by a directory export.
        excluded = room.engine.store.root / "PRIVATE-KEY-MARKER.txt"
        excluded.write_text("AUTHOR-PRIVATE-NEIGHBOR-DO-NOT-COPY")
        excluded.chmod(0o600)
        packet = export_packet(
            room.engine, room.operator, room.engagement, tmp_path / (mode + "-packet")
        )
        result = verify_packet(packet["path"], packet["manifest_sha256"])
        assert result["history_events"] == current["revision"] + 1
        assert packet["uncompressed_frame_bytes"] > 100 * 1024**2
        assert result["compressed_journal_bytes"] < packet["uncompressed_frame_bytes"] // 10
        assert len(current["tasks"]) == 409 and len(current["controls"]) == 70
        assert (Path(packet["path"]) / "engagement.json").read_bytes() == canonical(
            current
        ).encode()
        assert packet["identity_session_tables_copied"] is False
        assert packet["instructor_key_files_copied"] is False
        assert not (Path(packet["path"]) / "history.sqlite3").exists()
        assert not (Path(packet["path"]) / excluded.name).exists()
        assert file_sha(room.engine.store.db_path) == original_sha
        assert all(file_sha(path) == pin for path, pin in before.items())
        for item in packet["included_artifacts"]:
            assert file_sha(Path(packet["path"]) / "files" / item["sha256"]) == item["sha256"]
        cli = subprocess.run(
            [
                __import__("sys").executable,
                "-B",
                "-m",
                "enterprise.audit_suite.compressed_review_packet",
                packet["path"],
                packet["manifest_sha256"],
            ],
            check=True,
            capture_output=True,
        )
        assert json.loads(cli.stdout)["verified"] is True


@pytest.fixture
def packet(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "original")
    actor = store.provision("Original packet operator", ["instructor"])
    state = store.create(
        actor["id"],
        {
            "title": "Actual stored state",
            "mode": "CLEAN",
            "scope": {"soc2_categories": ["Security"]},
            "artifacts": [],
            "tasks": [],
            "count": 0,
        },
        "birth",
    )

    class Engine:
        pass

    engine = Engine()
    engine.store = store
    engine.artifacts = None
    selected = export_packet(engine, actor["id"], state["id"], tmp_path / "packet")
    return selected, tmp_path


def reseal(root, manifest):
    for name in manifest["files"]:
        manifest["files"][name] = file_sha(root / name)
    (root / "manifest.json").write_bytes((canonical(manifest) + "\n").encode())
    return file_sha(root / "manifest.json")


@pytest.mark.parametrize(
    "case",
    [
        "bool_revision",
        "bool_count",
        "selected_bool",
        "grade",
        "extra_file",
        "missing_history",
        "source_bytes",
    ],
)
def test_fully_resealed_packet_changes_refuse_without_typed_equality_or_unknown_members(
    packet, case
):
    selected, _ = packet
    root = Path(selected["path"])
    manifest = json.loads((root / "manifest.json").read_bytes())
    if case == "bool_revision":
        manifest["revision"] = False
    elif case == "bool_count":
        manifest["history_events"] = True
    elif case == "selected_bool":
        state = json.loads((root / "engagement.json").read_bytes())
        state["count"] = False
        (root / "engagement.json").write_bytes(canonical(state).encode())
        manifest["state_sha256"] = digest(state)
        manifest["selected_raw_sha256"] = hashlib.sha256(
            (root / "engagement.json").read_bytes()
        ).hexdigest()
    elif case == "grade":
        manifest["overall_grade"] = "PASS"
    elif case == "extra_file":
        write(root / "principals.json", {"name": "Neighbor auth table"})
    elif case == "missing_history":
        (root / "history.frames.zst").write_bytes(b"")
    elif case == "source_bytes":
        (root / "history.frames.zst").write_bytes((root / "history.frames.zst").read_bytes()[:-1])
    pin = reseal(root, manifest)
    with pytest.raises(DomainError):
        verify_packet(root, pin)


@pytest.mark.parametrize(
    "case",
    [
        "metadata_json",
        "raw_state_json",
        "raw_command_json",
        "frame_revision_bool",
        "future_real_clock",
        "foreign_room",
        "native_version_bool",
        "source_list",
        "trailing_frame",
        "selected_nonobject",
        "unknown_compression",
        "symlink",
    ],
)
def test_resealed_exact_raw_frame_and_private_members_refuse(packet, case):
    selected, _ = packet
    root = Path(selected["path"])
    manifest = json.loads((root / "manifest.json").read_bytes())
    if case == "symlink":
        member = root / "engagement.json"
        original = root.parent / "owned-selected.json"
        member.rename(original)
        member.symlink_to(original)
        pin = reseal(root, manifest)
    elif case == "unknown_compression":
        manifest["compression"]["algorithm"] = "OTHER"
        pin = reseal(root, manifest)
    elif case == "selected_nonobject":
        (root / "engagement.json").write_bytes(b"[]")
        pin = reseal(root, manifest)
    else:
        magic = b"SH_COMPLETE_RAW_AUDIT_EVENTS_V1\n"
        wire = subprocess.run(
            ["/usr/bin/zstd", "-q", "-d", "--long=30", str(root / "history.frames.zst"), "-c"],
            check=True,
            capture_output=True,
        ).stdout
        lengths = struct.Struct(">QQQ")
        nm, ns, nc = lengths.unpack(wire[len(magic) : len(magic) + lengths.size])
        offset = len(magic) + lengths.size
        metadata_raw = wire[offset : offset + nm]
        state_raw = wire[offset + nm : offset + nm + ns]
        command_raw = wire[offset + nm + ns : offset + nm + ns + nc]
        metadata, state, command = map(json.loads, (metadata_raw, state_raw, command_raw))
        if case == "frame_revision_bool":
            metadata["revision"] = False
        elif case == "future_real_clock":
            metadata["recorded_at"] += 10**10
        elif case == "foreign_room":
            state["id"] = "FOREIGN-ENGAGEMENT"
        elif case in {"native_version_bool", "source_list"}:
            state["artifacts"] = [
                {
                    "id": "OWNED-DECLARED-ORIGINAL",
                    "engagement_id": state["id"],
                    "name": "original.json",
                    "bytes": 0,
                    "sha256": "e" * 64,
                    "status": "AVAILABLE",
                    "source": []
                    if case == "source_list"
                    else {
                        "kind": "COLLECTED_COMPANY_SOURCE",
                        "receipt": {
                            "source": {"version": True, "sha256": "e" * 64},
                            "content_bytes": 0,
                            "engagement_id": state["id"],
                        },
                    },
                }
            ]
        record = {k: metadata[k] for k in ("actor", "recorded_at", "previous_hash", "command_id")}
        record |= {"state": state, "command": command}
        metadata["hash"], metadata["request_hash"] = digest(record), digest(command)
        metadata_raw, state_raw, command_raw = map(
            lambda x: canonical(x).encode(), (metadata, state, command)
        )
        if case == "metadata_json":
            metadata_raw = b"["
        elif case == "raw_state_json":
            state_raw = b"["
        elif case == "raw_command_json":
            command_raw = b"["
        rebuilt = magic + lengths.pack(len(metadata_raw), len(state_raw), len(command_raw))
        rebuilt += metadata_raw + state_raw + command_raw + lengths.pack(0, 0, 0)
        if case == "trailing_frame":
            rebuilt += b"UNREGISTERED-BYTES"
        compressed = subprocess.run(
            ["/usr/bin/zstd", "-q", "-T1", "-3", "--long=30", "-c"],
            input=rebuilt,
            check=True,
            capture_output=True,
        ).stdout
        (root / "history.frames.zst").write_bytes(compressed)
        # Fully repair intrinsic event/request/public hashes and selected state;
        # intrinsic type/privacy predicates must still reject these inputs.
        (root / "engagement.json").write_bytes(canonical(state).encode())
        manifest["state_sha256"] = digest(state)
        manifest["selected_raw_sha256"] = hashlib.sha256(
            (root / "engagement.json").read_bytes()
        ).hexdigest()
        manifest["history_terminal_event_sha256"] = metadata["hash"]
        manifest["history_sha256"] = digest(
            [record | {"hash": metadata["hash"], "revision": metadata["revision"]}]
        )
        manifest["uncompressed_frame_bytes"] = len(rebuilt)
        pin = reseal(root, manifest)
    with pytest.raises(DomainError):
        verify_packet(root, pin)


@pytest.mark.parametrize("change", ["source_original", "operator_revoke", "packet_original"])
def test_real_ordinary_original_and_current_authority_close_before_delivery(
    pair, tmp_path, monkeypatch, change
):
    from enterprise.audit_suite import compressed_review_packet as module

    _accept_runtime(pair, tmp_path)
    room = pair.rooms["CLEAN"]
    assert len(acquire(room)) == 1
    artifact = room.state()["artifacts"][0]
    original = room.engine.artifacts.root / artifact["sha256"]
    if change == "packet_original":
        selected = export_packet(room.engine, room.operator, room.engagement, tmp_path / "positive")
        member = Path(selected["path"]) / "files" / artifact["sha256"]
        digest_file = module.file_digest
        mutated = False

        def late_read(path):
            nonlocal mutated
            result = digest_file(path)
            if Path(path) == member and not mutated:
                member.write_bytes(member.read_bytes()[:-1] + b"X")
                mutated = True
            return result

        monkeypatch.setattr(module, "file_digest", late_read)
        with pytest.raises(DomainError):
            verify_packet(selected["path"], selected["manifest_sha256"])
        assert mutated
    else:
        verifier = module.verify_packet

        def late_verification(*args, **kwargs):
            result = verifier(*args, **kwargs)
            if change == "operator_revoke":
                room.engine.store.revoke(room.operator)
            else:
                original.write_bytes(original.read_bytes()[:-1] + b"X")
            return result

        monkeypatch.setattr(module, "verify_packet", late_verification)
        with pytest.raises(DomainError):
            export_packet(room.engine, room.operator, room.engagement, tmp_path / "refused")
        assert not (tmp_path / "refused").exists()
        assert (
            room.engine.store.get(room.auditor, room.engagement)["revision"]
            == room.state()["revision"]
        )
