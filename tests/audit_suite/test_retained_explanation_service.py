"""Existing protected views over genuine company-before-two-room originals."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_persistent_company_service import COMPANY, SYSTEM, command, login
from test_persistent_company_service import retained as retained_fixture

from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.retained_explanation_service import configuration, create_explained_app
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError

REPO = Path(__file__).resolve().parents[2]
retained = retained_fixture


@pytest.fixture
def keycase(retained):
    world, case = retained["world"], retained["workrooms"]["ALPHA"]
    engine, auditor, engagement = case["engine"], case["ids"]["auditor"], case["engagement"]
    state = command(
        engine,
        auditor,
        engagement,
        "pbc.create",
        {
            "title": "Actual company original",
            "purpose": "Examine existing original",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(engine, auditor, engagement, "pbc.issue", {"request_id": request})
    state = command(
        engine,
        auditor,
        engagement,
        "company.collect",
        {
            "system_id": SYSTEM,
            "record_id": "event-one",
            "version": 1,
            "request_id": request,
        },
    )
    state = engine.store.get(auditor, engagement)
    original = state["artifacts"][0]["source"]["receipt"]["source"]
    source = {
        "id": "native-one",
        **{k: original[k] for k in ("company", "branch", "system", "record", "version", "sha256")},
    }
    world.store.grant(world.operator.principal, engagement, COMPANY, "ALPHA", SYSTEM)
    snapshot = retained["root"] / "alpha-explanation"
    result = bind_snapshot(
        engine,
        instructor_id=case["ids"]["operator"],
        audited_actor_id=auditor,
        engagement_id=engagement,
        source_operator_id=world.operator.principal,
        source_as_of=state["simulated_at"],
        source_refs=[source],
        authored={
            "issues": [
                {
                    "id": "neutral-source-check",
                    "control_ids": ["SH-SEC-003"],
                    "source_ids": ["native-one"],
                    "claim": "Verify the selected original bytes.",
                    "uncertainty": "This is an authored teaching expectation, not effectiveness.",
                }
            ],
            "expectations": [
                {
                    "id": "inspect-original",
                    "issue_ids": ["neutral-source-check"],
                    "procedure": "Inspect the original and its collection custody.",
                    "acceptable_alternatives": ["Compare the retained copy to the native version."],
                }
            ],
            "uncertainty": ["No full-year effectiveness or calibrated grading asserted."],
            "source_pins": {},
        },
        output=snapshot,
    )
    bindings = retained["root"] / "ALPHA-EXPLANATION-BINDINGS.json"
    write(
        bindings,
        {engagement: {"path": str(snapshot), "manifest_sha256": result["manifest_sha256"]}},
    )
    config = retained["root"] / "ALPHA-EXPLANATION-CONFIG.json"
    write(
        config,
        configuration(
            case["config"], case["config_sha256"], bindings, file_sha(bindings), repository=REPO
        ),
    )
    return {
        "retained": retained,
        "case": case,
        "snapshot": snapshot,
        "bindings": bindings,
        "config": config,
        "config_sha256": file_sha(config),
        "before": state,
        "native": native_rows(world.database),
    }


def boot(keycase, **options):
    case = keycase["case"]
    return create_explained_app(
        case["root"],
        keycase["config"],
        keycase["config_sha256"],
        repository=REPO,
        allowed_hosts=["testserver"],
        **options,
    )


def test_existing_instructor_view_uses_same_original_company_and_audit_without_task_credit(keycase):
    app = boot(keycase)
    case = keycase["case"]
    client, _ = login(app, case, "operator")
    response = client.get("/api/engagements/" + case["engagement"] + "/instructor-binding")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["snapshot"]["sources"][0]["retained_audit_artifact_ids"] == [
        keycase["before"]["artifacts"][0]["id"]
    ]
    assert data["snapshot"]["professional_validation"] == "UNVALIDATED"
    assert data["snapshot"]["grading"] == "NOT_PERFORMED"
    capabilities = client.get("/api/bootstrap").json()["capabilities"]
    assert capabilities["bound_instructor_keys"] is True
    assert capabilities["instructor_assessments"] is False
    assert (
        app.state.engine.store.get(case["ids"]["auditor"], case["engagement"]) == keycase["before"]
    )
    assert native_rows(keycase["retained"]["world"].database) == keycase["native"]
    assert not keycase["retained"]["workrooms"]["BETA"]["engine"].store.get(
        keycase["retained"]["workrooms"]["BETA"]["ids"]["auditor"],
        keycase["retained"]["workrooms"]["BETA"]["engagement"],
    )["artifacts"]


@pytest.mark.parametrize("role", ["auditor", "reviewer"])
def test_learner_and_reviewer_cannot_open_private_key_or_use_other_workroom(keycase, role):
    app = boot(keycase)
    case = keycase["case"]
    client, _ = login(app, case, role)
    assert (
        client.get("/api/engagements/" + case["engagement"] + "/instructor-binding").status_code
        == 403
    )
    other = keycase["retained"]["workrooms"]["BETA"]["engagement"]
    assert client.get("/api/engagements/" + other + "/instructor-binding").status_code == 403
    public = client.get("/api/engagements/" + case["engagement"])
    assert public.status_code == 200
    assert "Verify the selected original bytes." not in public.text


def test_private_snapshot_tamper_fails_private_reads_while_learner_keeps_company_access(keycase):
    app = boot(keycase)
    case = keycase["case"]
    operator, _ = login(app, case, "operator")
    learner, _ = login(app, case)
    path = keycase["snapshot"] / "snapshot.json"
    path.write_bytes(path.read_bytes() + b" ")
    url = "/api/engagements/" + case["engagement"]
    assert operator.get(url + "/instructor-binding").status_code == 503
    assert learner.get(url + "/instructor-binding").status_code == 403
    assert learner.get(url + "/company/systems").status_code == 200
    assert learner.get(url).status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        "other_room",
        "wrong_actor",
        "wrong_prefix",
        "wrong_source",
        "boolean_version",
        "captured_grant",
        "captured_visibility",
        "claimed_validation",
        "claimed_grading",
        "authored_unbound_source",
        "authored_unscoped_control",
        "authored_unscoped_task",
        "boolean_watermark",
        "future_watermark",
        "software_claim",
        "source_claim",
    ],
)
def test_resealed_operator_key_cannot_substitute_native_actor_history_or_original(keycase, change):
    snapshot = keycase["snapshot"]
    path = snapshot / "snapshot.json"
    value = json.loads(path.read_bytes())
    if change == "other_room":
        value["company_binding"]["branch"] = "BETA"
    elif change == "wrong_actor":
        value["audited_actor_id"] = keycase["case"]["ids"]["reviewer"]
    elif change == "wrong_prefix":
        value["engagement"]["history_sha256"] = "0" * 64
    elif change == "wrong_source":
        value["sources"][0]["record"] = "another-record"
    elif change == "boolean_version":
        value["sources"][0]["version"] = True
    elif change == "captured_grant":
        value["sources"][0]["actor_granted_at_binding"] = not value["sources"][0][
            "actor_granted_at_binding"
        ]
    elif change == "captured_visibility":
        value["sources"][0]["actor_visibility_at_binding"] = "ACCESS_NOT_GRANTED"
    elif change == "claimed_validation":
        value["professional_validation"] = "VALIDATED"
    elif change == "claimed_grading":
        value["grading"] = "PERFORMED"
    elif change == "authored_unbound_source":
        value["authored"]["issues"][0]["source_ids"] = ["unbound"]
    elif change == "authored_unscoped_control":
        value["authored"]["issues"][0]["control_ids"] = ["SH-UNKNOWN"]
    elif change == "authored_unscoped_task":
        value["authored"]["expectations"][0]["task_ids"] = ["TASK-UNKNOWN"]
    elif change == "boolean_watermark":
        value["access_event_watermark"] = True
    elif change == "future_watermark":
        value["access_event_watermark"] += 100000
    elif change == "software_claim":
        value["software_verified"].append("Professional assurance")
    else:
        value["sources"][0]["fact_verification"] = "PROFESSIONALLY_VALIDATED"
    path.write_text(json.dumps(value, sort_keys=True))
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    manifest["files"]["snapshot.json"] = file_sha(path)
    (snapshot / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    index = json.loads(keycase["bindings"].read_bytes())
    index[keycase["case"]["engagement"]]["manifest_sha256"] = file_sha(snapshot / "manifest.json")
    keycase["bindings"].write_text(json.dumps(index, sort_keys=True))
    config = deepcopy(json.loads(keycase["config"].read_bytes()))
    config["explanation_bindings"]["sha256"] = file_sha(keycase["bindings"])
    keycase["config"].write_text(json.dumps(config, sort_keys=True))
    keycase["config_sha256"] = file_sha(keycase["config"])
    with pytest.raises((ProcedureError, ValueError, RuntimeError, DomainError)):
        boot(keycase)


def test_new_ordinary_work_keeps_exact_old_key_as_historical_without_rebinding_sources(keycase):
    case = keycase["case"]
    command(
        case["engine"],
        case["ids"]["auditor"],
        case["engagement"],
        "note.create",
        {"title": "Later ordinary note", "text": "Original remains the same."},
    )
    app = boot(keycase)
    client, _ = login(app, case, "operator")
    response = client.get("/api/engagements/" + case["engagement"] + "/instructor-binding")
    assert response.status_code == 200, response.text
    assert response.json()["binding"]["status"] == "HISTORICAL_REVISION"


def test_key_wrapper_does_not_accept_other_source_or_archive_overrides(keycase):
    with pytest.raises(ProcedureError, match="overrides"):
        boot(keycase, company_root=Path("/unused"))
