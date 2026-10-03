"""Original818 producer and separate derived storage, with real native inputs."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.history_inspection import inspect_history
from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, write
from enterprise.audit_suite.persistent_company_service import (
    configuration,
    create_retained_app,
    sealed_configuration,
)
from enterprise.audit_suite.pristine_tail_conversion import convert_pristine_tail
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError, Store
from tests.audit_suite.test_full_scope_company_pair import acquire

pytest_plugins = ["tests.audit_suite.test_full_scope_company_pair"]
REPO = Path(__file__).resolve().parents[2]
PRODUCER = Path("/home/kingoftheeast/Projects/SABLEHARBOR-retained-preexpiry-delegation-wt")
PRODUCER_CODE = r"""
import hashlib, importlib, json, sys
from pathlib import Path
from enterprise.audit_suite.preexpiry_seal_delegation import (
 DIRECT_MODULES,prepare_delegation,SealDelegation
)
from enterprise.audit_suite.sealed_history_store import prepare_tail
from enterprise.audit_suite.store import Store
request=json.loads(sys.stdin.read()); root=Path(request['root'])
origins={}
for name in DIRECT_MODULES:
 module=importlib.import_module(name);path=Path(module.__file__).absolute()
 origins[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
choice=prepare_delegation(root,request['credential'],request['binding'],origins,Path(request['grant']))
delegation=SealDelegation(choice)
store=Store.__new__(Store);store.root=root;store.db_path=root/'engagements.sqlite3'
parent=prepare_tail(store,request['operator'],request['engagement'],Path(request['parent']),delegation=delegation)
print(json.dumps({'parent':parent,'delegation':choice,'consumed':delegation.consumption}))
"""


@pytest.fixture
def original(request, tmp_path, monkeypatch):
    credentials = {}
    real = Store.provision

    def provision(store, *args, **kwargs):
        value = real(store, *args, **kwargs)
        credentials[value["id"]] = value["credential"]
        return value

    monkeypatch.setattr(Store, "provision", provision)
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
            "engineering_fixture_not_actual_acceptance": True,
        },
    )
    pair.world.accept_runtime(runtime, file_sha(runtime))
    parents = {}
    for mode, room in pair.rooms.items():
        assert len(acquire(room)) == 1
        binding = room.root / "BINDING.json"
        values = {
            "root": str(room.engine.store.root),
            "credential": credentials[room.operator],
            "binding": {"path": str(binding), "sha256": file_sha(binding)},
            "operator": room.operator,
            "engagement": room.engagement,
            "grant": str(tmp_path / (mode + "-grant")),
            "parent": str(tmp_path / (mode + "-parent")),
        }
        result = subprocess.run(
            [__import__("sys").executable, "-B", "-c", PRODUCER_CODE],
            input=json.dumps(values).encode(),
            capture_output=True,
            check=True,
            cwd=PRODUCER,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(PRODUCER) + ":" + str(PRODUCER / "src"),
            },
        )
        parents[mode] = json.loads(result.stdout)
    return pair, parents, credentials


@pytest.mark.parametrize("backend", ["native", "stdlib"])
def test_actual818_consumed_two409_pristine_storage_then_signed_renewal_and_reopen(
    original, tmp_path, monkeypatch, backend
):
    from enterprise.audit_suite import serialized_json

    if backend == "stdlib":
        monkeypatch.setattr(serialized_json, "_native", None)
    else:
        assert serialized_json._native is not None
    pair, parents, credentials = original
    for mode, room in pair.rooms.items():
        values = parents[mode]
        before = room.state()
        prefix_sha = file_sha(room.engine.store.db_path)
        parent_manifest = json.loads(Path(values["parent"]["path"]).read_bytes())
        parent_sha = file_sha(Path(parent_manifest["tail_path"]))
        choice = convert_pristine_tail(
            room.engine.store.root,
            values["parent"],
            values["delegation"],
            values["consumed"],
            tmp_path / (mode + "-codec"),
        )
        store = SealedHistoryStore(room.engine.store.root, choice["path"], choice["sha256"])
        converted = json.loads(Path(choice["path"]).read_bytes())
        assert converted["prefix"] == parent_manifest["prefix"]
        assert (
            converted["operator_authority"]["public_key_hex"]
            == parent_manifest["operator_authority"]["public_key_hex"]
        )
        assert store.get(room.auditor, room.engagement) == before
        old = credentials[room.auditor]
        access = store.rotate_credential(room.auditor, lifetime=3600)
        with pytest.raises(DomainError):
            store.authenticate(old)
        binding = room.root / "BINDING.json"
        base = configuration(pair.world, binding, file_sha(binding), repository=REPO)
        config = tmp_path / (mode + "-CONFIG.json")
        write(config, sealed_configuration(base, choice, store.authority_head, repository=REPO))
        app = create_retained_app(
            room.engine.store.root,
            config,
            file_sha(config),
            repository=REPO,
            allowed_hosts=["testserver"],
        )
        client = TestClient(app, base_url="https://testserver")
        response = client.post("/api/session", json={"credential": access["credential"]})
        assert response.status_code == 200
        current = app.state.engine.store.get(room.auditor, room.engagement)
        edited = client.post(
            "/api/engagements/" + room.engagement + "/commands",
            headers={"X-CSRF-Token": response.json()["csrf_token"]},
            json={
                "command_id": "ordinary-derived-note-" + mode,
                "expected_revision": current["revision"],
                "kind": "note.create",
                "payload": {
                    "title": "Ordinary exact tail",
                    "text": "No source or audit credit imported",
                },
            },
        )
        assert edited.status_code == 200, edited.text
        app.state.retained_workroom.refresh_integrity(room.auditor)
        history = inspect_history(
            app.state.engine.store, room.auditor, room.engagement, revisions=[0, before["revision"]]
        )
        assert history["count"] == before["revision"] + 2
        assert len(edited.json()["tasks"]) == 409 and len(edited.json()["controls"]) == 70
        assert all(t["conclusion"] == "NOT_RUN" for t in edited.json()["tasks"])
        reopened = create_retained_app(
            room.engine.store.root, config, file_sha(config), repository=REPO
        )
        assert reopened.state.engine.store.get(
            room.auditor, room.engagement
        ) == app.state.engine.store.get(room.auditor, room.engagement)
        assert file_sha(room.engine.store.db_path) == prefix_sha
        assert file_sha(Path(parent_manifest["tail_path"])) == parent_sha


@pytest.mark.parametrize("change", ["event", "rotate", "login", "logout"])
def test_parent_lifecycle_is_not_pristine_and_later_parent_mutation_refuses(
    original, tmp_path, change
):
    pair, parents, credentials = original
    room = pair.rooms["CLEAN"]
    values = parents["CLEAN"]
    converted = convert_pristine_tail(
        room.engine.store.root,
        values["parent"],
        values["delegation"],
        values["consumed"],
        tmp_path / "derived",
    )
    child = SealedHistoryStore(room.engine.store.root, converted["path"], converted["sha256"])
    parent = SealedHistoryStore(
        room.engine.store.root, values["parent"]["path"], values["parent"]["sha256"]
    )
    if change == "event":
        from enterprise.audit_suite.engine import Engine

        engine = Engine(room.engine.store.root, repository=REPO, _store=parent)
        before = parent.get(room.auditor, room.engagement)
        engine.command(
            room.auditor,
            room.engagement,
            {
                "command_id": "actual-parent-note",
                "expected_revision": before["revision"],
                "kind": "note.create",
                "payload": {"title": "Ordinary parent write", "text": "No outcome claim"},
            },
        )
    elif change == "rotate":
        parent.rotate_credential(room.auditor)
    else:
        session = parent.login(credentials[room.auditor])
        if change == "logout":
            parent.logout(session["token"])
    with pytest.raises(DomainError):
        child.check_prefix()
    with pytest.raises(DomainError):
        convert_pristine_tail(
            room.engine.store.root,
            values["parent"],
            values["delegation"],
            values["consumed"],
            tmp_path / "refused",
        )
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize(
    "field", ["operator", "engagement", "status", "delegation_sha256", "consumed_at"]
)
def test_resealed_consumption_does_not_substitute_another_operator_or_execution(
    original, tmp_path, field
):
    pair, parents, _ = original
    room, values = pair.rooms["CLEAN"], parents["CLEAN"]
    source = Path(values["consumed"]["path"])
    body = json.loads(source.read_bytes())
    body[field] = True if field == "consumed_at" else "UNRELATED"
    replacement = tmp_path / "REPAIRED-CONSUMED.json"
    write(replacement, body)
    wrong = {"path": str(replacement), "sha256": file_sha(replacement)}
    with pytest.raises(DomainError):
        convert_pristine_tail(
            room.engine.store.root,
            values["parent"],
            values["delegation"],
            wrong,
            tmp_path / "refused",
        )
    assert not (tmp_path / "refused").exists()


def test_expired_original_bearer_is_not_reactivated_by_storage_conversion(
    original, tmp_path, monkeypatch
):
    import time

    pair, parents, credentials = original
    room, values = pair.rooms["CLEAN"], parents["CLEAN"]
    grant = json.loads(Path(values["delegation"]["path"]).read_bytes())
    now = grant["operator"]["expires"] + 1
    monkeypatch.setattr(time, "time", lambda: now)
    choice = convert_pristine_tail(
        room.engine.store.root,
        values["parent"],
        values["delegation"],
        values["consumed"],
        tmp_path / "after-expiry",
    )
    store = SealedHistoryStore(room.engine.store.root, choice["path"], choice["sha256"])
    with pytest.raises(DomainError) as error:
        store.authenticate(credentials[room.operator])
    assert error.value.status == 401
    renewed = store.rotate_credential(room.operator, lifetime=3600)
    assert renewed["id"] == room.operator
    assert store.authenticate(renewed["credential"])["id"] == room.operator
