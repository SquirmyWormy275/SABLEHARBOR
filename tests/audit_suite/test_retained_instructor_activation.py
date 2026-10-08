"""Explicit manual teaching over fresh source-first workrooms; no old outcomes."""

import json
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_assessments import DIMENSIONS
from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, write
from enterprise.audit_suite.persistent_company_service import configuration
from enterprise.audit_suite.retained_explanation_service import (
    ACTIVE_MODULES,
    active_configuration,
    create_explained_app,
)
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError, canonical
from tests.audit_suite.test_full_scope_company_pair import acquire
from tests.audit_suite.test_persistent_company_service import http_command, login
from tests.audit_suite.test_sealed_retained_service import seal

pytest_plugins = [
    "tests.audit_suite.test_full_scope_company_pair",
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
]
REPO = Path(__file__).resolve().parents[2]


def activate(keycase, *, background=True):
    case = keycase["case"]
    generation = len(list(keycase["config"].parent.glob("*-active-config-*.json")))
    keycase["config"] = keycase["config"].parent / (
        f"{case['engagement']}-active-config-{generation}.json"
    )
    write(
        keycase["config"],
        active_configuration(
            case["config"],
            case["config_sha256"],
            keycase["bindings"],
            file_sha(keycase["bindings"]),
            repository=REPO,
            instructor_writeback=True,
            background_jobs=background,
        ),
    )
    keycase["config_sha256"] = file_sha(keycase["config"])
    return create_explained_app(
        case["root"],
        keycase["config"],
        keycase["config_sha256"],
        repository=REPO,
        allowed_hosts=["testserver"],
    )


def teaching(client, case, teacher, learner):
    base = "/api/engagements/" + case["engagement"]
    before = client.get(base, headers=teacher).json()
    options = client.get(
        base + "/instructor-assessments/options",
        params={"revision": before["revision"]},
        headers=teacher,
    )
    assert options.status_code == 200, options.text
    o = options.json()
    assessment = {
        k: o[k] for k in ("learner_revision", "key_pin", "rubric_sha256", "inventory_sha256")
    }
    issue, expectation = o["issues"][0]["id"], o["expectations"][0]["id"]
    assessment.update(
        expected_engagement_revision=before["revision"],
        title="Explicit limited source examination",
        issue_ids=[issue],
        expectation_ids=[expectation],
        dimensions=[
            {
                "dimension": d,
                "assessment": "Not assessed",
                "rationale": "Native custody alone does not establish understanding.",
                "reference_ids": [],
            }
            for d in DIMENSIONS
        ],
        alternatives=[],
        overrides=[],
        defects=[],
        predecessor=None,
        command_id="explicit-assessment",
    )
    saved = client.post(base + "/instructor-assessments", headers=teacher, json=assessment)
    assert saved.status_code == 200, saved.text
    assert (
        client.get(
            base + "/instructor-assessments/" + saved.json()["id"], headers=learner
        ).status_code
        == 403
    )
    debrief_options = client.get(base + "/instructor-releases/debrief-options", headers=teacher)
    assert debrief_options.status_code == 200, debrief_options.text
    draft = {
        "recipient_id": case["ids"]["auditor"],
        "expected_revision": before["revision"],
        "learner_revision": before["revision"],
        "title": "Selected source custody discussion",
        "predecessor_release_id": None,
        "sections": [
            {
                "issue_ids": [issue],
                "expectation_ids": [expectation],
                "explanation": "Compare originals and retained versions; no effectiveness claim.",
                "limitations": "Authored teaching content, not calibrated judgment.",
                "prompts": ["What additional corroboration is needed?"],
                "annotations": [],
            }
        ],
    }
    preview = client.post(
        base + "/instructor-releases/debrief-preview", headers=teacher, json=draft
    )
    assert preview.status_code == 200, preview.text
    assert client.get(base + "/assistance", headers=learner).json() == []
    p = preview.json()
    released = client.post(
        base + "/instructor-releases",
        headers=teacher,
        json={
            "preview_id": p["preview"]["id"],
            "preview_sha256": p["preview_sha256"],
            "command_id": "selected-release",
        },
    )
    assert released.status_code == 200, released.text
    content = client.get(base + "/assistance/" + released.json()["release_id"], headers=learner)
    assert content.status_code == 200, content.text
    assert content.json()["content"]["stage"] == "EXPLANATION"
    assert client.get(base + "/instructor-binding", headers=learner).status_code == 403
    assert client.get(base, headers=teacher).json() == before
    return saved.json(), released.json()


@pytest.mark.parametrize("backend", ["native", "stdlib"])
def test_source_before_two409_manual_assessment_selected_debrief_and_reopen(
    pair, tmp_path, monkeypatch, backend
):
    if backend == "stdlib":
        from enterprise.audit_suite import canonical_state_codec, serialized_json

        monkeypatch.setattr(serialized_json, "_native", None)
        monkeypatch.setattr(canonical_state_codec, "_fragmenter", None)
    runtime = tmp_path / "RUNTIME.json"
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
    for mode, room in pair.rooms.items():
        acquire(room)
        state = room.state()
        assert len(state["tasks"]) == 409 and len(state["artifacts"]) == 1
        source = state["artifacts"][0]["source"]["receipt"]["source"]
        native = {
            "id": "own-native",
            **{
                k: source[k] for k in ("company", "branch", "system", "record", "version", "sha256")
            },
        }
        pair.world.store.grant(
            pair.world.operator.principal,
            room.engagement,
            source["company"],
            source["branch"],
            source["system"],
        )
        snapshot = tmp_path / (mode + "-key")
        result = bind_snapshot(
            room.engine,
            instructor_id=room.operator,
            audited_actor_id=room.auditor,
            engagement_id=room.engagement,
            source_operator_id=pair.world.operator.principal,
            source_as_of=state["simulated_at"],
            source_refs=[native],
            authored={
                "issues": [
                    {
                        "id": "I",
                        "control_ids": ["SH-SEC-003"],
                        "source_ids": ["own-native"],
                        "claim": "Selected genuine source custody.",
                        "uncertainty": "No whole-year conclusion.",
                    }
                ],
                "expectations": [
                    {
                        "id": "E",
                        "issue_ids": ["I"],
                        "procedure": "Compare exact source version.",
                        "acceptable_alternatives": ["Document an unavailable corroborator."],
                    }
                ],
                "uncertainty": ["Authored training only"],
                "source_pins": {},
            },
            output=snapshot,
        )
        pair.world.store.grant(
            pair.world.operator.principal,
            room.engagement,
            source["company"],
            source["branch"],
            source["system"],
            active=False,
        )
        bindings = tmp_path / (mode + "-bindings.json")
        write(
            bindings,
            {
                room.engagement: {
                    "path": str(snapshot),
                    "manifest_sha256": result["manifest_sha256"],
                }
            },
        )
        base = tmp_path / (mode + "-base.json")
        write(
            base,
            configuration(
                pair.world,
                room.root / "BINDING.json",
                file_sha(room.root / "BINDING.json"),
                repository=REPO,
            ),
        )
        case = {
            "root": room.engine.store.root,
            "engine": room.engine,
            "ids": room.binding["identities"],
            "engagement": room.engagement,
            "config": base,
            "config_sha256": file_sha(base),
        }
        seal(case, state_codec=True)
        config = json.loads(base.read_bytes())
        store = SealedHistoryStore(
            case["root"], config["sealed_history"]["path"], config["sealed_history"]["sha256"]
        )
        case["people"] = {
            role: store.rotate_credential(pid, lifetime=3600) for role, pid in case["ids"].items()
        }
        config["authority_head"] = store.authority_head
        base = tmp_path / (mode + "-renewed-base.json")
        write(base, config)
        case["config"] = base
        case["config_sha256"] = file_sha(base)
        keycase = {
            "case": case,
            "bindings": bindings,
            "config": tmp_path / (mode + "-explained.json"),
        }
        app = activate(keycase)
        client = TestClient(app, base_url="https://testserver")
        teacher = {"Authorization": "Bearer " + case["people"]["operator"]["credential"]}
        learner = {"Authorization": "Bearer " + case["people"]["auditor"]["credential"]}
        capabilities = client.get("/api/bootstrap", headers=teacher).json()["capabilities"]
        assert all(
            capabilities[k]
            for k in (
                "instructor_assessments",
                "instructor_releases",
                "instructor_debriefs",
                "background_jobs",
            )
        )
        saved, released = teaching(client, case, teacher, learner)
        reopened = activate(keycase)
        other = TestClient(reopened, base_url="https://testserver")
        baseurl = "/api/engagements/" + room.engagement
        assert (
            other.get(
                baseurl + "/instructor-assessments/" + saved["id"], headers=teacher
            ).status_code
            == 200
        )
        assert (
            other.get(
                baseurl + "/assistance/" + released["release_id"], headers=learner
            ).status_code
            == 200
        )
        assert len(other.get(baseurl, headers=learner).json()["tasks"]) == 409
        assert file_sha(room.engine.store.db_path) == case["prefix_sha"]


@pytest.mark.parametrize("change", ["nodes", "logout", "native"])
def test_ordinary_get_closes_handler_node_auth_and_native_mutations(keycase, change):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = activate(keycase)
    client, _ = login(app, case, "auditor")
    path = "/api/engagements/" + case["engagement"]
    assert client.get(path).status_code == 200
    route = next(
        r
        for r in app.router.routes
        if getattr(r, "path", None) == "/api/engagements/{engagement_id}"
    )
    original = route.dependant.call

    async def changed(*args, **kwargs):
        response = await original(*args, **kwargs)
        if change == "logout":
            cookie = next(
                v for k, v in kwargs["request"].cookies.items() if k.startswith("sh_audit_session_")
            )
            app.state.engine.store.logout(cookie)
        elif change == "native":
            artifact = keycase["before"]["artifacts"][0]
            p = case["root"] / "artifacts" / artifact["sha256"]
            old = p.stat()
            data = p.read_bytes()
            p.write_bytes(bytes([data[0] ^ 1]) + data[1:])
            os.utime(p, ns=(old.st_atime_ns, old.st_mtime_ns))
        else:
            with sqlite3.connect(app.state.engine.store.db_path) as db:
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name='state_nodes'"
                ).fetchall()
                names = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='state_nodes'"
                ).fetchall()
                for (name,) in names:
                    db.execute('DROP TRIGGER "' + name + '"')
                row = db.execute(
                    "SELECT id,payload FROM state_nodes WHERE kind='L' LIMIT 1"
                ).fetchone()
                b = bytes(row[1])
                db.execute(
                    "UPDATE state_nodes SET payload=? WHERE id=?",
                    (bytes([b[0] ^ 1]) + b[1:], row[0]),
                )
                for (s,) in sql:
                    db.execute(s)
        return response

    route.dependant.call = changed
    response = client.get(path)
    assert response.status_code in (401, 403, 503), response.text
    assert "artifacts" not in response.json()


@pytest.mark.parametrize(
    "field,value",
    [("instructor_writeback", 1), ("background_jobs", "yes"), ("artifact_option_limit", True)],
)
def test_activation_configuration_requires_strict_explicit_types(keycase, field, value):
    arguments = {
        "instructor_writeback": True,
        "background_jobs": True,
        "artifact_option_limit": 5000,
    }
    arguments[field] = value
    with pytest.raises(Exception, match="Typed explicit"):
        active_configuration(
            keycase["case"]["config"],
            keycase["case"]["config_sha256"],
            keycase["bindings"],
            file_sha(keycase["bindings"]),
            repository=REPO,
            **arguments,
        )


def test_active_loaded_helper_origin_vector_is_exact_and_no_override(keycase):
    seal(keycase["case"], state_codec=True)
    activate(keycase)
    config = json.loads(keycase["config"].read_bytes())
    assert set(config["code_pins"]) == set(ACTIVE_MODULES)
    del config["code_pins"]["instructor_debrief.py"]
    keycase["config"] = keycase["config"].parent / "missing-helper-negative.json"
    write(keycase["config"], config)
    with pytest.raises(Exception, match="module pins"):
        create_explained_app(
            keycase["case"]["root"], keycase["config"], file_sha(keycase["config"]), repository=REPO
        )


@pytest.mark.parametrize("count", [2001, 5001])
def test_release_options_legacy_limit_and_explicit_5000_complete_metadata(tmp_path, count):
    from tests.audit_suite.test_instructor_releases import release

    core, engine, args = release.__wrapped__(tmp_path)
    state = engine.store.get(args["instructor_id"], args["engagement_id"])
    # Real private Store event before options. These are owned neutral metadata,
    # not claimed native operating records or accepted evidence.
    neutral = {
        "id": "A",
        "name": "neutral.txt",
        "engagement_id": args["engagement_id"],
        "sha256": "a" * 64,
        "bytes": 0,
        "audience": "LEARNER",
        "status": "AVAILABLE",
    }
    originals = [dict(neutral, id="A-" + str(i)) for i in range(count)]
    engine.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "kind": "neutral.metadata",
            "command_id": "large-options",
            "expected_revision": state["revision"],
            "payload": {},
        },
        lambda s, *_: s | {"artifacts": originals},
        permissions={"instruct"},
    )
    with pytest.raises(DomainError, match="options limit"):
        core.options(args["instructor_id"], args["engagement_id"])
    from enterprise.audit_suite.instructor_releases import InstructorReleases

    explicit = InstructorReleases(core.root, engine, core.bindings, artifact_option_limit=5000)
    if count > 5000:
        with pytest.raises(DomainError, match="options limit"):
            explicit.debrief_options(args["instructor_id"], args["engagement_id"])
        return
    data = explicit.debrief_options(args["instructor_id"], args["engagement_id"])
    assert len(data["artifacts"]) == count and len({r["id"] for r in data["artifacts"]}) == count
    assert len(canonical(data).encode()) < 32 * 1024 * 1024


@pytest.mark.parametrize(
    "view,change",
    [
        ("assessment", "key"),
        ("assessment", "logout"),
        ("debrief", "revocation"),
        ("debrief", "native"),
    ],
)
def test_manual_and_selected_routes_close_auth_key_nodes_and_original_bytes(keycase, view, change):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = activate(keycase)
    client, _ = login(app, case, "operator")
    actor = case["ids"]["operator"]
    saved, released = teaching(
        client,
        case,
        {"Authorization": "Bearer " + case["people"]["operator"]["credential"]},
        {"Authorization": "Bearer " + case["people"]["auditor"]["credential"]},
    )
    if view == "debrief":
        client, _ = login(app, case, "auditor")
        actor = case["ids"]["auditor"]
        route_path = "/api/engagements/{engagement_id}/assistance/{release_id}"
        path = "/api/engagements/" + case["engagement"] + "/assistance/" + released["release_id"]
    else:
        route_path = "/api/engagements/{engagement_id}/instructor-assessments/{assessment_id}"
        path = "/api/engagements/" + case["engagement"] + "/instructor-assessments/" + saved["id"]
    assert client.get(path).status_code == 200
    route = next(r for r in app.router.routes if getattr(r, "path", None) == route_path)
    original = route.dependant.call

    async def changed(*args, **kwargs):
        response = await original(*args, **kwargs)
        if change == "key":
            p = keycase["snapshot"] / "snapshot.json"
        elif change == "native":
            p = case["root"] / "artifacts" / keycase["before"]["artifacts"][0]["sha256"]
        elif change == "logout":
            token = next(
                v for k, v in kwargs["request"].cookies.items() if k.startswith("sh_audit_session_")
            )
            app.state.engine.store.logout(token)
            return response
        else:
            # A legitimate signed authority change is checked at response close.
            app.state.engine.store.revoke(actor)
            return response
        old = p.stat()
        data = p.read_bytes()
        p.write_bytes(bytes([data[0] ^ 1]) + data[1:])
        os.utime(p, ns=(old.st_atime_ns, old.st_mtime_ns))
        return response

    route.dependant.call = changed
    response = client.get(path)
    assert response.status_code in (401, 403, 503), response.text
    assert "content" not in response.json() and "dimensions" not in response.json()


def test_new_options_response_budget_refuses_whole_view_before_http_serialization(keycase):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = activate(keycase)
    client, _ = login(app, case, "operator")
    path = "/api/engagements/" + case["engagement"] + "/instructor-releases/options"
    whole = client.get(path)
    assert whole.status_code == 200 and whole.json()["artifacts"]
    app.state.engine.store.PRIVATE_VIEW_MAX_BYTES = 128
    denied = client.get(path)
    assert denied.status_code == 413 and denied.json()["code"] == "VIEW_BUDGET_EXCEEDED"
    assert "artifacts" not in denied.json()


def test_native_census_background_readthrough_reconnect_and_exact_replay(keycase):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = activate(keycase)
    client, headers = login(app, case, "auditor")
    created = http_command(
        client,
        headers,
        case,
        "pbc.create",
        {
            "title": "Independent native census",
            "purpose": "Discover actual source versions",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    assert created.status_code == 200, created.text
    rid = created.json()["requests"][-1]["id"]
    issued = http_command(client, headers, case, "pbc.issue", {"request_id": rid})
    assert issued.status_code == 200, issued.text
    before = issued.json()
    command = {
        "command_id": "background-native-census",
        "expected_revision": before["revision"],
        "kind": "company.census.collect",
        "payload": {
            "request_id": rid,
            "system_id": "operations.events",
            "query": {
                "version_policy": "ALL_VISIBLE_VERSIONS",
                "event_window": {"start": "2027-01-01T00:00:00Z", "end": "2027-01-03T00:00:00Z"},
                "unknown_event_policy": "INCLUDE_UNDATED_STRATUM",
            },
        },
    }
    jobs = app.state.background_jobs
    submitted = jobs.submit(case["ids"]["auditor"], case["engagement"], command)
    assert jobs.input(case["ids"]["auditor"], case["engagement"], submitted["id"]) == command
    jobs.start(case["ids"]["auditor"], case["engagement"], submitted["id"])
    thread = jobs.threads.get(submitted["id"])
    if thread:
        thread.join(30)
        assert not thread.is_alive()
    done = jobs.read(case["ids"]["auditor"], case["engagement"], submitted["id"])
    assert done["status"] == "COMPLETED", done
    after = client.get("/api/engagements/" + case["engagement"]).json()
    assert after["revision"] == before["revision"] + 1 and not after["populations"]
    assert jobs.submit(case["ids"]["auditor"], case["engagement"], command)["id"] == submitted["id"]
    reopened = activate(keycase)
    assert (
        reopened.state.background_jobs.read(
            case["ids"]["auditor"], case["engagement"], submitted["id"]
        )["status"]
        == "COMPLETED"
    )
    assert (
        reopened.state.engine.store.get(case["ids"]["auditor"], case["engagement"])["revision"]
        == after["revision"]
    )


def test_deferred_worker_rechecks_current_signed_authority_before_execution(keycase):
    case = keycase["case"]
    seal(case, state_codec=True)
    app = activate(keycase)
    actor = case["ids"]["operator"]
    state = app.state.engine.store.get(actor, case["engagement"])
    jobs = app.state.background_jobs
    envelope = {
        "command_id": "revoked-background",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {"meeting_id": "not-created", "content": "No hidden Key content."},
    }
    job = jobs.submit(actor, case["engagement"], envelope)
    app.state.engine.store.grant(case["engagement"], actor, "review")
    # Execute the already pending ordinary job under its original attributed
    # actor; it must not trust authorization at submission time.
    jobs._execute_job(actor, case["engagement"], job["id"])
    with jobs._db() as db:
        row = dict(db.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone())
    assert row["status"] == "FAILED" and row["result_revision"] is None
    assert (
        app.state.engine.store.get(case["ids"]["operator"], case["engagement"])["revision"]
        == state["revision"]
    )
