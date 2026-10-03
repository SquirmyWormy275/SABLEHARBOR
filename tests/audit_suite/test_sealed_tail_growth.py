"""Measured ordinary action growth; this is no actual-company scale claim."""

import json
import os
import time
from pathlib import Path

import pytest

from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, write
from enterprise.audit_suite.persistent_company_service import (
    configuration,
    create_retained_app,
    sealed_configuration,
)
from enterprise.audit_suite.sealed_history_store import prepare_tail
from enterprise.audit_suite.source_library_audit import file_sha
from tests.audit_suite.test_full_scope_company_pair import acquire

pytest_plugins = ["tests.audit_suite.test_full_scope_company_pair"]
REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("state_codec", [False, True])
def test_one_and_one_hundred_ordinary_fullscope_notes_report_exact_tail_growth(
    pair, tmp_path, state_codec
):
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
    room = pair.rooms["CLEAN"]
    assert len(acquire(room)) == 1
    prefix_sha = file_sha(room.engine.store.db_path)
    selected = prepare_tail(
        room.engine.store, room.operator, room.engagement, tmp_path / "measured-tail",
        state_codec=state_codec,
    )
    binding = room.root / "BINDING.json"
    values = configuration(pair.world, binding, file_sha(binding), repository=REPO)
    values = sealed_configuration(
        values,
        selected,
        json.loads(Path(selected["path"]).read_bytes())["initial_authority_head"],
        repository=REPO,
    )
    config = tmp_path / "CONFIG.json"
    write(config, values)
    started = time.perf_counter()
    app = create_retained_app(room.engine.store.root, config, file_sha(config), repository=REPO)
    constructor = time.perf_counter() - started
    store = app.state.engine.store

    def measured():
        with store.connect() as db:
            state_bytes = db.execute(
                "SELECT length(CAST(state AS BLOB)) FROM engagements"
            ).fetchone()[0]
            state = json.loads(db.execute("SELECT state FROM engagements").fetchone()[0])
            events = db.execute("SELECT COUNT(*) FROM event_tail").fetchone()[0]
        members = [store.db_path, *(Path(str(store.db_path) + x) for x in ("-wal", "-shm"))]
        filesystem = os.statvfs(store.db_path.parent)
        return {
            "tail_file_and_sidecar_logical_bytes": sum(
                p.stat().st_size for p in members if p.exists()
            ),
            "current_state_canonical_bytes": state_bytes,
            "tail_events": events,
            "revision": state["revision"],
            "filesystem_available_bytes": filesystem.f_bavail * filesystem.f_frsize,
        }

    steps = {"initial": measured()}
    command_seconds = []
    refresh_seconds = {}
    for index in range(1, 101):
        state = store.get(room.auditor, room.engagement)
        started = time.perf_counter()
        after = app.state.engine.command(
            room.auditor,
            room.engagement,
            {
                "command_id": "ordinary-growth-note-" + str(index),
                "kind": "note.create",
                "expected_revision": state["revision"],
                "payload": {
                    "title": "Engineering growth note " + str(index),
                    "text": "Measured ordinary action; no audit outcome. " + "x" * 1024,
                },
            },
        )
        command_seconds.append(time.perf_counter() - started)
        assert after["revision"] == state["revision"] + 1
        if index in (1, 100):
            steps[str(index)] = measured()
            started = time.perf_counter()
            app.state.retained_workroom.refresh_integrity(room.auditor)
            refresh_seconds[str(index)] = time.perf_counter() - started
    assert steps["100"]["tail_events"] == 100
    assert all(t["conclusion"] == "NOT_RUN" for t in after["tasks"])
    assert len(after["tasks"]) == 409 and len(after["controls"]) == 70
    assert file_sha(room.engine.store.db_path) == prefix_sha
    write(
        tmp_path / "WRITE_GROWTH.json",
        {
            "schema": "SH_ENGINEERING_SEALED_FULL_STATE_TAIL_GROWTH_V1",
            "engineering_neutral_only": True,
            "actual_company_opened": False,
            "events_are_genuine_ordinary_note_commands": True,
            "tail_codec": "EXACT_CANONICAL_FRAGMENT_STATE" if state_codec
            else "ORIGINAL_FULL_CANONICAL_EVENT_STATE",
            "constructor_seconds": constructor,
            "command_seconds": command_seconds,
            "command_timing_excludes_http_and_retained_private_guard": True,
            "typed_complete_refresh_seconds": refresh_seconds,
            "measurements": steps,
            "prefix_sha256_before_and_after": prefix_sha,
            "filesystem_available_delta_is_shared_and_not_dedicated_physical_allocation": True,
            "stat_blocks_not_used_for_encoded_btrfs_physical_capacity": True,
            "actual_scale_action_growth_and_packet_usability": "NOT_ACCEPTED_OR_MEASURED",
        },
    )
