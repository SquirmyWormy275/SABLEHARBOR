from itertools import count

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


def test_manual_records_retain_visible_form_fields_and_scoped_note_provenance(tmp_path):
    engine = Engine(tmp_path)
    actor = engine.store.provision("Learner", ["learner"])["id"]
    data = {key: [] for key in COLLECTIONS}
    data.update(scope={}, phase="ACTIVE", simulated_at="2028-01-02T09:00:00+00:00")
    data["meetings"] = [{"id": "M1", "messages": [{"id": "MSG1", "content": "Source statement"}]}]
    engagement = engine.store.create(actor, data, "create")["id"]
    counter = count()

    def command(kind, payload):
        state = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": str(next(counter)),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    state = command(
        "task.create",
        {
            "title": "Inspect intervening work",
            "test_type": "ROLL_FORWARD",
            "rationale": "Document the procedures addressing the remaining interval.",
        },
    )
    task = state["tasks"][0]
    assert task["kind"] == task["test_type"] == "ROLL_FORWARD"
    assert task["rationale"].startswith("Document")
    assert task["conclusion"] == "NOT_RUN"
    state = command(
        "note.create",
        {
            "title": "Management statement",
            "text": "The owner described a review.",
            "source_message_id": "MSG1",
        },
    )
    note = state["notes"][0]
    assert note["title"] == "Management statement"
    assert note["source_refs"] == ["MSG1"]
    state = command(
        "note.correct",
        {
            "note_id": note["id"],
            "text": "The owner described a review; operation is unverified.",
            "rationale": "Separate the statement from inspected evidence.",
        },
    )
    note = state["notes"][0]
    assert note["source_refs"] == ["MSG1"]
    assert note["history"][0]["text"] == "The owner described a review."
    assert note["history"][0]["rationale"].startswith("Separate")
    before = engine.store.get(actor, engagement)
    with pytest.raises(DomainError, match="existing engagement message"):
        command("note.create", {"text": "Unrelated", "source_message_id": "OTHER-ENGAGEMENT-MSG"})
    assert engine.store.get(actor, engagement) == before
    ratings = {
        "usability": "4",
        "evidence_quality": "3",
        "persona_consistency": "4",
        "feedback_usefulness": "2",
        "defect_reference": task["id"],
    }
    state = command("survey.submit", {"feedback": "Subjective training feedback", **ratings})
    assert {key: state["surveys"][0][key] for key in ratings} == ratings
    assert state["surveys"][0]["external_telemetry"] is False
