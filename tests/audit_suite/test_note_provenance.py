"""Neutral mixed-speaker extraction must retain actual message provenance."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine, exchange_note
from enterprise.audit_suite.store import DomainError


def exchange():
    user = {"id": "MSG-U", "role": "user", "actor": "LEARNER", "content": "I have not tested this."}
    company = {
        "id": "MSG-C",
        "role": "assistant",
        "person_id": "PERSON-C",
        "content": "The source remains unavailable.",
    }
    extraction = {
        "text": "The learner has not tested; company reports missing source.",
        "source_refs": ["MSG-U", "MSG-C"],
        "claims": [
            {"text": "Not tested", "source_refs": ["MSG-U"]},
            {"text": "Missing source", "source_refs": ["MSG-C"]},
        ],
    }
    return user, company, extraction


def test_mixed_speakers_and_each_claim_resolve_exact_message():
    user, company, extraction = exchange()
    note = exchange_note(
        {"id": "M", "person_id": "PERSON-C"}, user, company, {"extracted_notes": extraction}, {}
    )
    assert note["person_id"] is None
    assert [r["speaker_role"] for r in note["source_refs"]] == ["LEARNER", "COMPANY"]
    assert note["attributed_bullets"][0]["source_refs"][0]["speaker_id"] == "LEARNER"
    assert note["attributed_bullets"][1]["source_refs"][0]["original_text"] == company["content"]
    assert note["confirmation"] == "UNCONFIRMED_EXTRACTION"


def test_uncited_summary_does_not_become_company_statement_and_foreign_ref_rejected():
    user, company, extraction = exchange()
    extraction["source_refs"] = []
    note = exchange_note(
        {"id": "M", "person_id": "PERSON-C"}, user, company, {"extracted_notes": extraction}, {}
    )
    assert note["classification"] == "UNATTRIBUTED_PROPOSAL" and note["person_id"] is None
    extraction["claims"][0]["source_refs"] = ["OTHER-MEETING"]
    with pytest.raises(DomainError, match="unknown exchange"):
        exchange_note(
            {"id": "M", "person_id": "PERSON-C"}, user, company, {"extracted_notes": extraction}, {}
        )


def test_actual_store_message_ids_and_speaker_history_are_preserved(tmp_path, monkeypatch):
    engine = Engine(tmp_path)
    actor = engine.store.provision("Neutral learner", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        scope={},
        phase="ACTIVE",
        simulated_at="2027-01-04T09:00:00Z",
        people=[{"id": "PERSON-C", "name": "Company person"}],
        meetings=[{"id": "MEETING", "person_id": "PERSON-C", "messages": []}],
    )
    state = engine.store.create(actor, state, "create")
    user, company, extraction = exchange()
    response = {
        "text": company["content"],
        "source_refs": [],
        "message_ids": {"user": user["id"], "company": company["id"]},
        "extracted_notes": extraction,
    }
    monkeypatch.setattr(Engine, "_conversation", lambda *args: deepcopy(response))
    command = {
        "command_id": "exchange",
        "expected_revision": state["revision"],
        "kind": "meeting.message",
        "payload": {"meeting_id": "MEETING", "content": user["content"]},
    }
    result = engine.command(actor, state["id"], command)
    messages = result["meetings"][0]["messages"]
    assert [m["id"] for m in messages] == ["MSG-U", "MSG-C"]
    assert result["notes"][0]["source_refs"][0]["speaker_id"] == actor
    assert result["notes"][0]["source_refs"][1]["speaker_id"] == "PERSON-C"
    assert len(engine.command(actor, state["id"], command)["notes"]) == 1


def test_extractor_receives_actual_persistable_ids_and_separate_speakers(tmp_path, monkeypatch):
    calls = []

    class Provider:
        def __init__(self, _config):
            pass

        def generate(self, role, context, messages):
            calls.append((role, context))
            if role == "persona":
                return {"text": "Company cannot provide that source.", "source_refs": []}
            return {
                "text": "Both statements remain unverified.",
                "source_refs": context["source_ids"],
            }

    monkeypatch.setattr("enterprise.audit_suite.inference.LocalInference", Provider)
    engine = Engine(tmp_path, inference_config=tmp_path / "neutral-provider")
    state = {key: [] for key in COLLECTIONS}
    state.update(
        id="ENG-neutral",
        phase="ACTIVE",
        scope={"period_end": "2027-12-31"},
        simulated_at="2027-01-04T09:00:00Z",
        people=[{"id": "PERSON", "name": "Neutral person", "title": "Custodian"}],
        meetings=[{"id": "MEETING", "person_id": "PERSON", "kind": "KICKOFF", "messages": []}],
    )
    result = engine._conversation(
        state, {"meeting_id": "MEETING", "content": "I did not inspect it."}
    )
    context = calls[-1][1]
    assert context["source_ids"] == list(result["message_ids"].values())
    assert all(source.startswith("MSG-") for source in context["source_ids"])
    assert [source["speaker_role"] for source in context["sources"]] == ["LEARNER", "COMPANY"]
    assert context["sources"][0]["text"] == "I did not inspect it."
