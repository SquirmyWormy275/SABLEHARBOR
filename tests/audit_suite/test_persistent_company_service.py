"""Real retained neutral workrooms over HTTP, not actual company activation."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.persistent_company_journey import (
    RUNTIME_SCHEMA,
    RUNTIME_VERDICT,
    PersistentCompany,
    native_rows,
    write,
)
from enterprise.audit_suite.persistent_company_service import (
    BINDING_SCHEMA,
    RetainedWorkroom,
    configuration,
    create_retained_app,
)
from enterprise.audit_suite.recovery import _history
from enterprise.audit_suite.source_library_audit import (
    EMPTY_WORKROOM,
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    file_sha,
    quiescent_read,
)
from enterprise.audit_suite.store import canonical
from enterprise.ccf.registry import compile_registry, digest

REPO = Path(__file__).resolve().parents[2]
COMPANY = "NEUTRAL-RETAINED-SERVICE"
SYSTEM = "operations.events"


def command(engine, actor, engagement, kind, payload):
    state = engine.store.get(actor, engagement)
    return engine.command(
        actor,
        engagement,
        {
            "command_id": f"neutral-{kind}-{state['revision']}",
            "kind": kind,
            "payload": payload,
            "expected_revision": state["revision"],
        },
    )


@pytest.fixture
def retained(tmp_path):
    tmp_path.chmod(0o700)
    original = tmp_path / "original-neutral-source"
    original.mkdir(mode=0o700)
    source = CompanyStore(original)
    for branch in ("ALPHA", "BETA"):
        source.register_system(COMPANY, branch, SYSTEM, "neutral-owner")
        source.append_version(
            COMPANY,
            branch,
            SYSTEM,
            "event-one",
            expected_version=0,
            command_id="original-" + branch,
            event_at="2027-01-02T00:00:00Z",
            available_at="2027-01-02T01:00:00Z",
            content=json.dumps({"engineering_neutral_fixture": True, "revision": 1}).encode(),
            provenance={
                "source_reference": "neutral-original-only",
                "name": "event.json",
                "content_type": "application/json",
            },
        )
    database = original / "company.sqlite3"
    manifest, review = original / "MANIFEST.json", original / "REVIEW.json"
    write(
        manifest,
        {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(database)}},
    )
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {
                "company.sqlite3": file_sha(database),
                "MANIFEST.json": file_sha(manifest),
            },
            "native_versions": 2,
            "engineering_fixture_not_actual_independent_acceptance": True,
        },
    )
    accepted = AcceptedLibrary(
        database, file_sha(database), manifest, file_sha(manifest), review, file_sha(review), 2
    )
    world = PersistentCompany.initialize(
        accepted,
        tmp_path / "company-lifetime",
        operator_id="COMPANY-OPERATOR-NEUTRAL",
        engineering_only=True,
    )
    runtime = tmp_path / "NEUTRAL-RUNTIME-REVIEW.json"
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
            "accepted_baseline_pins": world.pins,
            "engineering_fixture_not_actual_independent_acceptance": True,
        },
    )
    world.accept_runtime(runtime, file_sha(runtime))
    pack = tmp_path / "NEUTRAL-INSTRUCTIONS.json"
    instructions = {
        "native_digest": digest(compile_registry(REPO)),
        "selections": {"baseline": {"controls": [], "actions": [], "dependency_gates": []}},
        "engineering_fixture_not_actual_program_acceptance": True,
        # Exercise a pack above the operator-config limit: the real pack is 11 MB.
        "neutral_padding": "x" * (1024 * 1024),
    }
    instructions["digest"] = digest(instructions)
    write(pack, instructions)
    workrooms = {}
    for branch in ("ALPHA", "BETA"):
        root = tmp_path / (branch.lower() + "-audit")
        engine = Engine(root, repository=REPO, program_pack=pack)
        engine.company_store = world.store
        people = {
            role: engine.store.provision("Neutral " + role, [permission])
            for role, permission in (
                ("operator", "instructor"),
                ("auditor", "learner"),
                ("reviewer", "reviewer"),
            )
        }
        ids = {k: v["id"] for k, v in people.items()}
        initial = engine.create(
            ids["operator"],
            {
                "command_id": "neutral-service-birth",
                "title": "Retained neutral investigation",
                "discipline": "IT",
                "mode": "CLEAN",
                "configuration": {"selections": []},
                "scope": {
                    "programs": ["SOC2"],
                    "report_type": "Type 2",
                    "period_start": "2027-01-01",
                    "period_end": "2027-12-31",
                    "fieldwork_start": "2027-01-03",
                    "timezone": "UTC",
                    "boundaries": ["corporate"],
                    "control_ids": ["SH-SEC-003"],
                },
            },
        )
        engagement = initial["id"]
        engine.store.grant(engagement, ids["auditor"], "learn")
        engine.store.grant(engagement, ids["reviewer"], "review")
        engine.company_bindings[engagement] = {"company": COMPANY, "branch": branch}
        command(engine, ids["operator"], engagement, "company.activate", {})
        command(engine, ids["auditor"], engagement, "kickoff.start", {})
        world.store.grant(ids["auditor"], engagement, COMPANY, branch, SYSTEM)
        binding = tmp_path / (branch + "-BINDING.json")
        write(
            binding,
            {
                "schema": BINDING_SCHEMA,
                "company_root": str(world.root),
                "company_initialization_sha256": file_sha(world.root / "INITIALIZATION.json"),
                "accepted_baseline_pins": world.pins,
                "audit_root": str(root),
                "engagement_id": engagement,
                "company": COMPANY,
                "branch": branch,
                "identities": ids,
                "company_operator_id": world.operator.principal,
                "program_pack": {"path": str(pack), "sha256": file_sha(pack)},
                "task_count": len(initial["tasks"]),
                "mode": initial["mode"],
                "initial_simulated_at": initial["simulated_at"],
                "scope": initial["scope"],
                "zero_workroom_counts": {k: len(initial[k]) for k in EMPTY_WORKROOM},
            },
        )
        config = tmp_path / (branch + "-CONFIG.json")
        write(config, configuration(world, binding, file_sha(binding), repository=REPO))
        workrooms[branch] = {
            "root": root,
            "engine": engine,
            "engagement": engagement,
            "people": people,
            "ids": ids,
            "binding": binding,
            "config": config,
            "config_sha256": file_sha(config),
        }
    return {"world": world, "workrooms": workrooms, "root": tmp_path, "pack": pack}


def boot(case, **options):
    return create_retained_app(
        case["root"],
        case["config"],
        case["config_sha256"],
        repository=REPO,
        allowed_hosts=["testserver"],
        **options,
    )


def login(app, case, role="auditor"):
    client = TestClient(app, base_url="https://testserver")
    response = client.post("/api/session", json={"credential": case["people"][role]["credential"]})
    assert response.status_code == 200, response.text
    return client, {"X-CSRF-Token": response.json()["csrf_token"]}


def http_command(client, headers, case, kind, payload):
    url = "/api/engagements/" + case["engagement"]
    state = client.get(url).json()
    return client.post(
        url + "/commands",
        headers=headers,
        json={
            "command_id": f"http-{kind}-{state['revision']}",
            "kind": kind,
            "payload": payload,
            "expected_revision": state["revision"],
        },
    )


def append_correction(world):
    content = json.dumps({"engineering_neutral_fixture": True, "revision": 2}).encode()
    return world.append(
        world.operator,
        {
            "company": COMPANY,
            "branch": "ALPHA",
            "system": SYSTEM,
            "record": "event-one",
            "expected_version": 1,
            "command_id": "neutral-company-correction",
            "event_at": "2027-01-10T00:00:00Z",
            "available_at": "2027-01-11T00:00:00Z",
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "provenance": {
                "source_reference": "neutral-later-correction",
                "name": "event.json",
                "content_type": "application/json",
            },
            "origin": "AUTHORED_TRAINING_SOURCE",
        },
        content,
    )


def test_existing_http_workroom_collects_actual_source_and_reopens_without_raw_store(
    retained, monkeypatch
):
    case = retained["workrooms"]["ALPHA"]
    baseline = native_rows(retained["world"].database)
    original_init = CompanyStore.__init__
    calls = []

    def guarded(self, *args, **kwargs):
        assert type(self) is not CompanyStore, "Engine must not open a raw company store"
        calls.append(type(self).__name__)
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(CompanyStore, "__init__", guarded)
    app = boot(case)
    client, headers = login(app, case)
    assert calls == ["SharedCompanyStore"]
    assert app.state.engine.company_store.world.database == retained["world"].database
    assert client.get("/api/bootstrap").json()["capabilities"]["company_sources"] is True
    url = "/api/engagements/" + case["engagement"]
    systems = client.get(url + "/company/systems")
    assert systems.status_code == 200, systems.text
    records = client.get(url + "/company/systems/" + SYSTEM + "/records")
    assert records.status_code == 200, records.text
    response = http_command(
        client,
        headers,
        case,
        "pbc.create",
        {
            "title": "Original event",
            "purpose": "Inspect company original",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    assert response.status_code == 200, response.text
    request = response.json()["requests"][-1]["id"]
    assert (
        http_command(client, headers, case, "pbc.issue", {"request_id": request}).status_code == 200
    )
    collected = http_command(
        client,
        headers,
        case,
        "company.collect",
        {
            "system_id": SYSTEM,
            "record_id": "event-one",
            "version": 1,
            "request_id": request,
        },
    )
    assert collected.status_code == 200, collected.text
    artifact = app.state.engine.store.get(case["ids"]["auditor"], case["engagement"])["artifacts"][
        0
    ]
    body = app.state.engine.artifacts.read(artifact)
    assert json.loads(body) == {"engineering_neutral_fixture": True, "revision": 1}
    restarted = boot(case)
    assert restarted.state.engine.artifacts.read(artifact) == body
    assert native_rows(retained["world"].database) == baseline
    with quiescent_read(retained["world"].database) as db:
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM grants WHERE active!=0").fetchone()[0] == 2
    assert not restarted.state.engine.store.get(case["ids"]["auditor"], case["engagement"])[
        "reviews"
    ]


def test_latest_company_checkpoint_and_ordinary_clock_advance_determine_visibility(retained):
    case = retained["workrooms"]["ALPHA"]
    append_correction(retained["world"])
    with pytest.raises(ProcedureError, match="Unreceipted"):
        boot(case)
    config = json.loads(case["config"].read_bytes())
    config["company_lifetime"].update(
        checkpoint=str(retained["world"].checkpoint),
        checkpoint_sha256=retained["world"].checkpoint_sha256,
    )
    case["config"].write_text(json.dumps(config))
    case["config_sha256"] = file_sha(case["config"])
    app = boot(case)
    client, headers = login(app, case)
    url = f"/api/engagements/{case['engagement']}/company/systems/{SYSTEM}/records"
    early = client.get(url).json()
    assert [row["version"] for row in early["records"]] == [1]
    assert client.get(url + "?as_of=2027-01-12T09:00:00Z").status_code == 422
    advanced = http_command(
        client,
        headers,
        case,
        "clock.advance",
        {
            "mode": "TARGET_DATE",
            "target": "2027-01-12T09:00:00Z",
        },
    )
    assert advanced.status_code == 200, advanced.text
    assert [row["version"] for row in client.get(url).json()["records"]] == [2]
    reopened = boot(case)
    assert reopened.state.engine.store.get(case["ids"]["auditor"], case["engagement"])[
        "simulated_at"
    ].startswith("2027-01-12")


def test_cross_workroom_private_and_source_replacement_routes_are_denied_without_mutation(retained):
    case = retained["workrooms"]["ALPHA"]
    app = boot(case)
    client, headers = login(app, case)
    foreign = retained["workrooms"]["BETA"]["engagement"]
    state = app.state.engine.store.get(case["ids"]["auditor"], case["engagement"])
    audit_before = file_sha(case["root"] / "engagements.sqlite3")
    company_before = file_sha(retained["world"].database)
    assert client.get("/api/engagements/" + foreign).status_code == 403
    assert client.post("/api/engagements", json={}, headers=headers).status_code == 403
    assert client.get(f"/api/engagements/{case['engagement']}/instructor/keys").status_code == 403
    assert client.get("/api/private-corpus").status_code == 403
    for kind in ("scope.update", "scenario.build", "generation.retry", "company.activate"):
        response = http_command(client, headers, case, kind, {})
        assert response.status_code == 403, response.text
    assert app.state.engine.store.get(case["ids"]["auditor"], case["engagement"]) == state
    assert file_sha(case["root"] / "engagements.sqlite3") == audit_before
    assert file_sha(retained["world"].database) == company_before
    response = client.get("/api/bootstrap")
    assert response.status_code == 200
    assert (
        "checkpoint_sha256" not in response.text and "accepted_baseline_pins" not in response.text
    )


@pytest.mark.parametrize("tamper", ["config", "binding", "pack", "code"])
def test_external_operator_pins_reject_changed_inputs_before_opening_engine(
    retained, tamper, monkeypatch
):
    case = retained["workrooms"]["ALPHA"]
    if tamper == "code":
        config = json.loads(case["config"].read_bytes())
        config["code_pins"]["service.py"] = "0" * 64
        case["config"].write_text(json.dumps(config))
        case["config_sha256"] = file_sha(case["config"])
    else:
        target = case[tamper] if tamper != "pack" else retained["pack"]
        target.write_bytes(target.read_bytes() + b" ")

    def forbidden(*args, **kwargs):
        pytest.fail("Rejected custody inputs must not instantiate the workroom Engine")

    monkeypatch.setattr(Engine, "__init__", forbidden)
    with pytest.raises(ProcedureError, match="changed"):
        boot(case)


@pytest.mark.parametrize("tamper", ["membership", "roles", "branch", "initial-clock", "task-count"])
def test_resealed_binding_cannot_substitute_retained_identity_birth_or_branch(retained, tamper):
    case = retained["workrooms"]["ALPHA"]
    if tamper in {"membership", "roles"}:
        with case["engine"].store.connect() as db:
            if tamper == "membership":
                db.execute(
                    "UPDATE members SET permission='review' WHERE principal=?",
                    (case["ids"]["auditor"],),
                )
            else:
                db.execute(
                    "UPDATE principals SET roles='[\"instructor\"]' WHERE id=?",
                    (case["ids"]["auditor"],),
                )
    else:
        binding = json.loads(case["binding"].read_bytes())
        if tamper == "branch":
            binding["branch"] = "BETA"
        elif tamper == "initial-clock":
            binding["initial_simulated_at"] = "2027-01-12T09:00:00Z"
        else:
            binding["task_count"] = True
        case["binding"].write_text(json.dumps(binding))
        config = json.loads(case["config"].read_bytes())
        config["workroom_binding"]["sha256"] = file_sha(case["binding"])
        case["config"].write_text(json.dumps(config))
        case["config_sha256"] = file_sha(case["config"])
    with pytest.raises(ProcedureError, match="differs|changed|differ"):
        boot(case)


def test_runtime_or_company_sidecar_change_after_boot_fails_closed_without_private_details(
    retained,
):
    case = retained["workrooms"]["ALPHA"]
    app = boot(case)
    client, _ = login(app, case)
    lifetime = json.loads(case["config"].read_bytes())["company_lifetime"]
    path = Path(lifetime["runtime_review"])
    path.write_bytes(path.read_bytes() + b" ")
    response = client.get("/api/bootstrap")
    assert response.status_code == 503
    assert response.json() == {
        "error": "Retained company workroom unavailable",
        "code": "SOURCE_UNAVAILABLE",
    }
    assert str(path) not in response.text


def test_held_open_company_wal_is_not_checkpointed_or_deleted_on_boot_failure(retained):
    case = retained["workrooms"]["ALPHA"]
    world = retained["world"]
    writer = sqlite3.connect(world.database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            "INSERT INTO grants VALUES (?,?,?,?,?,?)",
            ("NEUTRAL-EXTRA", "NEUTRAL-ENG", COMPANY, "ALPHA", SYSTEM, 1),
        )
        writer.commit()
        sidecar = Path(str(world.database) + "-wal")
        before = file_sha(sidecar)
        with pytest.raises(ProcedureError, match="sidecars"):
            boot(case)
        assert sidecar.exists() and file_sha(sidecar) == before
    finally:
        writer.close()


def test_retained_voice_and_inference_settings_are_preserved_and_overrides_are_rejected(retained):
    case = retained["workrooms"]["ALPHA"]
    inference, voice = retained["root"] / "inference.json", retained["root"] / "voice.json"
    app = boot(case, inference_config=inference, voice_config=voice)
    assert app.state.engine.inference_config == inference
    assert app.state.engine.voice_config == voice
    assert app.state.engine.capabilities["voice"] is True
    with pytest.raises(ProcedureError, match="overrides"):
        boot(case, company_root=retained["world"].root)
    with pytest.raises(ProcedureError, match="overrides"):
        boot(case, instructor_key_root=retained["root"])


def test_duplicate_operator_json_keys_and_absent_workroom_are_not_auto_initialized(retained):
    case = retained["workrooms"]["ALPHA"]
    case["config"].write_bytes(b'{"schema":"one","schema":"two"}')
    with pytest.raises(ValueError, match="Duplicate"):
        RetainedWorkroom(
            case["config"], file_sha(case["config"]), private_root=case["root"], repository=REPO
        )
    missing = retained["root"] / "never-create-this-audit"
    with pytest.raises(ProcedureError, match="differs"):
        RetainedWorkroom(
            retained["workrooms"]["BETA"]["config"],
            retained["workrooms"]["BETA"]["config_sha256"],
            private_root=missing,
            repository=REPO,
        )
    assert not missing.exists()


@pytest.mark.parametrize(
    "option", ["--persistent-company-config", "--persistent-company-config-sha256"]
)
def test_cli_requires_both_external_config_arguments_before_creating_store(
    tmp_path, option, capsys
):
    from enterprise.audit_suite.__main__ import main

    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("Neutral UI fixture")
    missing = tmp_path / "must-not-create"
    with pytest.raises(SystemExit) as error:
        main(
            [
                "serve",
                "--private-root",
                str(missing),
                "--web-root",
                str(web),
                "--local-http",
                option,
                "0" * 64,
            ]
        )
    assert error.value.code == 2
    assert "required together" in capsys.readouterr().err
    assert not missing.exists()


def test_cli_routes_pinned_existing_workroom_to_existing_loopback_service(retained, monkeypatch):
    import uvicorn

    from enterprise.audit_suite.__main__ import main

    case = retained["workrooms"]["ALPHA"]
    web = retained["root"] / "web"
    web.mkdir(mode=0o700)
    (web / "index.html").write_text("Neutral retained UI fixture")
    launched = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: launched.append((app, options)))
    main(
        [
            "serve",
            "--private-root",
            str(case["root"]),
            "--web-root",
            str(web),
            "--local-http",
            "--persistent-company-config",
            str(case["config"]),
            "--persistent-company-config-sha256",
            case["config_sha256"],
        ]
    )
    assert len(launched) == 1
    app, options = launched[0]
    assert options["host"] == "127.0.0.1" and options["port"] == 8780
    assert app.state.engine.company_store.world.root == retained["world"].root
    client = TestClient(app, base_url="http://localhost")
    assert client.get("/").text == "Neutral retained UI fixture"
    assert not app.state.engine.store.get(case["ids"]["auditor"], case["engagement"])["artifacts"]


def collect_existing_neutral_original(case):
    engine, actor, eid = case["engine"], case["ids"]["auditor"], case["engagement"]
    state = command(
        engine,
        actor,
        eid,
        "pbc.create",
        {
            "title": "Actual neutral original",
            "purpose": "Inspect source receipt custody",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(engine, actor, eid, "pbc.issue", {"request_id": request})
    command(
        engine,
        actor,
        eid,
        "company.collect",
        {
            "system_id": SYSTEM,
            "record_id": "event-one",
            "version": 1,
            "request_id": request,
        },
    )
    return engine.store.get(actor, eid)["artifacts"][0]


def fully_reseal_receipt_type_attack(case, world, field, *, historical_only=False):
    """Repair all event/current/journal hashes, leaving original native bytes intact."""
    artifact = collect_existing_neutral_original(case)
    if historical_only:
        command(
            case["engine"],
            case["ids"]["auditor"],
            case["engagement"],
            "clock.advance",
            {
                "mode": "TARGET_DATE",
                "target": "2027-01-04T09:00:00Z",
            },
        )
    native_before = native_rows(world.database)
    db_path = case["root"] / "engagements.sqlite3"
    with closing(sqlite3.connect(db_path)) as db:
        db.row_factory = sqlite3.Row
        triggers = list(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
        for name, _ in triggers:
            db.execute('DROP TRIGGER "' + name + '"')
        events = list(db.execute("SELECT * FROM events ORDER BY revision"))
        previous = ""
        for number, row in enumerate(events):
            state = json.loads(row["state"])
            for original in state["artifacts"]:
                if not historical_only or number != len(events) - 1:
                    if field == "source_version":
                        original["source"]["receipt"]["source"]["version"] = True
                    elif field == "receipt_bytes":
                        original["source"]["receipt"]["content_bytes"] = True
                    else:
                        original["bytes"] = True
            record = {
                "actor": row["actor"],
                "recorded_at": row["recorded_at"],
                "previous_hash": previous,
                "state": state,
                "command": json.loads(row["command"]),
                "command_id": row["command_id"],
            }
            current_hash = digest(record)
            db.execute(
                "UPDATE events SET state=?,previous_hash=?,hash=? WHERE revision=?",
                (canonical(state), previous, current_hash, row["revision"]),
            )
            previous = current_hash
        db.execute(
            "UPDATE engagements SET state=? WHERE id=?", (canonical(state), case["engagement"])
        )
        for _, sql in triggers:
            db.execute(sql)
        db.commit()
        _history(db)
        assert (
            list(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")) == triggers
        )
    if field in {"source_version", "receipt_bytes"} and not historical_only:
        receipt = artifact["source"]["receipt"]
        if field == "source_version":
            receipt["source"]["version"] = True
        else:
            receipt["content_bytes"] = True
        with closing(sqlite3.connect(world.database)) as db:
            triggers = list(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
            sql = next(sql for name, sql in triggers if name == "no_collection_update")
            db.execute("DROP TRIGGER no_collection_update")
            db.execute(
                "UPDATE collections SET receipt=? WHERE command_id=?",
                (canonical(receipt), receipt["command_id"]),
            )
            db.execute(sql)
            db.commit()
            assert dict(
                db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
            ) == dict(triggers)
    assert native_rows(world.database) == native_before
    return artifact


@pytest.mark.parametrize("field", ["source_version", "receipt_bytes", "artifact_bytes"])
def test_fully_resealed_receipt_boolean_types_are_rejected_with_native_history_unchanged(
    retained, field
):
    case = retained["workrooms"]["ALPHA"]
    fully_reseal_receipt_type_attack(case, retained["world"], field)
    with pytest.raises(ProcedureError, match="Strict.*(version|byte count)"):
        boot(case)


def test_repaired_current_receipt_does_not_hide_boolean_receipt_in_earlier_event(retained):
    case = retained["workrooms"]["ALPHA"]
    fully_reseal_receipt_type_attack(
        case, retained["world"], "source_version", historical_only=True
    )
    current = case["engine"].store.get(case["ids"]["auditor"], case["engagement"])
    assert type(current["artifacts"][0]["source"]["receipt"]["source"]["version"]) is int
    with pytest.raises(ProcedureError, match="Strict retained source version"):
        boot(case)


def test_resealed_boolean_zero_birth_counts_do_not_establish_empty_workroom(retained):
    case = retained["workrooms"]["ALPHA"]
    value = json.loads(case["binding"].read_bytes())
    value["zero_workroom_counts"] = {k: False for k in EMPTY_WORKROOM}
    case["binding"].write_text(json.dumps(value))
    config = json.loads(case["config"].read_bytes())
    config["workroom_binding"]["sha256"] = file_sha(case["binding"])
    case["config"].write_text(json.dumps(config))
    case["config_sha256"] = file_sha(case["config"])
    with pytest.raises(ProcedureError, match="birth binding"):
        boot(case)


def test_repository_file_pins_do_not_admit_a_differently_loaded_module_origin(
    retained, monkeypatch
):
    from enterprise.audit_suite import engine as loaded_engine

    case = retained["workrooms"]["ALPHA"]
    monkeypatch.setattr(
        loaded_engine.__spec__, "origin", str(retained["root"] / "another-engine.py")
    )
    with pytest.raises(ProcedureError, match="loaded module differs"):
        boot(case)
