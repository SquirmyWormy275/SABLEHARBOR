import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.bound_instructor import load_bindings, read_binding
from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_access import InstructorAccessLog
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_explanation_binding import workspace as base_workspace


@pytest.fixture
def workspace(tmp_path):
    return base_workspace.__wrapped__(tmp_path)


def configured(engine, args):
    receipt = bind_snapshot(engine, **args)
    config = args["output"].parent / "bindings.json"
    config.write_text(
        json.dumps(
            {
                args["engagement_id"]: {
                    "path": str(args["output"]),
                    "manifest_sha256": receipt["manifest_sha256"],
                }
            }
        )
    )
    config.chmod(0o600)
    return config, receipt


def test_actual_bound_route_authorization_exact_pin_and_no_ordinary_leak(workspace):
    engine, args = workspace
    config, receipt = configured(engine, args)
    teacher = engine.store.provision("Neutral reader", ["instructor"])
    learner = engine.store.provision("Neutral learner", ["learner"])
    engine.store.grant(args["engagement_id"], teacher["id"], "instruct")
    engine.store.grant(args["engagement_id"], learner["id"], "learn")
    app = create_app(engine.store.root, instructor_bindings=config, allowed_hosts=["testserver"])
    client = TestClient(app, base_url="https://testserver")
    base = f"/api/engagements/{args['engagement_id']}"
    headers = {"Authorization": "Bearer " + teacher["credential"]}
    student = {"Authorization": "Bearer " + learner["credential"]}
    before = client.get(base, headers=headers).json()
    assert client.get(base + "/instructor-binding", headers=student).status_code == 403
    response = client.get(base + "/instructor-binding", headers=headers)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["binding"]["manifest_sha256"] == receipt["manifest_sha256"]
    assert value["binding"]["status"] == "MATCHING_REVISION"
    assert value["snapshot"]["professional_validation"] == "UNVALIDATED"
    assert value["snapshot"]["sources"][1]["actor_visibility_at_binding"] == "FUTURE_UNAVAILABLE"
    assert client.get(base, headers=headers).json() == before
    assert "Instructor interpretation" not in client.get(base, headers=student).text
    events = InstructorAccessLog(engine.store.root / "instructor-key-access").verify()
    assert events[-1]["binding_manifest_sha256"] == receipt["manifest_sha256"]
    assert events[-1]["operation"] == "BOUND_SNAPSHOT"
    original = (args["output"] / "snapshot.json").read_bytes()
    (args["output"] / "snapshot.json").write_bytes(original + b" ")
    blocked = client.get(base + "/instructor-binding", headers=headers)
    assert blocked.status_code == 503 and str(args["output"]) not in blocked.text
    assert (args["output"] / "snapshot.json").read_bytes() == original + b" "


def test_historical_revision_remains_pinned_without_rebinding(workspace):
    engine, args = workspace
    config, _ = configured(engine, args)
    bindings = load_bindings(config)
    principal = {"id": args["instructor_id"]}
    first = read_binding(engine, principal, args["engagement_id"], bindings)
    state = engine.store.get(principal["id"], args["engagement_id"])
    engine.store.command(
        principal["id"],
        args["engagement_id"],
        {
            "command_id": "neutral-change",
            "expected_revision": state["revision"],
            "kind": "neutral.change",
            "payload": {},
        },
        lambda s, c, t: {**s, "simulated_at": "2027-06-02T00:00:00Z"},
        permissions={"instruct"},
    )
    later = read_binding(engine, principal, args["engagement_id"], bindings)
    assert later["binding"]["status"] == "HISTORICAL_REVISION"
    assert later["snapshot"] == first["snapshot"]
    assert later["binding"]["current_revision"] > later["binding"]["bound_revision"]


def test_config_rejects_foreign_scope_public_permissions_and_wrong_pin(workspace):
    engine, args = workspace
    config, receipt = configured(engine, args)
    config.chmod(0o644)
    with pytest.raises(DomainError):
        load_bindings(config)
    config.chmod(0o600)
    config.write_text(
        json.dumps(
            {
                "FOREIGN": {
                    "path": str(args["output"]),
                    "manifest_sha256": receipt["manifest_sha256"],
                }
            }
        )
    )
    with pytest.raises(DomainError):
        load_bindings(config)
    config.write_text(
        json.dumps(
            {args["engagement_id"]: {"path": str(args["output"]), "manifest_sha256": "0" * 64}}
        )
    )
    with pytest.raises(DomainError):
        load_bindings(config)
