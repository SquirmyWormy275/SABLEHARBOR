import copy
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import generation, review
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, canonical, digest


def fixture(tmp_path):
    engine = Engine(tmp_path / "state")
    user = engine.store.provision("Learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Scoped five-layer fixture",
        phase="ACTIVE",
        discipline="IT",
        mode="MESSY",
        organization={},
        scope={
            "programs": ["HIPAA"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "program_versions": {"HIPAA": "retained source"},
        },
        simulated_at="2028-01-01T09:00:00Z",
        controls=[
            {"id": "C1", "title": "Approval policy", "owner_ids": ["P1"]},
            {"id": "C2", "title": "Unselected secret control"},
        ],
        people=[{"id": "P1", "name": "Operating owner"}],
        tasks=[
            {
                "id": "T1",
                "control_id": "C1",
                "title": "Verify authorization",
                "procedure": "Compare dated original authorization to transaction",
            }
        ],
    )
    state = engine.store.create(user["id"], state, "create")
    artifact = engine.artifacts.retain(
        state["id"],
        "observed.txt",
        b"Observed original approval dated April 10.",
        source={},
        coverage={"control_id": "C1"},
    )
    root = generation.epoch_directory(engine, state["id"])
    world = {"world_integrity_version": 1, "selections": []}
    world["world_sha256"] = digest(world)
    (root / "world.json").write_text(canonical(world))
    secret = "PRIVATE_UNRELEASED_CASE_FACT"
    definition = {
        "id": "PRIVATE-CASE",
        "facts": [{"id": "F1", "statement": secret}],
        "events": [{"id": "E1", "trigger": "FOLLOWUP", "business_days": 2}],
        "rubric": {
            "acceptable_alternatives": ["Precise supported limitation"],
            "unsupported_guesses": ["PRIVATE_RUBRIC_GUESS"],
            "professional_validation": "UNVALIDATED",
        },
        "playable_paths": [{"terminal_state": "SUPPORTED_CONCLUSION"}],
    }
    plan = {
        "control_id": "C1",
        "plan_integrity_version": 1,
        "facts": [],
        "events": [],
        "scenario_cases": [{"bound_definition": definition}],
        "requests": [],
    }
    plan["plan_sha256"] = digest(plan)
    (root / "unit-00000.json").write_text(canonical(plan))

    def populate(s, *_):
        s["generation"] = {"world_digest": digest(world)}
        s["artifacts"] = [artifact]
        s["workpapers"] = [
            {
                "id": "WP1",
                "versions": [
                    {
                        "version": 1,
                        "evidence_ids": [artifact["id"]],
                        "conclusion": "Limited observed approval only",
                    }
                ],
            }
        ]
        return s

    state = engine.store.command(
        user["id"],
        state["id"],
        {
            "command_id": "fixture",
            "expected_revision": state["revision"],
            "kind": "fixture",
            "payload": {},
        },
        populate,
        permissions={"learn"},
    )
    return engine, user, state, secret


def test_actual_layers_scoped_pinned_and_preview_private(tmp_path):
    engine, user, state, secret = fixture(tmp_path)
    result = review.prepare(state, engine.artifacts, engine=engine)
    private = result["_private"]["layers"]
    assert private["scope_resolution"]["control_ids"] == ["C1"]
    assert private["A_authority"]["passages"][0]["procedure"].startswith("Compare dated")
    assert private["B_policy_organization"]["controls"][0]["title"] == "Approval policy"
    assert secret in canonical(private["C_scenario"])
    assert "Precise supported limitation" in canonical(private["D_rubric"])
    assert secret not in canonical(review.public_prepared(result))
    path = generation.epoch_directory(engine, state["id"]) / "unit-00000.json"
    changed = json.loads(path.read_text())
    changed["facts"].append({"statement": "tamper"})
    path.write_text(canonical(changed))
    with pytest.raises(DomainError, match="integrity"):
        review.prepare(state, engine.artifacts, engine=engine)


def test_two_pass_private_result_never_enters_learner_state_or_history(tmp_path, monkeypatch):
    engine, user, state, secret = fixture(tmp_path)
    calls = []

    class Provider:
        model = "bounded-test-provider"

        def __init__(self, *args):
            pass

        def generate(self, role, context, messages):
            calls.append(copy.deepcopy(context))
            return {
                "text": secret
                if "private_five_layers" in context
                else "Observable limitation only",
                "source_refs": [],
                "claims": [],
                "observations": [],
            }

    monkeypatch.setattr(review, "LocalInference", Provider)
    engine.inference_config = Path("fixture-config")
    state = engine.command(
        user["id"],
        state["id"],
        {
            "command_id": "prepare",
            "expected_revision": state["revision"],
            "kind": "review.prepare",
            "payload": {"workpaper_ids": ["WP1"]},
        },
    )
    prepared = state["reviews"][-1]
    state = engine.command(
        user["id"],
        state["id"],
        {
            "command_id": "review",
            "expected_revision": state["revision"],
            "kind": "review.experimental",
            "payload": {
                "workpaper_ids": ["WP1"],
                "experimental_consent": True,
                "input_digest": prepared["input_digest"],
            },
        },
    )
    assert len(calls) == 2 and secret in canonical(calls[0]) and secret not in canonical(calls[1])
    assert secret not in canonical(state)
    assert secret not in canonical(engine.store.history(user["id"], state["id"]))
    pin = state["reviews"][-1]["private_review_appendix"]["digest"]
    path = generation.run_directory(engine, state["id"]) / "review-inputs" / (pin + ".json")
    assert secret in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600


def test_omissions_are_explicit_and_change_consent(tmp_path):
    engine, user, state, secret = fixture(tmp_path)
    before = review.public_prepared(review.prepare(state, engine.artifacts, engine=engine))
    changed = copy.deepcopy(state)
    changed["tasks"][0]["procedure"] = "X" * 20000
    after = review.public_prepared(review.prepare(changed, engine.artifacts, engine=engine))
    assert after["five_layer_review"]["context_omissions"]["A_authority"]["omitted_records"]
    assert digest(before) != digest(after)
    with pytest.raises(DomainError, match="inputs changed"):
        review.run(
            changed,
            engine.artifacts,
            Path("unused"),
            {"experimental_consent": True, "input_digest": digest(before)},
            engine=engine,
        )


def test_private_appendix_only_in_authorized_reviewer_export(tmp_path):
    import io
    import zipfile

    from enterprise.audit_suite.review_layers import retain

    engine, learner, state, secret = fixture(tmp_path)
    pin = retain(engine, state, {"result": {"text": secret}, "model": "fixture-not-actual-call"})

    def attach(s, *_):
        s["reviews"].append({"id": "R1", "private_review_appendix": pin})
        return s

    state = engine.store.command(
        learner["id"],
        state["id"],
        {
            "command_id": "appendix-fixture",
            "expected_revision": state["revision"],
            "kind": "fixture",
            "payload": {},
        },
        attach,
        permissions={"learn"},
    )
    envelope = {
        "command_id": "denied",
        "expected_revision": state["revision"],
        "kind": "review.export",
        "payload": {"edition": "REVIEWER"},
    }
    with pytest.raises(DomainError):
        engine.command(learner["id"], state["id"], envelope)
    reviewer = engine.store.provision("Independent reviewer", ["reviewer"])
    engine.store.grant(state["id"], reviewer["id"], "review")
    state = engine.command(reviewer["id"], state["id"], {**envelope, "command_id": "allowed"})
    data = engine.artifacts.read(state["artifacts"][-1])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert any(
            secret.encode() in archive.read(p)
            for p in archive.namelist()
            if p.startswith("private/review-inputs/")
        )
    projected = engine._project(learner["id"], copy.deepcopy(state))
    assert not any(a.get("audience") == "REVIEWER" for a in projected["artifacts"])
    assert secret not in canonical(projected)


def test_private_artifact_is_not_extractable_as_learner_review_source(tmp_path):
    engine, user, state, secret = fixture(tmp_path)
    hidden = engine.artifacts.retain(
        state["id"], "private.txt", secret.encode(), source={}, coverage={}
    )
    hidden["audience"] = "REVIEWER"
    state["artifacts"].append(hidden)
    state["workpapers"][0]["versions"][-1]["evidence_ids"].append(hidden["id"])
    result = review.prepare(state, engine.artifacts, engine=engine)
    assert secret not in canonical(result["observable_layer"])
