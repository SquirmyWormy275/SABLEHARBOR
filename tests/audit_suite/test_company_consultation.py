import copy

import pytest
import test_company_persona_selection as persona_tests

from enterprise.audit_suite import company_consultation as consultation
from enterprise.audit_suite.background_jobs import BackgroundJobs
from enterprise.audit_suite.inference import _response_schema, validate_result
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def exchange(tmp_path):
    engine, actor, state, pins = persona_tests.context.__wrapped__(tmp_path)

    def seed(s, c, a):
        s["meetings"][0]["title"] = "Origin meeting"
        s["meetings"][0]["messages"] = [
            {
                "id": "Q1",
                "role": "user",
                "content": "What does the source establish?",
                "simulated_at": s["simulated_at"],
                "actor": actor,
            },
            {
                "id": "A1",
                "role": "assistant",
                "person_id": "owner",
                "claim_type": "PERSONA_STATEMENT",
                "content": "Earlier qualified company statement.",
                "simulated_at": s["simulated_at"],
                "actor": actor,
            },
        ]
        s["meetings"].append(
            {
                "id": "M2",
                "title": "Consulted colleague",
                "kind": "WALKTHROUGH",
                "person_id": "other",
                "messages": [],
            }
        )
        return s

    state = engine.store.command(
        actor,
        state["id"],
        {
            "kind": "fixture",
            "payload": {},
            "command_id": "seed",
            "expected_revision": state["revision"],
        },
        seed,
        permissions={"learn"},
    )
    index = consultation.input_pins(state)["questions"][0]
    command = {
        "kind": "meeting.message",
        "command_id": "consult",
        "expected_revision": state["revision"],
        "payload": {
            "meeting_id": "M2",
            "content": "Please clarify the earlier statement.",
            "source_records": [pins["different"]],
            "consultation": {
                "kind": "REFERRAL",
                "question_ref": index["ref"],
                "response_ref": index["responses"][0]["ref"],
            },
        },
    }
    return engine, actor, state, pins, command


def provider(monkeypatch, *, relation="CLARIFIES", during=None):
    calls = []

    class Fake:
        def __init__(self, *a):
            pass

        def generate(self, role, context, messages):
            calls.append((role, copy.deepcopy(context), copy.deepcopy(messages)))
            if role == "persona":
                if during:
                    during()
                originals = [
                    s for s in context["sources"] if s["kind"] == "COMPANY_ORIGINAL_RECORD"
                ]
                return {
                    "text": "Attributed clarification from selected support.",
                    "source_refs": [s["id"] for s in originals],
                    "consultation_relation": relation,
                    "proposed_actions": [],
                    "model": {"fixture": True},
                }
            return {"text": "Attributed note.", "source_refs": [], "claims": []}

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", Fake)
    return calls


def test_referred_reply_exact_links_sources_originals_and_replay(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch)
    before = copy.deepcopy(state["meetings"][0]["messages"])
    source_before = e.company_store.path.read_bytes()
    result = e.command(actor, state["id"], command)
    assert result["meetings"][0]["messages"] == before
    user, answer = result["meetings"][1]["messages"]
    assert (
        user["role"] == "user"
        and user["consultation"]["request_authorship"] == "LEARNER_REQUESTED_COMPANY_CONSULTATION"
    )
    assert answer["person_id"] == "other" and answer["claim_type"] == "PERSONA_STATEMENT"
    assert answer["consultation"]["relation"] == "CLARIFIES"
    manifest = answer["consultation"]["source_manifest"]
    assert len(manifest) == 1 and manifest[0]["sha256"] == pins["different"]["sha256"]
    assert "text" not in manifest[0]["locations"][0]
    assert calls[0][1]["allowed_actions"] == []
    assert calls[1][1]["attributed_consultation"]["relation"] == "CLARIFIES"
    assert result["notes"][-1]["consultation"] == answer["consultation"]
    historical = [
        s["value"] for s in calls[0][1]["sources"] if s["kind"] == "ATTRIBUTED_HISTORICAL_STATEMENT"
    ]
    assert historical[0]["speaker_role"] == "LEARNER" and historical[1]["person_id"] == "owner"
    assert e.command(actor, state["id"], command) == result and len(calls) == 2
    assert not result["artifacts"] and e.company_store.path.read_bytes() == source_before


@pytest.mark.parametrize(
    "bad",
    [
        "question_hash",
        "response_hash",
        "foreign_meeting",
        "wrong_role",
        "same_person",
        "answer_text",
    ],
)
def test_invalid_pin_role_or_forged_answer_rejected_before_model(exchange, monkeypatch, bad):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch)
    p = command["payload"]
    value = p["consultation"]
    if bad == "question_hash":
        value["question_ref"]["sha256"] = "f" * 64
    elif bad == "response_hash":
        value["response_ref"]["sha256"] = "f" * 64
    elif bad == "foreign_meeting":
        value["question_ref"]["meeting_id"] = "FOREIGN"
    elif bad == "wrong_role":
        value["question_ref"] = value["response_ref"]
    elif bad == "same_person":
        p["meeting_id"] = "M1"
    else:
        p["company_response"] = "Pretend this was company-authored"
    with pytest.raises(DomainError):
        e.command(actor, state["id"], command)
    assert calls == [] and e.store.get(actor, state["id"])["revision"] == state["revision"]


def test_correction_requires_response_and_retains_both_statements(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    provider(monkeypatch, relation="CORRECTS")
    command["payload"]["consultation"]["kind"] = "CORRECTION_REQUEST"
    result = e.command(actor, state["id"], command)
    answer = result["meetings"][1]["messages"][-1]
    assert answer["consultation"]["relation"] == "CORRECTS"
    assert answer["consultation"]["response_ref"]["message_id"] == "A1"
    assert result["meetings"][0]["messages"][1]["content"] == "Earlier qualified company statement."
    assert "VERIFIED_CORRECTION" in answer["consultation"]["authority"]


def test_missing_support_remains_unknown_without_default_source_sampling(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch, relation="CANNOT_ESTABLISH")
    del command["payload"]["source_records"]
    result = e.command(actor, state["id"], command)
    answer = result["meetings"][1]["messages"][-1]
    assert answer["consultation"]["source_support"] == "SUPPORT_NOT_SUPPLIED"
    assert answer["consultation"]["source_manifest"] == []
    assert not any(s["kind"] == "COMPANY_ORIGINAL_RECORD" for s in calls[0][1]["sources"])


def test_correction_without_previous_response_rejected(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch, relation="CORRECTS")
    command["payload"]["consultation"]["response_ref"] = None
    with pytest.raises(DomainError, match="Correction must identify"):
        e.command(actor, state["id"], command)
    assert len(calls) == 1 and e.store.get(actor, state["id"])["revision"] == state["revision"]


def test_revoked_selected_source_during_generation_prevents_reply(exchange, monkeypatch):
    e, actor, state, pins, command = exchange

    def revoke():
        e.company_store.grant(actor, state["id"], "SH", "base", "different", active=False)

    provider(monkeypatch, during=revoke)
    with pytest.raises(DomainError) as error:
        e.command(actor, state["id"], command)
    assert error.value.code == "SOURCE_CONTEXT_UNAVAILABLE"
    assert not e.store.get(actor, state["id"])["meetings"][1]["messages"]


def test_changed_revision_during_generation_prevents_reply(exchange, monkeypatch):
    e, actor, state, pins, command = exchange

    def change():
        e.store.command(
            actor,
            state["id"],
            {
                "kind": "fixture",
                "payload": {},
                "command_id": "race",
                "expected_revision": state["revision"],
            },
            lambda s, c, a: s,
            permissions={"learn"},
        )

    provider(monkeypatch, during=change)
    with pytest.raises(DomainError) as error:
        e.command(actor, state["id"], command)
    assert (
        error.value.status == 409 and not e.store.get(actor, state["id"])["meetings"][1]["messages"]
    )


def test_model_relation_is_context_gated_and_actions_forbidden():
    value = {"text": "Statement", "source_refs": [], "consultation_relation": "CORRECTS"}
    with pytest.raises(DomainError):
        validate_result("persona", value, {"source_ids": []})
    with pytest.raises(DomainError):
        validate_result(
            "persona", value, {"source_ids": [], "consultation": {"has_prior_response": False}}
        )
    context = {
        "source_ids": [],
        "consultation": {"has_prior_response": True},
        "allowed_actions": [],
    }
    assert validate_result("persona", value, context)["authority"] == "PERSONA_STATEMENT"
    assert "consultation_relation" in _response_schema("persona", [], context)["required"]
    assert "consultation_relation" not in _response_schema("persona", [], {})["properties"]


def test_projection_limits_clear_all_choices(exchange):
    e, actor, state, pins, command = exchange
    state["meetings"][1]["messages"] = [{}] * 2001
    assert consultation.input_pins(state) == {"status": "INPUT_LIMIT_EXCEEDED", "questions": []}


def test_future_meeting_is_durable_delayed_job_without_model(exchange, monkeypatch, tmp_path):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch)

    def schedule(s, c, a):
        s["meetings"][1]["scheduled_at"] = "2027-03-01T00:00:00Z"
        return s

    state = e.store.command(
        actor,
        state["id"],
        {
            "kind": "fixture",
            "payload": {},
            "command_id": "future",
            "expected_revision": state["revision"],
        },
        schedule,
        permissions={"learn"},
    )
    command["expected_revision"] = state["revision"]
    (tmp_path / "jobs").mkdir(mode=0o700)
    jobs = BackgroundJobs(tmp_path / "jobs", e)
    job = jobs.submit(actor, state["id"], command)
    jobs._execute_job(actor, state["id"], job["id"])
    final = jobs.read(actor, state["id"], job["id"])
    assert final["status"] == "FAILED" and final["error_code"] == "CONSULTATION_DELAYED"
    assert not calls and not e.store.get(actor, state["id"])["meetings"][1]["messages"]


def test_future_original_denied_before_any_provider_call(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch)
    native = e.company_store.append_version(
        "SH",
        "base",
        "different",
        "FUTURE",
        expected_version=0,
        command_id="future-native",
        event_at="2027-03-01T00:00:00Z",
        available_at="2027-03-01T00:00:00Z",
        content=b'{"future":"unknown"}',
        provenance={"source_reference": "future", "name": "future.json"},
    )
    command["payload"]["source_records"] = [
        {"system_id": "different", "record_id": "FUTURE", "version": 1, "sha256": native["sha256"]}
    ]
    with pytest.raises(DomainError) as error:
        e.command(actor, state["id"], command)
    assert error.value.code == "SOURCE_CONTEXT_UNAVAILABLE" and calls == []


def test_revoked_actor_during_reply_prevents_note_call_and_commit(exchange, monkeypatch):
    e, actor, state, pins, command = exchange

    def revoke():
        with e.store.connect() as db:
            db.execute("UPDATE principals SET revoked=1 WHERE id=?", (actor,))

    calls = provider(monkeypatch, during=revoke)
    with pytest.raises(DomainError):
        e.command(actor, state["id"], command)
    assert len(calls) == 1
    with e.store.connect() as db:
        assert (
            db.execute("SELECT revision FROM engagements WHERE id=?", (state["id"],)).fetchone()[0]
            == state["revision"]
        )


def test_cross_engagement_question_pin_not_resolved(exchange, monkeypatch):
    e, actor, state, pins, command = exchange
    calls = provider(monkeypatch)
    command["payload"]["consultation"]["question_ref"] = {
        "meeting_id": "M-FOREIGN",
        "message_id": "Q-FOREIGN",
        "sha256": "f" * 64,
    }
    with pytest.raises(DomainError, match="question unavailable"):
        e.command(actor, state["id"], command)
    assert not calls


@pytest.mark.parametrize(
    "damage", ["duplicate_message", "invalid_time", "nonlist_messages", "missing_people"]
)
def test_malformed_projection_is_unavailable_not_engine_failure(exchange, damage):
    e, actor, state, pins, command = exchange
    broken = copy.deepcopy(state)
    if damage == "duplicate_message":
        broken["meetings"][0]["messages"].append(
            copy.deepcopy(broken["meetings"][0]["messages"][0])
        )
    elif damage == "invalid_time":
        broken["meetings"][0]["messages"][0]["simulated_at"] = "not-a-date"
    elif damage == "nonlist_messages":
        broken["meetings"][0]["messages"] = None
    else:
        broken["people"] = None
    assert consultation.input_pins(broken) == {"status": "INPUT_DATA_UNAVAILABLE", "questions": []}
    # Engine projection must remain usable for the surrounding engagement.
    projected = e._project(actor, broken)
    assert projected["company_consultation_inputs"]["status"] == "INPUT_DATA_UNAVAILABLE"
