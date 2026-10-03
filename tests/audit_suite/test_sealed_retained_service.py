"""Company-before-audit ordinary collection into the opt-in sealed journal."""

import json

import pytest

from enterprise.audit_suite.history_inspection import inspect_history
from enterprise.audit_suite.persistent_company_service import (
    create_retained_app,
    sealed_configuration,
)
from enterprise.audit_suite.sealed_history_store import prepare_tail
from enterprise.audit_suite.source_library_audit import file_sha
from tests.audit_suite.test_persistent_company_service import (
    REPO,
    SYSTEM,
    command,
    http_command,
    login,
)

pytest_plugins = [
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
]


def seal(case, *, state_codec=False):
    store = case["engine"].store
    case["prefix_sha"] = file_sha(store.db_path)
    choice = prepare_tail(
        store,
        case["ids"]["operator"],
        case["engagement"],
        case["root"].parent / (case["root"].name + "-tail"),
        state_codec=state_codec,
    )
    config = json.loads(case["config"].read_bytes())
    config = sealed_configuration(
        config,
        choice,
        json.loads(open(choice["path"]).read())["initial_authority_head"],
        repository=REPO,
    )
    case["config"].write_text(json.dumps(config))
    case["config_sha256"] = file_sha(case["config"])
    return choice


def boot(case):
    return create_retained_app(
        case["root"],
        case["config"],
        case["config_sha256"],
        repository=REPO,
        allowed_hosts=["testserver"],
    )


def test_ordinary_collection_tail_and_reopen_preserve_original_native_history(retained):
    case = retained["workrooms"]["ALPHA"]
    # An actual ordinary collection exists in the prefix before publication.
    created = command(
        case["engine"],
        case["ids"]["auditor"],
        case["engagement"],
        "pbc.create",
        {
            "title": "Native event",
            "purpose": "Inspect original",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = created["requests"][-1]["id"]
    command(
        case["engine"],
        case["ids"]["auditor"],
        case["engagement"],
        "pbc.issue",
        {"request_id": request},
    )
    command(
        case["engine"],
        case["ids"]["auditor"],
        case["engagement"],
        "company.collect",
        {"system_id": SYSTEM, "record_id": "event-one", "version": 1, "request_id": request},
    )
    old_history = case["engine"].store.history(case["ids"]["operator"], case["engagement"])
    seal(case)
    app = boot(case)
    client, headers = login(app, case)
    response = http_command(
        client,
        headers,
        case,
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2027-01-12T09:00:00Z"},
    )
    assert response.status_code == 200, response.text
    room = app.state.retained_workroom
    room.refresh_integrity(case["ids"]["operator"])
    state = app.state.engine.store.get(case["ids"]["auditor"], case["engagement"])
    inspected = inspect_history(
        app.state.engine.store,
        case["ids"]["operator"],
        case["engagement"],
        revisions=[0, state["revision"]],
    )
    assert inspected["selected"][0] == old_history[0]
    assert inspected["count"] == len(old_history) + 1
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]
    reopened = boot(case)
    assert (
        reopened.state.engine.store.get(case["ids"]["auditor"], case["engagement"])["simulated_at"]
        == state["simulated_at"]
    )


def test_signed_rotation_reopen_requires_new_external_head(retained):
    case = retained["workrooms"]["ALPHA"]
    seal(case)
    app = boot(case)
    store = app.state.engine.store
    new = store.rotate_credential(case["ids"]["operator"], lifetime=3600)
    with pytest.raises(Exception, match="head|sequence|authority"):
        boot(case)
    config = json.loads(case["config"].read_bytes())
    config["authority_head"] = new["authority_head"]
    case["config"].write_text(json.dumps(config))
    case["config_sha256"] = file_sha(case["config"])
    reopened = boot(case)
    assert (
        reopened.state.engine.store.authenticate(new["credential"])["id"] == case["ids"]["operator"]
    )
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]


def test_signed_downgrade_preserves_other_learner_history_and_company_access(retained):
    case = retained["workrooms"]["ALPHA"]
    seal(case)
    app = boot(case)
    store = app.state.engine.store
    store.grant(case["engagement"], case["ids"]["operator"], "learn")
    config = json.loads(case["config"].read_bytes())
    config["authority_head"] = store.authority_head
    case["config"].write_text(json.dumps(config))
    case["config_sha256"] = file_sha(case["config"])
    reopened = boot(case)
    client, _headers = login(reopened, case)
    url = "/api/engagements/" + case["engagement"]
    assert client.get(url + "/company/systems").status_code == 200
    inspected = inspect_history(
        reopened.state.engine.store, case["ids"]["auditor"], case["engagement"], revisions=[0]
    )
    assert inspected["selected"][0]["state"]["created_by"] == case["ids"]["operator"]
    assert (
        reopened.state.engine.store.membership(case["ids"]["operator"], case["engagement"])
        == "learn"
    )
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]


def explained(keycase):
    from enterprise.audit_suite.retained_explanation_service import create_explained_app

    case = keycase["case"]
    config = json.loads(keycase["config"].read_bytes())
    config["retained_workroom"]["sha256"] = case["config_sha256"]
    keycase["config"].write_text(json.dumps(config))
    keycase["config_sha256"] = file_sha(keycase["config"])
    return create_explained_app(
        case["root"],
        keycase["config"],
        keycase["config_sha256"],
        repository=REPO,
        allowed_hosts=["testserver"],
    )


def test_protected_historical_key_and_complete_packet_include_genuine_new_tail(keycase):
    from enterprise.audit_suite.retained_review_packet import export_packet, verify_packet

    case = keycase["case"]
    seal(case)
    app = explained(keycase)
    client, headers = login(app, case, "operator")
    url = "/api/engagements/" + case["engagement"] + "/instructor-binding"
    assert client.get(url).status_code == 200
    response = http_command(
        client,
        headers,
        case,
        "note.create",
        {"title": "Genuine new note", "text": "Kept in the ordinary tail."},
    )
    assert response.status_code == 200, response.text
    assert client.get(url).status_code == 200
    output = case["root"].parent / "sealed-complete-packet"
    packet = export_packet(app.state.engine, case["ids"]["operator"], case["engagement"], output)
    verified = verify_packet(output, packet["manifest_sha256"])
    assert verified["history_events"] == response.json()["revision"] + 1
    assert packet["identity_session_tables_copied"] is False
    assert packet["instructor_key_files_copied"] is False
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]


@pytest.mark.parametrize("state_codec", [False, True])
@pytest.mark.parametrize("change", ["scope", "source_version", "future_clock", "identity", "mode"])
def test_fully_resealed_post_bound_tail_cannot_evade_typed_custody(keycase, change, state_codec):
    from enterprise.audit_suite.store import canonical, digest

    case = keycase["case"]
    seal(case, state_codec=state_codec)
    app = explained(keycase)
    client, headers = login(app, case, "operator")
    url = "/api/engagements/" + case["engagement"] + "/instructor-binding"
    assert client.get(url).status_code == 200
    assert (
        http_command(
            client,
            headers,
            case,
            "note.create",
            {"title": "Tail before counter", "text": "Actual normal command."},
        ).status_code
        == 200
    )
    store = app.state.engine.store
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        table = store.event_table
        trigger_name = table + "_no_update"
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name=?", (trigger_name,)
        ).fetchone()[0]
        row = db.execute("SELECT * FROM event_tail ORDER BY revision DESC LIMIT 1").fetchone()
        state = json.loads(row["state"])
        if change == "scope":
            state["scope"]["soc2_categories"] = ["Privacy"]
        elif change == "source_version":
            state["artifacts"][0]["source"]["receipt"]["source"]["version"] = True
        elif change == "identity":
            state["id"] = "ENG-FOREIGN-UNREGISTERED"
        elif change == "mode":
            state["mode"] = "MESSY"
        else:
            state["simulated_at"] = "2099-01-01T00:00:00Z"
        record = {k: row[k] for k in ("actor", "recorded_at", "previous_hash", "command_id")} | {
            "state": state,
            "command": json.loads(row["command"]),
        }
        if change == "future_clock":
            record["recorded_at"] += 10**10
        db.execute("DROP TRIGGER " + trigger_name)
        stored = canonical(state)
        if state_codec:
            import hashlib

            from enterprise.audit_suite.canonical_state_codec import encode

            root, size = encode(db, state)
            stored = canonical(
                {"root": root, "bytes": size, "sha256": hashlib.sha256(stored.encode()).hexdigest()}
            )
        db.execute(
            f"UPDATE main.{table} SET state=?,hash=?,recorded_at=? WHERE revision=?",
            (stored, digest(record), record["recorded_at"], row["revision"]),
        )
        db.execute(
            "UPDATE engagements SET state=? WHERE id=?", (canonical(state), case["engagement"])
        )
        db.execute(trigger)
        if state_codec:
            # Remove superseded unreferenced nodes, preserving exact schema;
            # this counter must pass full graph/hash integrity first.
            roots = [store.state_codec["initial_root"]] + [
                json.loads(r[0])["root"] for r in db.execute("SELECT state FROM main.event_frames")
            ]
            seen, stack = set(), list(roots)
            while stack:
                identifier = stack.pop()
                if identifier in seen:
                    continue
                seen.add(identifier)
                node = db.execute(
                    "SELECT kind,payload FROM state_nodes WHERE id=?", (identifier,)
                ).fetchone()
                if node[0] == "C":
                    stack.extend(json.loads(node[1]))
            node_trigger = db.execute(
                "SELECT sql FROM sqlite_master WHERE name='state_nodes_no_delete'"
            ).fetchone()[0]
            db.execute("DROP TRIGGER state_nodes_no_delete")
            for (identifier,) in db.execute("SELECT id FROM state_nodes").fetchall():
                if identifier not in seen:
                    db.execute("DELETE FROM state_nodes WHERE id=?", (identifier,))
            db.execute(node_trigger)
            store.verify_codec(db)
            from enterprise.audit_suite.recovery import _history

            assert _history(db)[case["engagement"]]["events"] == row["revision"] + 1
    assert client.get(url).status_code == 503
    learner, _ = login(app, case)
    assert learner.get(
        "/api/engagements/" + case["engagement"] + "/company/systems"
    ).status_code == (404 if change == "identity" else 200)
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]


@pytest.mark.parametrize("change", ["logout", "snapshot"])
def test_private_response_closes_after_actual_handler_over_session_and_key_members(keycase, change):
    case = keycase["case"]
    seal(case)
    app = explained(keycase)
    client, _ = login(app, case, "operator")
    url = "/api/engagements/" + case["engagement"] + "/instructor-binding"
    assert client.get(url).status_code == 200
    route = next(
        r
        for r in app.router.routes
        if getattr(r, "path", None) == ("/api/engagements/{engagement_id}/instructor-binding")
    )
    original = route.dependant.call

    async def after_handler(*args, **kwargs):
        response = await original(*args, **kwargs)
        if change == "logout":
            request = kwargs["request"]
            token = next(v for k, v in request.cookies.items() if k.startswith("sh_audit_session_"))
            app.state.engine.store.logout(token)
        else:
            member = keycase["snapshot"] / "snapshot.json"
            member.write_bytes(member.read_bytes() + b" ")
        return response

    route.dependant.call = after_handler
    response = client.get(url)
    assert response.status_code == (401 if change == "logout" else 503), response.text
    assert "snapshot" not in response.json()
    learner, _ = login(app, case)
    assert (
        learner.get("/api/engagements/" + case["engagement"] + "/company/systems").status_code
        == 200
    )
    assert file_sha(case["root"] / "engagements.sqlite3") == case["prefix_sha"]
