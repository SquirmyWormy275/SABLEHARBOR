"""Opt-in reuse of a genuine live room; no persisted source/outcome admission."""

import asyncio
import json
import os
import threading
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import retained_explanation_service as explanation
from enterprise.audit_suite import sealed_retained_service
from enterprise.audit_suite.persistent_company_journey import write
from enterprise.audit_suite.persistent_company_service import RetainedWorkroom
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_persistent_company_service import login
from tests.audit_suite.test_sealed_retained_service import seal

pytest_plugins = [
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
    "tests.audit_suite.test_full_scope_company_pair",
]
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def live(keycase):
    case = keycase["case"]
    seal(case, state_codec=True)
    room = RetainedWorkroom(
        case["config"], case["config_sha256"], private_root=case["root"], repository=REPO
    )
    config = keycase["config"].parent / "SEALED-LIVE-EXPLANATION.json"
    write(
        config,
        explanation.configuration(
            case["config"],
            case["config_sha256"],
            keycase["bindings"],
            file_sha(keycase["bindings"]),
            repository=REPO,
        ),
    )
    keycase["config"], keycase["config_sha256"] = config, file_sha(config)
    keycase["room"] = room
    return keycase


def explained(live, **changes):
    args = dict(private_root=live["case"]["root"], repository=REPO, retained_workroom=live["room"])
    args.update(changes)
    return explanation.ExplainedWorkroom(live["config"], live["config_sha256"], **args)


def app(live, **changes):
    args = dict(repository=REPO, retained_workroom=live["room"], allowed_hosts=["testserver"])
    args.update(changes)
    return explanation.create_explained_app(
        live["case"]["root"], live["config"], live["config_sha256"], **args
    )


@pytest.mark.parametrize("active", [False, True])
def test_reuse_same_initialized_object_and_default_real_cold_scan(live, monkeypatch, active):
    if active:
        p = live["config"].parent / "ACTIVE-LIVE.json"
        write(
            p,
            explanation.active_configuration(
                live["case"]["config"],
                live["case"]["config_sha256"],
                live["bindings"],
                file_sha(live["bindings"]),
                repository=REPO,
                instructor_writeback=True,
                background_jobs=True,
                artifact_option_limit=5000,
            ),
        )
        live["config"], live["config_sha256"] = p, file_sha(p)
    calls = []
    original = sealed_retained_service.verify_sealed

    def scan(room):
        calls.append(room)
        return original(room)

    monkeypatch.setattr(sealed_retained_service, "verify_sealed", scan)
    source_before = file_sha(live["room"].world.database)
    prefix_before = file_sha(live["room"].sealed_store.prefix_path)
    first = explained(live)
    application = app(live)
    assert (
        first.retained is live["room"]
        and application.state.engine is live["room"].engine
        and calls == []
    )
    cold = explanation.ExplainedWorkroom(
        live["config"], live["config_sha256"], private_root=live["case"]["root"], repository=REPO
    )
    assert cold.retained is not live["room"] and calls == [cold.retained]
    assert (
        file_sha(live["room"].world.database) == source_before
        and file_sha(live["room"].sealed_store.prefix_path) == prefix_before
    )


@pytest.mark.parametrize(
    "wrong",
    [
        "duck",
        "uninitialized",
        "subclass",
        "pending",
        "engine",
        "world",
        "config_sha",
        "config_path",
        "binding",
        "root",
        "repository",
        "missing_prefix",
        "setting",
    ],
)
def test_live_reuse_refuses_fake_failed_or_different_identity(live, wrong, tmp_path):
    room = live["room"]
    args = {}
    if wrong == "duck":
        args["retained_workroom"] = object()
    elif wrong == "uninitialized":
        args["retained_workroom"] = RetainedWorkroom.__new__(RetainedWorkroom)
    elif wrong == "subclass":

        class Fake(RetainedWorkroom):
            pass

        obj = Fake.__new__(Fake)
        obj.__dict__.update(vars(room))
        args["retained_workroom"] = obj
    elif wrong == "pending":
        room._pending_prefix = None
    elif wrong == "engine":
        room.engine = object()
    elif wrong == "world":
        room.world = object()
    elif wrong == "config_sha":
        room.expected_sha256 = "f" * 64
    elif wrong == "config_path":
        p = tmp_path / "same-bytes-other-path.json"
        p.write_bytes(room.path.read_bytes())
        p.chmod(0o600)
        room.path = p
    elif wrong == "binding":
        room.binding["branch"] = "FOREIGN"
    elif wrong == "root":
        args["private_root"] = tmp_path
    elif wrong == "repository":
        args["repository"] = tmp_path
    elif wrong == "missing_prefix":
        room.sealed_store._prefix_integrity = None
    else:
        args["inference_config"] = tmp_path / "not-current-model.json"
    with pytest.raises((DomainError, ValueError)):
        explained(live, **args)


@pytest.mark.parametrize("change", ["config", "native", "prefix", "head", "role", "revoke", "key"])
def test_reuse_fresh_code_config_source_native_head_role_and_privacy(live, change):
    room = live["room"]
    case = live["case"]
    if change == "config":
        raw = room.path.read_bytes()
        room.path.write_bytes(raw + b" ")
    elif change == "native":
        p = room.root / "artifacts" / live["before"]["artifacts"][0]["sha256"]
        st = p.stat()
        raw = p.read_bytes()
        p.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    elif change == "prefix":
        p = room.sealed_store.prefix_path
        st = p.stat()
        with p.open("r+b") as f:
            f.seek(-1, 2)
            b = f.read(1)
            f.seek(-1, 2)
            f.write(bytes([b[0] ^ 1]))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    elif change == "head":
        room.engine.store.rotate_credential(case["ids"]["operator"], lifetime=3600)
    elif change == "role":
        room.engine.store.grant(room.engagement, case["ids"]["operator"], "learn")
    elif change == "revoke":
        room.engine.store.revoke(case["ids"]["operator"])
    else:
        p = live["snapshot"] / "snapshot.json"
        p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises((DomainError, ValueError)):
        explained(live)
    if change == "key":
        # Private damage does not block independently valid ordinary company reads.
        client = TestClient(app_for_retained(room), base_url="https://testserver")
        headers = {"Authorization": "Bearer " + case["people"]["auditor"]["credential"]}
        assert (
            client.get(
                "/api/engagements/" + room.engagement + "/company/systems", headers=headers
            ).status_code
            == 200
        )


def app_for_retained(room):
    from enterprise.audit_suite.service import create_app

    return create_app(
        room.root,
        repository=REPO,
        engine_factory=lambda: room.engine,
        request_guard=room.guard,
        allowed_hosts=["testserver"],
    )


def test_same_reused_object_login_scope_privacy_logout_and_real_repin_reopen(live):
    room = live["room"]
    case = live["case"]
    application = app(live)
    client, csrf = login(application, case, "operator")
    base = "/api/engagements/" + room.engagement
    assert client.get(base + "/instructor-binding").status_code == 200
    learner, _ = login(application, case, "auditor")
    assert learner.get(base + "/instructor-binding").status_code == 403
    assert learner.get(base).status_code == 200
    state = room.engine.store.get(case["ids"]["auditor"], room.engagement)
    prefix_before = file_sha(room.sealed_store.prefix_path)
    assert client.post("/api/logout", headers=csrf).status_code == 200
    assert client.get(base + "/instructor-binding").status_code == 401
    assert (
        room.engine.store.get(case["ids"]["auditor"], room.engagement) == state
        and file_sha(room.sealed_store.prefix_path) == prefix_before
    )
    # A genuine cold reopen consumes freshly pinned signed logout inventory.
    config = json.loads(room.path.read_bytes())
    config["session_revocations"] = room.sealed_store.session_authority.known_revocations
    p = room.path.parent / "REPinned-COLD.json"
    write(p, config)
    updated = explanation.configuration(
        p, file_sha(p), live["bindings"], file_sha(live["bindings"]), repository=REPO
    )
    q = live["config"].parent / "REPinned-KEY.json"
    write(q, updated)
    cold = explanation.ExplainedWorkroom(q, file_sha(q), private_root=room.root, repository=REPO)
    assert (
        cold.retained is not room
        and cold.retained.engine.store.get(case["ids"]["auditor"], room.engagement) == state
    )


def test_reused_instance_cancelled_handler_settles_before_next_guard(live):
    application = app(live)
    case = live["case"]
    started = threading.Event()
    release = threading.Event()
    path = "/api/engagements/" + live["room"].engagement + "/own-slow-read"

    def worker():
        started.set()
        assert release.wait(10)
        return {"owned": "settled"}

    @application.get(path)
    async def slow():
        return await asyncio.to_thread(worker)

    async def run():
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
            headers = {"Authorization": "Bearer " + case["people"]["operator"]["credential"]}
            first = asyncio.create_task(client.get(path, headers=headers))
            assert await asyncio.to_thread(started.wait, 10)
            first.cancel()
            second = asyncio.create_task(client.get("/api/bootstrap", headers=headers))
            await asyncio.sleep(0.1)
            assert not first.done() and not second.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await first
            assert (await second).status_code == 200

    try:
        asyncio.run(run())
    finally:
        release.set()


@pytest.mark.parametrize("backend", ["native", "stdlib"])
def test_reused_two409_source_before_audit_manual_release_journey(
    pair, tmp_path, monkeypatch, backend
):
    """Real ordinary native collection and manual flow, same objects per app."""
    from tests.audit_suite import test_retained_instructor_activation as activation

    original = explanation.create_explained_app
    reused = []

    def with_live(root, path, pin, *, repository, **options):
        config = json.loads(path.read_bytes())["retained_workroom"]
        room = RetainedWorkroom(
            config["path"], config["sha256"], private_root=root, repository=repository
        )
        result = original(root, path, pin, repository=repository, retained_workroom=room, **options)
        assert result.state.engine is room.engine
        reused.append(room)
        return result

    monkeypatch.setattr(activation, "create_explained_app", with_live)
    activation.test_source_before_two409_manual_assessment_selected_debrief_and_reopen(
        pair, tmp_path, monkeypatch, backend
    )
    assert len(reused) == 4  # First apps and genuinely cold reopen, both modes.
    assert len({id(room) for room in reused}) == 4
