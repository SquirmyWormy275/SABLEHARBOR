import json

import pytest

from enterprise.audit_suite.company_persona import sources
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def context(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    e = Engine(tmp_path / "audit", company_root=company, inference_config=tmp_path / "unused.json")
    actor = e.store.provision("Investigator", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Selected original dialogue",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-01-31",
        },
        configuration={},
        simulated_at="2027-02-01T00:00:00Z",
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
    )
    state["people"] = [
        {"id": "owner", "name": "Scoped owner", "title": "Source custodian"},
        {"id": "other", "name": "Another custodian", "title": "Other owner"},
    ]
    state["meetings"] = [{"id": "M1", "kind": "KICKOFF", "person_id": "owner", "messages": []}]
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    pins = {}
    for system, owner in [("a-docs", "owner"), ("z-operations", "owner"), ("different", "other")]:
        e.company_store.register_system("SH", "base", system, owner)
        e.company_store.grant(actor, state["id"], "SH", "base", system)
        for number in range(5 if system == "a-docs" else 1):
            record = f"R{number}"
            row = e.company_store.append_version(
                "SH",
                "base",
                system,
                record,
                expected_version=0,
                command_id=system + record,
                event_at="2027-01-01T00:00:00Z",
                available_at="2027-01-01T00:00:00Z",
                content=json.dumps(
                    {"system": system, "record": record, "value": "Original source"}
                ).encode(),
                provenance={
                    "source_reference": "fixture",
                    "name": "source.json",
                    "classification": "EXERCISE_ONLY",
                },
            )
            pins[system] = {
                "system_id": system,
                "record_id": record,
                "version": 1,
                "sha256": row["sha256"],
            }
    return e, actor, state, pins


def test_explicit_late_system_overrides_sampler_without_substitution(context):
    e, actor, state, pins = context
    default = sources(e, actor, state, "owner")
    assert {r["value"]["system_id"] for r in default if r["kind"] == "COMPANY_ORIGINAL_RECORD"} == {
        "a-docs"
    }
    selected = sources(e, actor, state, "owner", selected_records=[pins["z-operations"]])
    originals = [r for r in selected if r["kind"] == "COMPANY_ORIGINAL_RECORD"]
    assert len(originals) == 1
    value = originals[0]["value"]
    assert (
        value["system_id"] == "z-operations"
        and value["source_identity"]["system"] == "z-operations"
    )
    assert value["source_identity"]["sha256"] == pins["z-operations"]["sha256"]
    assert value["locations_omitted"] == 0
    assert e.store.get(actor, state["id"])["revision"] == state["revision"]


@pytest.mark.parametrize(
    "bad",
    [[], None, [{}], [{"system_id": "x", "record_id": "R", "version": True, "sha256": "a" * 64}]],
)
def test_invalid_selection_fails_before_inference(context, monkeypatch, bad):
    e, actor, state, _ = context

    def forbidden(*args):
        pytest.fail("Invalid selection must not invoke a model")

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", forbidden)
    with pytest.raises(DomainError) as error:
        e.command(
            actor,
            state["id"],
            {
                "command_id": "bad",
                "expected_revision": state["revision"],
                "kind": "meeting.message",
                "payload": {"meeting_id": "M1", "content": "Inspect this", "source_records": bad},
            },
        )
    assert error.value.code == "INVALID_SOURCE_SELECTION"
    assert not e.store.get(actor, state["id"])["meetings"][0]["messages"]


def test_wrong_owner_hash_future_revoked_and_parse_budget_never_fall_back(context, monkeypatch):
    e, actor, state, pins = context
    for selected in [
        [pins["different"]],
        [{**pins["z-operations"], "sha256": "a" * 64}],
        [pins["z-operations"], pins["z-operations"]],
    ]:
        with pytest.raises(DomainError):
            sources(e, actor, state, "owner", selected_records=selected)
    future = e.company_store.append_version(
        "SH",
        "base",
        "z-operations",
        "R0",
        expected_version=1,
        command_id="future",
        event_at="2028-01-01T00:00:00Z",
        available_at="2028-01-01T00:00:00Z",
        content=b"future",
        provenance={"source_reference": "future", "name": "source.txt"},
    )
    with pytest.raises(DomainError):
        sources(
            e,
            actor,
            state,
            "owner",
            selected_records=[{**pins["z-operations"], "version": 2, "sha256": future["sha256"]}],
        )
    with monkeypatch.context() as patch:
        patch.setattr("enterprise.audit_suite.company_persona.MAX_CHARACTERS", 3)
        with pytest.raises(DomainError):
            sources(e, actor, state, "owner", selected_records=[pins["z-operations"]])
    e.company_store.grant(actor, state["id"], "SH", "base", "z-operations", active=False)
    with pytest.raises(DomainError):
        sources(e, actor, state, "owner", selected_records=[pins["z-operations"]])


def test_revocation_during_decode_fails_closed(context, monkeypatch):
    e, actor, state, pins = context
    from enterprise.audit_suite import company_persona

    original = company_persona.extract

    def revoke(*args):
        result = original(*args)
        e.company_store.grant(actor, state["id"], "SH", "base", "z-operations", active=False)
        return result

    monkeypatch.setattr(company_persona, "extract", revoke)
    with pytest.raises(DomainError) as error:
        sources(e, actor, state, "owner", selected_records=[pins["z-operations"]])
    assert error.value.code == "SOURCE_CONTEXT_UNAVAILABLE"


@pytest.mark.parametrize("revoke_during_model", [False, True])
def test_actual_engine_retains_chosen_pins_or_rejects_revocation_before_commit(
    context, monkeypatch, revoke_during_model
):
    e, actor, state, pins = context
    calls = []

    class Provider:
        def __init__(self, *args):
            pass

        def generate(self, role, context, messages):
            calls.append((role, context))
            if role == "persona":
                originals = [
                    r for r in context["sources"] if r["kind"] == "COMPANY_ORIGINAL_RECORD"
                ]
                assert [r["value"]["system_id"] for r in originals] == ["z-operations"]
                if revoke_during_model:
                    e.company_store.grant(
                        actor, state["id"], "SH", "base", "z-operations", active=False
                    )
                return {
                    "text": "Source-specific reply",
                    "source_refs": [originals[0]["id"]],
                    "proposed_actions": [],
                }
            return {"text": "Attributed note", "source_refs": [], "claims": []}

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", Provider)
    envelope = {
        "command_id": "selected",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {
            "meeting_id": "M1",
            "content": "Inspect selected original",
            "source_records": [pins["z-operations"]],
        },
    }
    if revoke_during_model:
        with pytest.raises(DomainError) as error:
            e.command(actor, state["id"], envelope)
        assert error.value.code == "SOURCE_CONTEXT_UNAVAILABLE"
        assert not e.store.get(actor, state["id"])["meetings"][0]["messages"]
    else:
        result = e.command(actor, state["id"], envelope)
        assert result["meetings"][0]["messages"][0]["source_records"] == [pins["z-operations"]]
        assert e.command(actor, state["id"], envelope) == result
        assert len(calls) == 2
        assert result["artifacts"] == []


def test_background_job_input_preserves_exact_selected_source_pins(context, tmp_path):
    from enterprise.audit_suite.background_jobs import BackgroundJobs

    e, actor, state, pins = context
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    jobs = BackgroundJobs(root, e)
    command = {
        "command_id": "selected-background",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {
            "meeting_id": "M1",
            "content": "Inspect this exact original",
            "source_records": [pins["z-operations"]],
        },
    }
    job = jobs.submit(actor, state["id"], command)
    assert jobs.input(actor, state["id"], job["id"]) == command
    assert "source_records" not in json.dumps(jobs.listing(actor, state["id"]))
    assert jobs.read(actor, state["id"], job["id"])["status"] == "PENDING"
