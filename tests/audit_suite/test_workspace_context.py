from copy import deepcopy

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError
from enterprise.audit_suite.workspace_context import WorkspaceContexts


@pytest.fixture
def workspace(tmp_path):
    engine = Engine(tmp_path / "audit")
    actor = engine.store.provision("Personal investigator", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Context exercise",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={"boundaries": ["corporate"]},
        simulated_at="2027-01-01T00:00:00Z",
        configuration={},
    )
    state["controls"] = [{"id": "C1", "title": "Neutral control"}]
    state["tasks"] = [{"id": "T1", "control_id": "C1", "status": "NOT_STARTED"}]
    state["artifacts"] = [
        {"id": "A1", "sha256": "a" * 64, "version": 2, "coverage": {"control_id": "C1"}}
    ]
    state["workpapers"] = [
        {
            "id": "W1",
            "control_id": "C1",
            "prepared_by": actor,
            "versions": [{"version": 1, "text": "Original work"}],
        }
    ]
    state = engine.store.create(actor, state, "create")
    private = tmp_path / "contexts"
    private.mkdir(mode=0o700)
    contexts = WorkspaceContexts(private, engine, max_active=2)
    return contexts, engine, actor, state


def payload(contexts, actor, state):
    return {
        "title": "My question",
        "question": "Which source supports the decision?",
        "next_step": "Inspect the pinned original",
        "links": [
            contexts.make_link(actor, state["id"], kind="artifact", record_id="A1", version=2),
            contexts.make_link(actor, state["id"], kind="workpaper", record_id="W1", version=1),
        ],
    }


def change(engine, actor, state, edit):
    current = engine.store.get(actor, state["id"])
    command = {
        "command_id": f"edit-{current['revision']}",
        "expected_revision": current["revision"],
        "kind": "neutral-test-update",
        "payload": {},
    }

    def reducer(s, *_):
        edit(s)
        return s

    return engine.store.command(actor, state["id"], command, reducer, permissions={"learn"})


def test_only_explicit_user_context_is_saved_without_formal_work(workspace):
    c, e, actor, s = workspace
    assert c.listing(actor, s["id"]) == []
    p = payload(c, actor, s)
    saved = c.create(actor, s["id"], p, command_id="save1")
    assert saved["user"] == p and saved["formal_work_mutated"] is False
    assert c.create(actor, s["id"], p, command_id="save1") == saved
    assert e.store.get(actor, s["id"])["revision"] == s["revision"]
    assert all(x["status"] == "EXACT_PIN_AVAILABLE" for x in saved["link_status"])
    restarted = WorkspaceContexts(c.root, e)
    assert restarted.read(actor, s["id"], saved["id"]) == saved


def test_optimistic_save_reset_and_history_retained(workspace):
    c, e, actor, s = workspace
    p = payload(c, actor, s)
    saved = c.create(actor, s["id"], p, command_id="create")
    p["next_step"] = "Seek corroboration"
    updated = c.save(actor, s["id"], saved["id"], p, expected_version=1, command_id="update")
    assert updated["version"] == 2
    with pytest.raises(DomainError):
        c.save(actor, s["id"], saved["id"], p, expected_version=1, command_id="stale")
    reset = c.reset(actor, s["id"], saved["id"], expected_version=2, command_id="reset")
    assert reset["status"] == "RESET" and reset["user"]["links"] == []
    assert c.listing(actor, s["id"]) == []
    with c._db() as db:
        assert db.execute("SELECT COUNT(*) FROM history").fetchone()[0] == 3


def test_historical_workpaper_and_scope_change_do_not_redirect_links(workspace):
    c, e, actor, s = workspace
    p = payload(c, actor, s)
    saved = c.create(actor, s["id"], p, command_id="save")

    def edit(state):
        state["workpapers"][0]["versions"].append({"version": 2, "text": "Later work"})
        state["scope"]["period_end"] = "2027-12-31"

    change(e, actor, s, edit)
    current = c.read(actor, s["id"], saved["id"])
    assert current["scope_status"] == "SCOPE_CHANGED"
    assert current["link_status"][1]["status"] == "HISTORICAL_VERSION_AVAILABLE"
    assert current["user"]["links"] == p["links"]


def test_missing_changed_and_out_of_scope_links_are_stale(workspace):
    c, e, actor, s = workspace
    p = payload(c, actor, s)
    p["links"].append(c.make_link(actor, s["id"], kind="task", record_id="T1"))
    saved = c.create(actor, s["id"], p, command_id="save")

    def edit(state):
        state["tasks"] = []
        state["artifacts"][0]["sha256"] = "b" * 64

    change(e, actor, s, edit)
    current = c.read(actor, s["id"], saved["id"])
    assert [r["status"] for r in current["link_status"]] == [
        "CONTENT_CHANGED",
        "EXACT_PIN_AVAILABLE",
        "MISSING",
    ]
    with pytest.raises(DomainError):
        c.save(actor, s["id"], saved["id"], p, expected_version=1, command_id="bad")
    change(e, actor, s, lambda state: state.update(controls=[]))
    assert c.read(actor, s["id"], saved["id"])["link_status"][0]["status"] == "OUT_OF_SCOPE"


def test_other_principal_and_revoked_membership_cannot_read(workspace):
    c, e, actor, s = workspace
    saved = c.create(actor, s["id"], payload(c, actor, s), command_id="save")
    other = e.store.provision("Other", ["learner"])["id"]
    e.store.grant(s["id"], other, "learn")
    assert c.listing(other, s["id"]) == []
    with pytest.raises(DomainError):
        c.read(other, s["id"], saved["id"])
    with e.store.connect() as db:
        db.execute("DELETE FROM members WHERE engagement=? AND principal=?", (s["id"], actor))
    with pytest.raises(DomainError):
        c.read(actor, s["id"], saved["id"])


@pytest.mark.parametrize(
    "fault", ["question", "hidden_kind", "wrong_version", "duplicate", "extra"]
)
def test_invalid_or_unpinned_payload_never_creates_context(workspace, fault):
    c, e, actor, s = workspace
    p = deepcopy(payload(c, actor, s))
    if fault == "question":
        p["question"] = ""
    elif fault == "hidden_kind":
        p["links"][0]["kind"] = "instructor_key"
    elif fault == "wrong_version":
        p["links"][1]["version"] = 2
    elif fault == "duplicate":
        p["links"].append(p["links"][0])
    else:
        p["auto_infer"] = True
    with pytest.raises(DomainError):
        c.create(actor, s["id"], p, command_id="invalid")
    assert c.listing(actor, s["id"]) == []


def test_population_selection_links_keep_exact_scope_and_membership(workspace):
    import json

    c, e, actor, s = workspace

    def add(state):
        state["scope"].update(period_start="2027-01-01", period_end="2027-12-31", timezone="UTC")
        state["populations"] = [
            {
                "id": "POP1",
                "version": 1,
                "immutable": {
                    "scope_json": json.dumps(
                        {
                            "boundary_id": "corporate",
                            "period_start": "2027-01-01T00:00:00Z",
                            "period_end": "2027-12-31T23:59:59Z",
                        }
                    ),
                    "records_json": ['{"id":"ITEM1"}'],
                },
            }
        ]
        state["selections"] = [
            {"id": "SEL1", "population_id": "POP1", "immutable": {"selected_ids": ["ITEM1"]}}
        ]

    change(e, actor, s, add)
    p = payload(c, actor, s)
    p["links"] += [
        c.make_link(actor, s["id"], kind="population", record_id="POP1", version=1),
        c.make_link(actor, s["id"], kind="selection", record_id="SEL1"),
    ]
    saved = c.create(actor, s["id"], p, command_id="population-context")
    change(e, actor, s, lambda state: state["scope"].update(period_start="2027-02-01"))
    current = c.read(actor, s["id"], saved["id"])
    assert [r["status"] for r in current["link_status"]][-2:] == ["OUT_OF_SCOPE", "OUT_OF_SCOPE"]
    assert current["user"]["links"] == p["links"]


def test_context_limit_and_typed_versions(workspace):
    c, e, actor, s = workspace
    p = payload(c, actor, s)
    with pytest.raises(DomainError):
        c.make_link(actor, s["id"], kind="artifact", record_id="A1", version=2.0)
    for key in ["one", "two"]:
        c.create(actor, s["id"], p, command_id=key)
    with pytest.raises(DomainError, match="limit"):
        c.create(actor, s["id"], p, command_id="three")
