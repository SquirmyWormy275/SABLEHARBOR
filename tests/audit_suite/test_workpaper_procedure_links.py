from itertools import count

import pytest

from enterprise.audit_suite.audit_readiness import summarize
from enterprise.audit_suite.draft_store import DraftStore
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def workspace(tmp_path):
    engine = Engine(tmp_path / "audit")
    actor = engine.store.provision("Neutral preparer", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        scope={"boundaries": ["corporate"]}, phase="ACTIVE", simulated_at="2027-05-01T09:00:00Z"
    )
    state["controls"] = [{"id": "C1"}, {"id": "C2"}]
    state["tasks"] = [
        {"id": "T1", "control_id": "C1", "status": "NOT_STARTED"},
        {"id": "T2", "control_id": "C2"},
        {"id": "T3", "control_id": "C1", "boundary_id": "other"},
    ]
    state = engine.store.create(actor, state, "create")
    seq = count()

    def command(kind, payload):
        return engine.command(
            actor,
            state["id"],
            {
                "command_id": str(next(seq)),
                "expected_revision": engine.store.get(actor, state["id"])["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    return engine, actor, state, command


def test_versions_preserve_omitted_links_and_clear_explicitly_without_testing_credit(workspace):
    engine, actor, state, command = workspace
    one = command(
        "workpaper.add", {"title": "Neutral paper", "control_id": "C1", "task_ids": ["T1"]}
    )
    wp = one["workpapers"][0]
    two = command("workpaper.update", {"workpaper_id": wp["id"], "text": "Second version"})
    assert two["workpapers"][0]["versions"][1]["task_ids"] == ["T1"]
    three = command("workpaper.update", {"workpaper_id": wp["id"], "task_ids": []})
    assert [v["task_ids"] for v in three["workpapers"][0]["versions"]] == [["T1"], ["T1"], []]
    assert three["tasks"][0]["status"] == "NOT_STARTED"
    report = summarize(three)["controls"][0]["procedures"][0]
    assert len(report["workpaper_links"]) == 2
    assert not report["current_version_link_recorded"]
    assert all(not link["current_version"] for link in report["workpaper_links"])
    assert report["testing_verified"] == "NOT_ASSESSED"


@pytest.mark.parametrize("refs", [["T2"], ["T3"], ["ABSENT"], ["T1", "T1"], "T1", [1], None])
def test_wrong_scope_duplicate_and_malformed_references_atomic(workspace, refs):
    engine, actor, state, command = workspace
    before = engine.store.get(actor, state["id"])
    with pytest.raises(DomainError):
        command("workpaper.add", {"title": "Invalid", "control_id": "C1", "task_ids": refs})
    assert engine.store.get(actor, state["id"]) == before


def test_drafts_roundtrip_links_validate_scope_and_never_mutate_formal_state(workspace):
    engine, actor, state, command = workspace
    drafts = DraftStore(engine.store)
    payload = {
        "command_id": "d1",
        "expected_version": 0,
        "base_workpaper_version": None,
        "fields": {"title": "Draft", "control_id": "C1", "task_ids": ["T1"]},
    }
    saved = drafts.write(actor, state["id"], "workpaper.add", "new", payload)
    assert saved["fields"]["task_ids"] == ["T1"]
    assert drafts.get(actor, state["id"], "workpaper.add", "new")["fields"]["task_ids"] == ["T1"]
    with pytest.raises(DomainError):
        drafts.write(
            actor,
            state["id"],
            "workpaper.add",
            "new",
            {
                **payload,
                "command_id": "bad",
                "expected_version": saved["version"],
                "fields": {**payload["fields"], "task_ids": ["T2"]},
            },
        )
    assert engine.store.get(actor, state["id"])["revision"] == state["revision"]
