"""Explicit authored judgments over actual bound history; no models or live data."""

import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.instructor_assessments import (
    DIMENSIONS,
    InstructorAssessments,
    validate_archive,
)
from enterprise.audit_suite.store import DomainError, canonical, digest
from tests.audit_suite.test_explanation_binding import workspace
from tests.audit_suite.test_instructor_comparison import advance, bound


@pytest.fixture
def assessment(tmp_path):
    engine, args, bindings = bound(workspace.__wrapped__(tmp_path))
    root = tmp_path / "assessments"
    root.mkdir(mode=0o700)
    return InstructorAssessments(root, engine, bindings), engine, args


def payload(core, args, revision=0, **changes):
    options = core.options(args["instructor_id"], args["engagement_id"], revision)
    value = {
        k: options[k] for k in ("learner_revision", "key_pin", "rubric_sha256", "inventory_sha256")
    }
    value.update(
        expected_engagement_revision=options["current_engagement_revision"],
        title="Bounded instructor assessment",
        issue_ids=["I1"],
        expectation_ids=["E1"],
        dimensions=[
            {
                "dimension": d,
                "assessment": "Not assessed",
                "rationale": "Insufficient selected support; no adverse conclusion inferred.",
                "reference_ids": [],
            }
            for d in DIMENSIONS
        ],
        alternatives=[],
        overrides=[],
        defects=[],
        predecessor=None,
        command_id="record",
    )
    value.update(changes)
    return value


def test_authored_six_dimensions_private_history_reload_and_exact_retry(assessment, monkeypatch):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    monkeypatch.setattr(engine.store, "history", lambda *_: pytest.fail("All history materialized"))
    p = payload(core, args)
    saved = core.save(actor, eid, p)
    assert saved["document"]["authored"]["dimensions"] == p["dimensions"]
    assert saved["document"]["references"] == []
    assert "NO_AGGREGATE_GRADE" in saved["document"]["qualification"]
    assert core.save(actor, eid, p) == saved
    loaded = InstructorAssessments(core.root, engine, core.bindings)
    assert loaded.read(actor, eid, saved["id"]) == saved
    listing = loaded.listing(actor, eid)["assessments"]
    assert "document" not in listing[0] and listing[0]["title"] == p["title"]
    validate_archive(loaded.snapshot())
    assert engine.store.get(actor, eid) == before


def test_exact_historical_workpaper_versions_and_control_only_references(assessment):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    source = args["source_refs"][0]
    old = {
        "version": 1,
        "actor": actor,
        "evidence_ids": ["A1"],
        "conclusion": "First recorded conclusion",
    }

    def initial(s):
        s.update(
            company_source_binding={"company": "C", "branch": "B"},
            artifacts=[
                {"id": "A1", "sha256": source["sha256"], "source": {"receipt": {"source": source}}}
            ],
            workpapers=[{"id": "WP", "prepared_by": actor, "versions": [old]}],
            requests=[{"id": "REQ", "control_id": "CONTROL1", "status": "OPEN"}],
        )
        return s

    advance(engine, args, initial)
    options = core.options(actor, eid, 1)
    wp = next(r for r in options["references"] if r["kind"] == "workpaper")
    request = next(r for r in options["references"] if r["kind"] == "request")
    assert wp["version"] == 1 and wp["content_sha256"] == digest(old)
    assert request["relation"] == "CONTROL_ASSOCIATION_ONLY" and request["content_sha256"] is None
    p = payload(core, args, 1)
    p["dimensions"][2]["reference_ids"] = [wp["id"], request["id"]]
    saved = core.save(actor, eid, p)

    def later(s):
        s["workpapers"][0]["versions"].append({**old, "version": 2, "conclusion": "Changed"})
        return s

    advance(engine, args, later)
    read = core.read(actor, eid, saved["id"])
    assert next(r for r in read["document"]["references"] if r["kind"] == "workpaper")[
        "content_sha256"
    ] == digest(old)
    assert read["current_engagement_revision"] == 2 and read["learner_revision"] == 1


def test_correction_retains_original_and_reasoned_alternative_override_defect(assessment):
    core, _, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    first = core.save(actor, eid, payload(core, args))
    p = payload(
        core,
        args,
        command_id="correction",
        predecessor={"id": first["id"], "sha256": first["sha256"]},
    )
    p["alternatives"] = [
        {
            "expectation_id": "E1",
            "description": "Other authorized corroboration",
            "rationale": "Explicit instructor acceptance of this alternative only",
            "reference_ids": [],
        }
    ]
    p["overrides"] = [
        {
            "expectation_id": "E1",
            "prior_interpretation": "Original authored analysis",
            "replacement": "Revised limited interpretation",
            "rationale": "Reasoned instructor correction",
            "reference_ids": [],
        }
    ]
    p["defects"] = [
        {
            "issue_id": "I1",
            "description": "Potential missing scenario support",
            "impact": "Assessment limited",
            "rationale": "Requires scenario-owner review",
            "reference_ids": [],
        }
    ]
    corrected = core.save(actor, eid, p)
    assert (
        corrected["version"] == 2
        and corrected["document"]["predecessor"]["sha256"] == first["sha256"]
    )
    assert core.read(actor, eid, first["id"])["document"] == first["document"]
    assert not core.read(actor, eid, first["id"])["correction_allowed"]
    with pytest.raises(DomainError):
        core.save(actor, eid, {**p, "command_id": "fork"})
    validate_archive(core.snapshot())


@pytest.mark.parametrize(
    "damage",
    ["dimension", "extra", "issue", "expectation", "ref", "rubric", "inventory", "revision"],
)
def test_strict_authored_selection_and_exact_pins(assessment, damage):
    core, _, args = assessment
    p = payload(core, args)
    if damage == "dimension":
        p["dimensions"].pop()
    if damage == "extra":
        p["aggregate_score"] = 100
    if damage == "issue":
        p["issue_ids"] = ["absent"]
    if damage == "expectation":
        p["expectation_ids"] = ["absent"]
    if damage == "ref":
        p["dimensions"][0]["reference_ids"] = ["REF-ABSENT"]
    if damage == "rubric":
        p["rubric_sha256"] = "0" * 64
    if damage == "inventory":
        p["inventory_sha256"] = "0" * 64
    if damage == "revision":
        p["learner_revision"] = True
    with pytest.raises(DomainError):
        core.save(args["instructor_id"], args["engagement_id"], p)
    assert core.snapshot()["documents"] == []


def test_owned_isolation_and_stale_metadata_redaction(assessment):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    saved = core.save(actor, eid, payload(core, args))
    other = engine.store.provision("Other instructor", ["instructor"])["id"]
    engine.store.grant(eid, other, "instruct")
    assert core.listing(other, eid)["assessments"] == []
    with pytest.raises(DomainError) as error:
        core.read(other, eid, saved["id"])
    assert error.value.status == 404
    with pytest.raises(DomainError) as error:
        core.listing(args["audited_actor_id"], eid)
    assert error.value.status == 403
    advance(engine, args, lambda s: {**s, "evidence_acquisition": "changed"})
    row = core.read(actor, eid, saved["id"])
    assert (
        row["context_status"] == "CONTEXT_CHANGED" and "document" not in row and "title" not in row
    )


def test_final_role_race_rolls_back_and_inert_archive_rejects_extra_prose(assessment, monkeypatch):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = payload(core, args)
    finish = core._finish

    def revoked(*a):
        engine.store.grant(eid, actor, "learn")
        finish(*a)

    monkeypatch.setattr(core, "_finish", revoked)
    with pytest.raises(DomainError):
        core.save(actor, eid, p)
    assert core.snapshot()["documents"] == []
    engine.store.grant(eid, actor, "instruct")
    monkeypatch.setattr(core, "_finish", finish)
    core.save(actor, eid, p)
    archive = deepcopy(core.snapshot())
    body = json.loads(archive["documents"][0]["body"])
    body["document"]["selected_issues"][0]["private_source_path"] = "/hidden"
    archive["documents"][0].update(body=canonical(body), sha256=digest(body))
    with pytest.raises(DomainError):
        validate_archive(archive)


def test_other_instructor_cannot_correct_owned_assessment(assessment):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    first = core.save(actor, eid, payload(core, args))
    other = engine.store.provision("Independent colleague", ["instructor"])["id"]
    engine.store.grant(eid, other, "instruct")
    other_args = {**args, "instructor_id": other}
    p = payload(core, other_args, predecessor={"id": first["id"], "sha256": first["sha256"]})
    with pytest.raises(DomainError, match="predecessor"):
        core.save(other, eid, p)
    assert len(core.snapshot()["documents"]) == 1


def test_correction_explicitly_selects_new_revision_with_new_pins(assessment):
    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    original = core.save(actor, eid, payload(core, args))
    advance(
        engine,
        args,
        lambda s: {
            **s,
            "title": "New shared work",
            "company_source_binding": {"company": "C", "branch": "B"},
        },
    )
    p = payload(
        core,
        args,
        1,
        command_id="new-revision",
        predecessor={"id": original["id"], "sha256": original["sha256"]},
    )
    corrected = core.save(actor, eid, p)
    assert corrected["learner_revision"] == 1
    assert (
        original["document"]["pins"]["selected_state_sha256"]
        != corrected["document"]["pins"]["selected_state_sha256"]
    )
    assert core.read(actor, eid, original["id"])["learner_revision"] == 0


def test_current_key_race_cannot_publish(assessment, monkeypatch):
    core, _, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = payload(core, args)
    finish = core._finish
    calls = 0

    def changed(*a):
        nonlocal calls
        calls += 1
        if calls == 2:
            core.bindings[eid]["manifest_sha256"] = "0" * 64
        finish(*a)

    monkeypatch.setattr(core, "_finish", changed)
    with pytest.raises(DomainError, match="context changed"):
        core.save(actor, eid, p)
    assert core.snapshot()["documents"] == []


def test_private_alias_limit_and_no_active_restore_api(assessment, monkeypatch, tmp_path):
    from enterprise.audit_suite import instructor_assessments

    core, engine, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    alias = tmp_path / "alias"
    alias.symlink_to(core.root, target_is_directory=True)
    with pytest.raises(DomainError):
        InstructorAssessments(alias, engine, core.bindings)
    monkeypatch.setattr(instructor_assessments, "MAX_DOCUMENTS", 1)
    core.save(actor, eid, payload(core, args))
    with pytest.raises(DomainError):
        core.save(actor, eid, payload(core, args, command_id="over-limit"))
    assert len(core.snapshot()["documents"]) == 1
    assert not hasattr(core, "restore_archive")


def test_same_command_different_authored_reason_rejected(assessment):
    core, _, args = assessment
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = payload(core, args)
    core.save(actor, eid, p)
    p["dimensions"][0]["rationale"] = "A changed interpretation"
    with pytest.raises(DomainError, match="payload differs"):
        core.save(actor, eid, p)
    assert len(core.snapshot()["documents"]) == 1
