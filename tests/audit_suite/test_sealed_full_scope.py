"""One neutral company before two real 409-task rooms; no imported outcomes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.history_inspection import inspect_history
from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, write
from enterprise.audit_suite.persistent_company_service import (
    SEALED_CODE_MODULES,
    configuration,
    create_retained_app,
    retained_native_files,
    sealed_configuration,
)
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
from enterprise.audit_suite.source_library_audit import file_sha
from tests.audit_suite.test_full_scope_company_pair import acquire

pytest_plugins = ["tests.audit_suite.test_full_scope_company_pair"]
REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("backend", ["native", "stdlib"])
@pytest.mark.parametrize("state_codec", [False, True])
def test_two409_ordinary_native_collections_tail_writes_clock_and_reopen(
    request, tmp_path, monkeypatch, backend, state_codec
):
    from enterprise.audit_suite import serialized_json

    if backend == "native":
        assert serialized_json._native is not None
    else:
        monkeypatch.setattr(serialized_json, "_native", None)
        from enterprise.audit_suite import canonical_state_codec

        monkeypatch.setattr(canonical_state_codec, "_fragmenter", None)
    pair = request.getfixturevalue("pair")
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
    identities = set()
    for mode, room in pair.rooms.items():
        acquired = acquire(room)
        assert len(acquired) == 1
        state = room.state()
        assert len(state["tasks"]) == 409 and len(state["controls"]) == 70
        prefix_sha = file_sha(room.engine.store.db_path)
        history = room.engine.store.history(room.operator, room.engagement)
        selected = prepare_tail(
            room.engine.store,
            room.operator,
            room.engagement,
            tmp_path / (mode + "-tail"),
            state_codec=state_codec,
        )
        standalone = SealedHistoryStore(
            room.engine.store.root, selected["path"], selected["sha256"]
        )
        access = {
            role: standalone.rotate_credential(person, lifetime=3600)
            for role, person in room.binding["identities"].items()
        }
        base = configuration(
            pair.world,
            room.root / "BINDING.json",
            file_sha(room.root / "BINDING.json"),
            repository=REPO,
        )
        config = tmp_path / (mode + "-CONFIG.json")
        values = sealed_configuration(base, selected, standalone.authority_head, repository=REPO)
        assert len(values["code_pins"]) == len(SEALED_CODE_MODULES) + len(
            retained_native_files(sealed=True)
        )
        assert len(values["authority_backend"]["origins"]) == 12
        write(config, values)
        app = create_retained_app(
            room.engine.store.root,
            config,
            file_sha(config),
            repository=REPO,
            allowed_hosts=["testserver"],
        )
        client = TestClient(app, base_url="https://testserver")
        logged = client.post("/api/session", json={"credential": access["auditor"]["credential"]})
        assert logged.status_code == 200, logged.text
        url = "/api/engagements/" + room.engagement
        after = client.post(
            url + "/commands",
            headers={"X-CSRF-Token": logged.json()["csrf_token"]},
            json={
                "command_id": "ordinary-tail-" + mode,
                "kind": "note.create",
                "expected_revision": state["revision"],
                "payload": {"title": "New exact tail", "text": "No audit credit."},
            },
        )
        assert after.status_code == 200, after.text
        app.state.retained_workroom.refresh_integrity(room.auditor)
        inspected = inspect_history(
            app.state.engine.store,
            room.auditor,
            room.engagement,
            revisions=[0, state["revision"], after.json()["revision"]],
        )
        assert inspected["count"] == len(history) + 1
        assert inspected["selected"][0] == history[0]
        assert inspected["selected"][state["revision"]] == history[-1]
        assert len(after.json()["tasks"]) == 409
        assert all(t["conclusion"] == "NOT_RUN" for t in after.json()["tasks"])
        assert file_sha(room.engine.store.db_path) == prefix_sha
        final = app.state.engine.store.get(room.auditor, room.engagement)
        reopened = create_retained_app(
            room.engine.store.root,
            config,
            file_sha(config),
            repository=REPO,
            allowed_hosts=["testserver"],
        )
        assert reopened.state.engine.store.get(room.auditor, room.engagement) == final
        assert file_sha(room.engine.store.db_path) == prefix_sha
        identities.update(room.binding["identities"].values())
    assert len(identities) == 6
