from copy import deepcopy

import pytest

from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_comparison import compare
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_explanation_binding import workspace as base_workspace


@pytest.fixture
def workspace(tmp_path):
    return base_workspace.__wrapped__(tmp_path)


def bound(workspace):
    engine, args = workspace
    receipt = bind_snapshot(engine, **args)
    bindings = {
        args["engagement_id"]: {
            "path": args["output"],
            "manifest_sha256": receipt["manifest_sha256"],
        }
    }
    return engine, args, bindings


def advance(engine, args, mutate, *, actor=None):
    actor = actor or args["instructor_id"]
    state = engine.store.get(actor, args["engagement_id"])
    return engine.store.command(
        actor,
        args["engagement_id"],
        {
            "command_id": f"update-{state['revision']}",
            "expected_revision": state["revision"],
            "kind": "neutral.update",
            "payload": {},
        },
        lambda s, _command, _actor: mutate(s),
        permissions={"instruct", "learn"},
    )


def test_exact_historical_revision_no_submission_or_missing_issue_grade(workspace):
    engine, args, bindings = bound(workspace)
    result = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0
    )
    assert result["status"] == "DETERMINISTIC_LINK_INVENTORY_ONLY"
    assert result["sources"][0]["status"] == "NO_EXACT_RETAINED_LINK_RECORDED"
    assert result["expectations"][0]["testing"] == "NOT_ASSESSED"
    assert result["submission"] == "NOT_INFERRED_FROM_REVISION"
    assert result["audited_actor_activity"] == []
    assert result["shared_workspace_activity_count"] == 1
    assert result["selected_history_sha256"] == digest(
        engine.store.history(args["instructor_id"], args["engagement_id"])
    )


def test_exact_source_version_links_and_shared_actor_are_separate(workspace):
    engine, args, bindings = bound(workspace)
    source = args["source_refs"][0]
    version = {
        "version": 1,
        "actor": args["instructor_id"],
        "evidence_ids": ["A1"],
        "conclusion": "Recorded assertion",
    }

    def mutate(s):
        s["company_source_binding"] = {"company": "C", "branch": "B"}
        s["artifacts"] = [
            {"id": "A1", "sha256": source["sha256"], "source": {"receipt": {"source": source}}},
            {
                "id": "PRIVATE",
                "audience": "INSTRUCTOR",
                "sha256": source["sha256"],
                "source": {"receipt": {"source": source}},
            },
        ]
        s["workpapers"] = [
            {"id": "W1", "prepared_by": args["instructor_id"], "versions": [version]}
        ]
        s["tasks"] = [{"id": "T1", "control_id": "CONTROL1", "status": "COMPLETE"}]
        s["reviews"] = [
            {
                "id": "RV1",
                "workpaper_id": "W1",
                "workpaper_version": 1,
                "workpaper_version_digest": digest(version),
                "actor": args["instructor_id"],
            }
        ]
        return s

    advance(engine, args, mutate)
    selected = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=1
    )
    assert [a["id"] for a in selected["sources"][0]["exact_retained_artifacts"]] == ["A1"]
    expectation = selected["expectations"][0]
    assert expectation["status"] == "EXPLICIT_SOURCE_LINK_PRESENT"
    assert expectation["source_linked_workpaper_versions"][0]["version_sha256"] == digest(version)
    assert expectation["workpaper_version_reviews"][0]["target_digest_matches"]
    assert selected["audited_actor_activity"] == []
    old = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0
    )
    assert old["sources"][0]["exact_retained_artifacts"] == []

    def mismatch(s):
        s["artifacts"][0]["sha256"] = "f" * 64
        return s

    advance(engine, args, mismatch, actor=args["audited_actor_id"])
    changed = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=2
    )
    assert changed["sources"][0]["exact_retained_artifacts"] == []
    assert changed["sources"][0]["different_version_or_digest_artifact_ids"] == ["A1"]
    assert len(changed["audited_actor_activity"]) == 1


def test_context_mismatch_has_only_metadata_not_partial_comparisons(workspace):
    engine, args, bindings = bound(workspace)

    def mutate(s):
        s["scope"]["period_end"] = "2028-12-31"
        return s

    advance(engine, args, mutate)
    result = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=1
    )
    assert result["status"] == "CONTEXT_MISMATCH"
    assert "expectations" not in result and "sources" not in result


def test_denial_invalid_revision_tamper_and_final_permission_check(workspace, monkeypatch):
    engine, args, bindings = bound(workspace)
    with pytest.raises(DomainError) as denied:
        compare(
            engine, {"id": args["audited_actor_id"]}, args["engagement_id"], bindings, revision=0
        )
    assert denied.value.status == 403
    with pytest.raises(DomainError):
        compare(
            engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=True
        )
    original = engine.store.history

    def tampered(*a):
        result = deepcopy(original(*a))
        result[0]["state"]["scope"] = {"changed": True}
        return result

    monkeypatch.setattr(engine.store, "history", tampered)
    with pytest.raises(DomainError) as bad:
        compare(engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0)
    assert bad.value.status == 503

    def revoked(*a):
        result = original(*a)
        engine.store.grant(args["engagement_id"], args["instructor_id"], "review")
        return result

    monkeypatch.setattr(engine.store, "history", revoked)
    with pytest.raises(DomainError) as denied:
        compare(engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0)
    assert denied.value.status == 403


def test_company_basis_change_blocks_even_matching_historical_scope(workspace):
    engine, args, bindings = bound(workspace)
    engine.company_bindings[args["engagement_id"]] = {"company": "C", "branch": "OTHER"}
    result = compare(
        engine, {"id": args["instructor_id"]}, args["engagement_id"], bindings, revision=0
    )
    assert result["status"] == "CONTEXT_MISMATCH"
    assert "CURRENT_COMPANY_BASIS_DIFFERS_FROM_BOUND_SOURCE" in result["mismatches"]
    assert "sources" not in result


def test_actual_protected_route_and_no_learner_access(workspace):
    from fastapi.testclient import TestClient

    from enterprise.audit_suite.service import create_app
    from tests.audit_suite.test_bound_instructor import configured

    engine, args = workspace
    config, _ = configured(engine, args)
    teacher = engine.store.provision("Route instructor", ["instructor"])
    learner = engine.store.provision("Route learner", ["learner"])
    engine.store.grant(args["engagement_id"], teacher["id"], "instruct")
    engine.store.grant(args["engagement_id"], learner["id"], "learn")
    app = create_app(engine.store.root, instructor_bindings=config, allowed_hosts=["testserver"])
    app.state.engine.company_bindings = engine.company_bindings
    client = TestClient(app, base_url="https://testserver")
    path = f"/api/engagements/{args['engagement_id']}/instructor-comparison?revision=0"
    allowed = client.get(path, headers={"authorization": "Bearer " + teacher["credential"]})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["grading"] == "NOT_PERFORMED"
    denied = client.get(path, headers={"authorization": "Bearer " + learner["credential"]})
    assert denied.status_code == 403
    assert "expectation_id" not in denied.text and "source_id" not in denied.text
    assert client.get(path).status_code == 401
    assert (
        client.get(
            path.replace("revision=0", "revision=999"),
            headers={"authorization": "Bearer " + teacher["credential"]},
        ).status_code
        == 404
    )
