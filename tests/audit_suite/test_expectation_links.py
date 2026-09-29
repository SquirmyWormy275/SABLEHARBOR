from copy import deepcopy

import pytest

from enterprise.audit_suite.company_federation import CAPABILITIES
from enterprise.audit_suite.explanation_binding import _authored, bind_snapshot, verify_snapshot
from enterprise.audit_suite.instructor_comparison import compare
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_explanation_binding import workspace as base_workspace
from tests.audit_suite.test_instructor_comparison import advance


@pytest.fixture
def workspace(tmp_path):
    return base_workspace.__wrapped__(tmp_path)


def setup(workspace):
    engine, args = workspace

    def add(s):
        s["scope"]["boundaries"] = ["B1"]
        s["tasks"] = [
            {"id": "T1", "control_id": "CONTROL1", "boundary_id": "B1"},
            {"id": "T2", "control_id": "CONTROL1", "boundary_id": "B1"},
        ]
        s["company_source_binding"] = engine.company_bindings[args["engagement_id"]]
        return s

    advance(engine, args, add)
    args["authored"]["expectations"][0]["task_ids"] = ["T1"]
    return engine, args


@pytest.mark.parametrize(
    "fault",
    [
        "unknown",
        "foreign_control",
        "boundary",
        "excluded",
        "prior",
        "duplicate",
        "untyped",
        "removed_control",
    ],
)
def test_rejects_unscoped_authored_task_links(workspace, fault):
    engine, args = setup(workspace)
    state = engine.store.get(args["instructor_id"], args["engagement_id"])
    row = args["authored"]["expectations"][0]
    if fault == "unknown":
        row["task_ids"] = ["FOREIGN-ENGAGEMENT-TASK"]
    elif fault == "foreign_control":
        state["tasks"][0]["control_id"] = "OTHER"
    elif fault == "boundary":
        state["tasks"][0]["boundary_id"] = "OTHER"
    elif fault == "excluded":
        state["tasks"][0]["applicability"] = "EXCLUDED"
    elif fault == "prior":
        state["tasks"][0]["applicability"] = "PRIOR_SCOPE_REQUIRES_REASSESSMENT"
    elif fault == "duplicate":
        row["task_ids"] = ["T1", "T1"]
    elif fault == "untyped":
        row["task_ids"] = "T1"
    else:
        state["controls"] = []
    with pytest.raises(DomainError):
        _authored(args["authored"], {"R1", "R2"}, {"CONTROL1"}, engine.repository, state)


def test_immutable_authored_links_exact_historical_versions_and_unmapped_legacy(workspace):
    engine, args = setup(workspace)
    receipt = bind_snapshot(engine, **args)
    frozen = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    assert frozen["authored"] == args["authored"]
    bindings = {
        args["engagement_id"]: {
            "path": args["output"],
            "manifest_sha256": receipt["manifest_sha256"],
        }
    }
    v1 = {"version": 1, "task_ids": ["T1"], "evidence_ids": [], "actor": args["audited_actor_id"]}

    def first(s):
        s["workpapers"] = [{"id": "W1", "control_id": "CONTROL1", "versions": [deepcopy(v1)]}]
        return s

    initial = advance(engine, args, first)

    def second(s):
        s["workpapers"][0]["versions"].append(
            {"version": 2, "task_ids": ["T2"], "evidence_ids": []}
        )
        return s

    later = advance(engine, args, second)
    for revision in [initial["revision"], later["revision"]]:
        result = compare(
            engine,
            {"id": args["instructor_id"]},
            args["engagement_id"],
            bindings,
            revision=revision,
        )["expectations"][0]
        assert result["task_mapping_status"] == "EXPLICIT_AUTHORED_LINKS"
        linked = result["task_linked_workpaper_versions"]
        assert len(linked) == 1 and linked[0]["version"] == 1
        assert linked[0]["version_sha256"] == digest(v1)
        assert linked[0]["task_ids"] == ["T1"] and linked[0]["source_artifact_ids"] == []
        assert result["source_linked_workpaper_versions"] == []
        assert result["testing"] == "NOT_ASSESSED"

    def exclude(s):
        s["tasks"][0]["applicability"] = "PRIOR_SCOPE_REQUIRES_REASSESSMENT"
        return s

    excluded = advance(engine, args, exclude)
    result = compare(
        engine,
        {"id": args["instructor_id"]},
        args["engagement_id"],
        bindings,
        revision=excluded["revision"],
    )["expectations"][0]
    assert result["authored_task_ids"] == ["T1"]
    assert result["task_mapping_status"] == "UNRESOLVED_IN_SELECTED_SCOPE"
    assert result["task_linked_workpaper_versions"] == []
    assert (
        verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
        == frozen
    )
    from enterprise.audit_suite.expectation_links import inventory

    legacy = deepcopy(args["authored"]["expectations"][0])
    del legacy["task_ids"]
    assert inventory(legacy, ["CONTROL1"], set(), initial)["task_mapping_status"] == "UNMAPPED"
    assert "task_ids" not in legacy


def test_portfolio_capability_only_promotes_supported_binding():
    assert CAPABILITIES["explanation_binding"] is True
    assert CAPABILITIES["global_snapshot"] is False
    assert CAPABILITIES["cross_store_populations"] is False
    assert CAPABILITIES["source_mutation"] is False


def test_task_reference_does_not_promote_unrelated_source_or_later_version():
    from enterprise.audit_suite.expectation_links import inventory

    state = {
        "controls": [{"id": "C"}],
        "tasks": [{"id": "T", "control_id": "C"}],
        "workpapers": [
            {
                "id": "W",
                "control_id": "C",
                "versions": [
                    {"version": 1, "task_ids": ["T"], "evidence_ids": ["EXACT", "UNRELATED"]},
                    {"version": 2, "task_ids": [], "evidence_ids": ["EXACT"]},
                ],
            }
        ],
    }
    rows = inventory({"task_ids": ["T"]}, ["C"], {"EXACT"}, state)["task_linked_workpaper_versions"]
    assert len(rows) == 1
    assert rows[0]["version"] == 1 and rows[0]["source_artifact_ids"] == ["EXACT"]
    assert rows[0]["version_sha256"] == digest(state["workpapers"][0]["versions"][0])
