import copy
from types import SimpleNamespace

import pytest
from test_audit_readiness import projection

from enterprise.audit_suite import work_guidance as guidance
from enterprise.audit_suite.store import DomainError, Store, canonical, digest


@pytest.fixture
def environment(tmp_path):
    store = Store(tmp_path / "audit")
    actor = store.provision("Investigator", ["learner"])["id"]
    state = projection()
    state.update(
        configuration={},
        phase="ACTIVE",
        simulated_at="2028-01-01T00:00:00Z",
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
    )
    state = store.create(actor, state, "create")

    def get(who, eid):
        result = store.get(who, eid)
        result["permissions"] = [store.membership(who, eid)]
        result.pop("configuration", None)  # shared learners receive no full configuration
        return result

    engine = SimpleNamespace(store=store, get=get)
    root = tmp_path / "guidance"
    root.mkdir(mode=0o700)
    core = guidance.WorkGuidance(root, engine)
    return core, actor, state


def mutate(core, actor, state, fn):
    def reducer(s, c, a):
        fn(s)
        return s

    return core.engine.store.command(
        actor,
        state["id"],
        {
            "command_id": "change-" + str(state["revision"]),
            "expected_revision": state["revision"],
            "kind": "fixture",
            "payload": {},
        },
        reducer,
        permissions={"learn", "instruct", "review"},
    )


def allow(core, actor, state):
    return mutate(
        core,
        actor,
        state,
        lambda s: s["configuration"].update(
            work_guidance_allowed=True, work_guidance_policy_revision=s["revision"] + 1
        ),
    )


def enable(core, actor, state, command="opt-in"):
    status = core.status(actor, state["id"])
    return core.opt_in(
        actor,
        state["id"],
        True,
        "Explicit administrative help requested",
        expected_version=status["version"],
        expected_engagement_revision=state["revision"],
        command_id=command,
    )


def reveal(core, actor, state, command="show"):
    ref = core.status(actor, state["id"])["contexts"][0]["reference"]
    return core.reveal(
        actor, state["id"], ref, expected_engagement_revision=state["revision"], command_id=command
    )


def test_default_off_never_computes_or_exposes_guidance(environment, monkeypatch):
    core, actor, state = environment
    monkeypatch.setattr(
        guidance, "summarize", lambda *a: pytest.fail("Readiness must not run while off")
    )
    assert core.status(actor, state["id"])["status"] == "POLICY_DISABLED"
    with pytest.raises(DomainError):
        enable(core, actor, state)
    state = allow(core, actor, state)
    status = core.status(actor, state["id"])
    assert (
        status["status"] == "OPT_IN_REQUIRED"
        and status["contexts"] == []
        and "candidates" not in status
    )
    enabled = enable(core, actor, state)
    assert enabled["opted_in"] and enabled["contexts"] and "candidates" not in enabled


def test_explicit_reveal_exact_refs_and_private_decision_reload(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    before = copy.deepcopy(core.engine.store.get(actor, state["id"]))
    result = reveal(core, actor, state)
    assert result["status"] == "AVAILABLE" and len(result["candidates"]) == 3
    artifact = next(
        c for c in result["candidates"] if c["code"] == "RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK"
    )
    assert artifact["references"][0]["reference"] == {
        "kind": "artifact",
        "id": "A1",
        "version": 2,
        "sha256": "a" * 64,
    }
    assert "judgment" in artifact["reason"]
    chosen = result["candidates"][0]
    decision = core.decide(
        actor,
        state["id"],
        chosen["id"],
        chosen["sha256"],
        "DISMISS",
        "Already considered; retain original reasoning",
        expected_engagement_revision=state["revision"],
        command_id="dismiss",
    )
    assert decision["decision"]["action"] == "DISMISS"
    reloaded = guidance.WorkGuidance(core.root, core.engine)
    again = reveal(reloaded, actor, state, "show-again")
    assert again["candidates"][0]["decision"]["rationale"].startswith("Already considered")
    assert core.engine.store.get(actor, state["id"]) == before
    assert (
        guidance.validate_archive(core.snapshot())["restoration"]
        == "INERT_ONLY_NO_ACTIVE_REHYDRATION"
    )


@pytest.mark.parametrize("change", ["scope", "binding", "artifact", "policy_epoch", "permission"])
def test_changed_basis_redacts_rationale_requires_new_opt_in(environment, change):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    reveal(core, actor, state)
    if change == "permission":
        with core.engine.store.connect() as db:
            db.execute(
                "UPDATE members SET permission=? WHERE engagement=? AND principal=?",
                ("review", state["id"], actor),
            )
    else:

        def modify(s):
            if change == "scope":
                s["scope"]["period_end"] = "2028-12-31"
            elif change == "binding":
                s["company_source_binding"] = {"company": "CO", "branch": "other"}
            elif change == "artifact":
                s["artifacts"][0]["sha256"] = "b" * 64
            else:
                s["configuration"]["work_guidance_policy_revision"] += 1

        state = mutate(core, actor, state, modify)
    status = core.status(actor, state["id"])
    assert status["status"] == "CONTEXT_CHANGED" and not status["personal_content_visible"]
    assert not status["opted_in"] and status["contexts"] == [] and "preference" not in status


def test_policy_disable_then_enable_does_not_restore_opt_in(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    state = mutate(
        core,
        actor,
        state,
        lambda s: s["configuration"].update(
            work_guidance_allowed=False, work_guidance_policy_revision=s["revision"] + 1
        ),
    )
    assert core.status(actor, state["id"])["status"] == "POLICY_DISABLED"
    state = allow(core, actor, state)
    assert core.status(actor, state["id"])["status"] == "CONTEXT_CHANGED"


def test_private_command_replay_and_opt_out_prevent_old_reveal(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    status = enable(core, actor, state)
    ref = status["contexts"][0]["reference"]
    first = reveal(core, actor, state)
    same = core.reveal(
        actor, state["id"], ref, expected_engagement_revision=state["revision"], command_id="show"
    )
    assert first == same
    with pytest.raises(DomainError):
        core.reveal(
            actor,
            state["id"],
            {**ref, "id": "C2"},
            expected_engagement_revision=state["revision"],
            command_id="show",
        )
    core.opt_in(
        actor,
        state["id"],
        False,
        "Continue without guidance",
        expected_version=first["version"],
        expected_engagement_revision=state["revision"],
        command_id="disable",
    )
    old = core.reveal(
        actor, state["id"], ref, expected_engagement_revision=state["revision"], command_id="show"
    )
    assert not old["opted_in"] and "candidates" not in old and old["contexts"] == []


def test_workpaper_exact_current_version_no_old_candidate_substitution(environment):
    core, actor, state = environment
    state = mutate(
        core,
        actor,
        state,
        lambda s: s["workpapers"].append(
            {
                "id": "W1",
                "control_id": "C1",
                "prepared_by": actor,
                "versions": [{"version": 1, "actor": actor, "evidence_ids": ["A1"]}],
            }
        ),
    )
    state = allow(core, actor, state)
    enable(core, actor, state)
    result = reveal(core, actor, state)
    candidate = next(
        c
        for c in result["candidates"]
        if c["code"] == "NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD"
    )
    pin = candidate["references"][0]["reference"]
    assert pin["version"] == 1
    assert pin["sha256"] == digest(
        core.engine.get(actor, state["id"])["workpapers"][0]["versions"][0]
    )
    state = mutate(
        core,
        actor,
        state,
        lambda s: s["workpapers"][0]["versions"].append(
            {"version": 2, "actor": actor, "evidence_ids": ["A1"], "text": "Changed"}
        ),
    )
    with pytest.raises(DomainError):
        core.decide(
            actor,
            state["id"],
            candidate["id"],
            candidate["sha256"],
            "REVIEW",
            "Old version checked",
            expected_engagement_revision=state["revision"],
            command_id="stale",
        )
    updated = reveal(core, actor, state, "new-reveal")
    now = next(c for c in updated["candidates"] if c["code"] == candidate["code"])
    assert (
        now["references"][0]["reference"]["version"] == 2 and now["sha256"] != candidate["sha256"]
    )
    assert candidate["references"][0]["reference"] == pin


def test_missing_original_is_non_navigable_not_adverse_conclusion(environment):
    core, actor, state = environment
    state = mutate(
        core,
        actor,
        state,
        lambda s: s["workpapers"].append(
            {
                "id": "W1",
                "control_id": "C1",
                "versions": [{"version": 1, "evidence_ids": ["MISSING"]}],
            }
        ),
    )
    state = allow(core, actor, state)
    enable(core, actor, state)
    candidate = next(
        c
        for c in reveal(core, actor, state)["candidates"]
        if c["code"] == "WORKPAPER_REFERENCES_MISSING_ARTIFACT"
    )
    assert candidate["references"] == [
        {"kind": "artifact", "id": "MISSING", "status": "UNAVAILABLE", "reference": None}
    ]
    assert "not proof" in candidate["reason"]


def test_cross_actor_and_engagement_isolation(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    other = core.engine.store.provision("Other investigator", ["learner"])["id"]
    with pytest.raises(DomainError):
        core.status(other, state["id"])
    with core.engine.store.connect() as db:
        db.execute("INSERT INTO members VALUES (?,?,?)", (state["id"], other, "learn"))
    assert core.status(other, state["id"])["version"] == 0
    assert core.status(other, state["id"])["status"] == "OPT_IN_REQUIRED"
    second = core.engine.store.create(
        actor,
        {
            **projection(),
            "configuration": {"work_guidance_allowed": True, "work_guidance_policy_revision": 1},
        },
        "second",
    )
    assert core.status(actor, second["id"])["version"] == 0


def test_revocation_during_reveal_rolls_back_private_event(environment, monkeypatch):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    before = core.snapshot()["rows"]
    original = guidance.summarize

    def revoke(projected):
        result = original(projected)
        with core.engine.store.connect() as db:
            db.execute("UPDATE principals SET revoked=1 WHERE id=?", (actor,))
        return result

    monkeypatch.setattr(guidance, "summarize", revoke)
    with pytest.raises(DomainError):
        reveal(core, actor, state)
    assert core.snapshot()["rows"] == before


def test_reserved_final_opt_out_after_history_limit(environment, monkeypatch):
    monkeypatch.setattr(guidance, "MAX_EVENTS", 2)
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    shown = reveal(core, actor, state)
    with pytest.raises(DomainError):
        reveal(core, actor, state, "over-limit")
    final = core.opt_in(
        actor,
        state["id"],
        False,
        "Stop guidance at quota",
        expected_version=shown["version"],
        expected_engagement_revision=state["revision"],
        command_id="stop",
    )
    assert not final["opted_in"] and final["version"] == 3
    assert core.snapshot()["rows"][-1]["version"] == 3


@pytest.mark.parametrize("damage", ["actor", "version", "extra", "typed_boolean"])
def test_inert_archive_rejects_re_pinned_malformed_history(environment, damage):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    archive = core.snapshot()
    row = archive["rows"][0]
    body = guidance._json(row["body"])
    if damage == "actor":
        body["actor"] = "other"
    elif damage == "version":
        body["version"] = True
    elif damage == "extra":
        body["unknown"] = "not allowed"
    else:
        body["data"]["enabled"] = 1
    row["body"] = canonical(body)
    row["sha256"] = digest(body)
    with pytest.raises(DomainError):
        guidance.validate_archive(archive)


def test_exact_candidate_required_and_decision_rationale_not_empty(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    candidate = reveal(core, actor, state)["candidates"][0]
    with pytest.raises(DomainError):
        core.decide(
            actor,
            state["id"],
            candidate["id"],
            "f" * 64,
            "DISMISS",
            "reason",
            expected_engagement_revision=state["revision"],
            command_id="wrong-pin",
        )
    with pytest.raises(DomainError):
        core.decide(
            actor,
            state["id"],
            candidate["id"],
            candidate["sha256"],
            "DISMISS",
            " ",
            expected_engagement_revision=state["revision"],
            command_id="no-reason",
        )


def test_private_storage_modes_and_aliases(environment, tmp_path):
    core, actor, state = environment
    assert core.path.stat().st_mode & 0o777 == 0o600
    alias = tmp_path / "alias"
    alias.symlink_to(core.root, target_is_directory=True)
    with pytest.raises(DomainError):
        guidance.WorkGuidance(alias, core.engine)
    core.path.chmod(0o644)
    with pytest.raises(DomainError):
        core.status(actor, state["id"])


def test_outstanding_request_reference_is_exact_and_navigable(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    candidate = next(
        c for c in reveal(core, actor, state)["candidates"] if c["code"] == "OUTSTANDING_RESPONSE"
    )
    assert candidate["references"][0] == {
        "kind": "request",
        "id": "R1",
        "status": "CURRENT",
        "reference": {
            "kind": "request",
            "id": "R1",
            "version": None,
            "sha256": digest(core.engine.get(actor, state["id"])["requests"][0]),
        },
    }


def test_replayed_reveal_shows_current_explicit_decision(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    result = reveal(core, actor, state)
    candidate = result["candidates"][0]
    core.decide(
        actor,
        state["id"],
        candidate["id"],
        candidate["sha256"],
        "REVIEW",
        "Reviewed this recorded reason",
        expected_engagement_revision=state["revision"],
        command_id="reviewed",
    )
    replay = reveal(core, actor, state)
    assert replay["candidates"][0]["decision"]["action"] == "REVIEW"
    assert len(core.snapshot()["rows"]) == 3


def test_candidate_reference_bound_denies_without_partial_disclosure(environment):
    core, actor, state = environment
    state = mutate(
        core,
        actor,
        state,
        lambda s: s["requests"].extend(
            [
                {"id": "R" + str(i), "control_id": "C1", "status": "ISSUED", "artifact_ids": []}
                for i in range(2, 68)
            ]
        ),
    )
    state = allow(core, actor, state)
    enable(core, actor, state)
    before = core.snapshot()["rows"]
    with pytest.raises(DomainError, match="bound"):
        reveal(core, actor, state)
    assert core.snapshot()["rows"] == before


def test_same_view_cas_rejects_conflicting_opt_in(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    with pytest.raises(DomainError, match="version"):
        core.opt_in(
            actor,
            state["id"],
            False,
            "Stale preference",
            expected_version=0,
            expected_engagement_revision=state["revision"],
            command_id="stale-preference",
        )
    assert core.status(actor, state["id"])["opted_in"]


def test_local_review_reference_preserves_control_and_version_boundaries(environment):
    core, actor, state = environment
    state["workpapers"] = [{"id": "W1", "control_id": "C1", "versions": [{"version": 1}]}]
    row = {"id": "RV1", "workpaper_id": "W1", "control_id": "C1", "kind": "HUMAN"}
    assert guidance.current_reference(state, "review", row, None)["sha256"] == digest(row)
    with pytest.raises(DomainError, match="controls differ"):
        guidance.current_reference(state, "review", {**row, "control_id": "OUTSIDE"}, None)
    with pytest.raises(DomainError, match="version"):
        guidance.current_reference(state, "request", {"id": "R1", "version": True}, True)


def test_validated_archive_is_inert_and_new_store_has_no_opt_in(environment, tmp_path):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    reveal(core, actor, state)
    archived = guidance.validate_archive(core.snapshot())
    assert len(archived["rows"]) == 2
    fresh = tmp_path / "fresh-guidance"
    fresh.mkdir(mode=0o700)
    other = guidance.WorkGuidance(fresh, core.engine)
    assert other.status(actor, state["id"])["status"] == "OPT_IN_REQUIRED"
    assert other.snapshot()["rows"] == []
    assert not hasattr(other, "restore")


def test_archive_rejects_orphan_reveal_even_with_recomputed_hash(environment):
    core, actor, state = environment
    state = allow(core, actor, state)
    enable(core, actor, state)
    reveal(core, actor, state)
    archive = core.snapshot()
    row = archive["rows"][1]
    body = guidance._json(row["body"])
    body["version"] = 1
    body["previous_sha256"] = ""
    row["version"] = 1
    row["body"] = canonical(body)
    row["sha256"] = digest(body)
    archive["rows"] = [row]
    with pytest.raises(DomainError, match="explicit opt-in"):
        guidance.validate_archive(archive)
