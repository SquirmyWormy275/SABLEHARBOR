"""Exact attributed consultation links; never company authority from learner text."""

import copy
import re

from .company_collection import binding
from .company_store import _time
from .store import DomainError, digest

RELATIONS = ("ANSWERS", "CLARIFIES", "CORRECTS", "CANNOT_ESTABLISH")
MAX_MESSAGES = 2000
MAX_QUESTIONS = 500


def require(value, message, *, code="INVALID_CONSULTATION", status=400):
    if not value:
        raise DomainError(message, code=code, status=status)


def message_ref(meeting, message):
    return {"meeting_id": meeting["id"], "message_id": message["id"], "sha256": digest(message)}


def _ref(value):
    require(
        isinstance(value, dict) and set(value) == {"meeting_id", "message_id", "sha256"},
        "Exact consultation message reference required",
    )
    require(
        all(
            isinstance(value[k], str) and 1 <= len(value[k]) <= 128
            for k in ("meeting_id", "message_id")
        )
        and isinstance(value["sha256"], str)
        and re.fullmatch("[0-9a-f]{64}", value["sha256"]),
        "Typed message pins required",
    )


def input_pins(state):
    result = {"status": "AVAILABLE", "questions": []}
    if state.get("phase") != "ACTIVE":
        return {**result, "status": "ENGAGEMENT_NOT_ACTIVE"}
    if state.get("evidence_acquisition") != "COMPANY_SOURCE_COLLECTION":
        return {**result, "status": "NOT_COMPANY_SOURCE_MODE"}
    try:
        meetings = state.get("meetings", [])
        require(isinstance(meetings, list) and len(meetings) <= MAX_MESSAGES, "Input limit")
        people = {p["id"] for p in state["people"] if p.get("status") != "former_employee"}
        seen = set()
        count = 0
        for meeting in meetings:
            require(
                isinstance(meeting, dict) and isinstance(meeting.get("messages"), list),
                "Invalid meeting",
            )
            count += len(meeting["messages"])
            if count > MAX_MESSAGES:
                return {"status": "INPUT_LIMIT_EXCEEDED", "questions": []}
            require(meeting["id"] not in seen, "Duplicate meeting")
            seen.add(meeting["id"])
            if meeting.get("person_id") not in people:
                continue
            question = None
            for message in meeting["messages"]:
                require(
                    isinstance(message, dict)
                    and isinstance(message.get("id"), str)
                    and isinstance(message.get("content"), str),
                    "Invalid message",
                )
                identity = ("message", message["id"])
                require(identity not in seen, "Duplicate message")
                seen.add(identity)
                if _time(message["simulated_at"]) > _time(state["simulated_at"]):
                    question = None
                    continue
                if message.get("role") == "user":
                    question = {
                        "ref": message_ref(meeting, message),
                        "meeting_title": meeting.get("title", meeting["id"]),
                        "person_id": meeting["person_id"],
                        "content": message["content"],
                        "simulated_at": message["simulated_at"],
                        "responses": [],
                    }
                    result["questions"].append(question)
                    if len(result["questions"]) > MAX_QUESTIONS:
                        return {"status": "INPUT_LIMIT_EXCEEDED", "questions": []}
                elif (
                    question
                    and message.get("role") == "assistant"
                    and message.get("claim_type") == "PERSONA_STATEMENT"
                    and message.get("person_id") == meeting["person_id"]
                ):
                    require(
                        _time(message["simulated_at"]) >= _time(question["simulated_at"]),
                        "Response chronology differs",
                    )
                    question["responses"].append(
                        {
                            "ref": message_ref(meeting, message),
                            "person_id": message["person_id"],
                            "content": message["content"],
                            "simulated_at": message["simulated_at"],
                        }
                    )
        return result
    except (ValueError, KeyError, TypeError):
        return {"status": "INPUT_DATA_UNAVAILABLE", "questions": []}


def prepare(engine, actor, state, payload):
    require(
        set(payload) <= {"meeting_id", "content", "source_records", "consultation"},
        "Unexpected consultation submission fields",
    )
    value = payload.get("consultation")
    require(
        isinstance(value, dict) and set(value) == {"kind", "question_ref", "response_ref"},
        "Exact consultation request required",
    )
    require(value["kind"] in ("REFERRAL", "CORRECTION_REQUEST"), "Unknown consultation kind")
    _ref(value["question_ref"])
    if value["response_ref"] is not None:
        _ref(value["response_ref"])
    require(
        value["kind"] != "CORRECTION_REQUEST" or value["response_ref"] is not None,
        "Correction request requires the exact prior company response",
    )
    current = engine.store.get(actor, state["id"])
    require(
        current["revision"] == state["revision"],
        "Engagement changed during consultation",
        status=409,
    )
    index = input_pins(current)
    require(index["status"] == "AVAILABLE", "Consultation input context unavailable", status=409)
    matches = [q for q in index["questions"] if q["ref"] == value["question_ref"]]
    require(len(matches) == 1, "Original question unavailable or changed", status=409)
    question = matches[0]
    response = None
    if value["response_ref"] is not None:
        matches = [r for r in question["responses"] if r["ref"] == value["response_ref"]]
        require(
            len(matches) == 1, "Prior company response does not match this question", status=409
        )
        response = matches[0]
    meetings = [m for m in current["meetings"] if m["id"] == payload.get("meeting_id")]
    require(len(meetings) == 1, "Consulted meeting unavailable")
    meeting = meetings[0]
    people = [
        p
        for p in current["people"]
        if p["id"] == meeting.get("person_id") and p.get("status") != "former_employee"
    ]
    require(len(people) == 1, "Consulted person is not a current scoped contact", status=403)
    require(
        value["kind"] != "REFERRAL" or meeting["person_id"] != question["person_id"],
        "Referral requires a different scoped company contact",
    )
    if meeting.get("control_id"):
        controls = [c for c in current["controls"] if c["id"] == meeting["control_id"]]
        require(len(controls) == 1, "Consulted control unavailable", status=403)
        contacts = set(controls[0].get("owner_ids", [])) | set(
            controls[0].get("assignment", {}).get("proposed_contact_ids", [])
        )
        require(
            meeting["person_id"] in contacts,
            "Contact is not assigned to the consulted control",
            status=403,
        )
    if meeting.get("scheduled_at"):
        from .engine import scoped_datetime

        require(
            _time(scoped_datetime(meeting["scheduled_at"], current["scope"]))
            <= _time(current["simulated_at"]),
            "Consultation is delayed until the scheduled meeting",
            code="CONSULTATION_DELAYED",
            status=409,
        )
    bound = binding(engine, current)
    basis = {
        "revision": current["revision"],
        "scope": current["scope"],
        "binding": bound,
        "evidence_acquisition": current["evidence_acquisition"],
        "people": current["people"],
        "target_meeting": {
            k: meeting.get(k) for k in ("id", "person_id", "control_id", "scheduled_at")
        },
    }
    return {
        "requested": copy.deepcopy(value),
        "context_sha256": digest(basis),
        "question": question,
        "response": response,
        "person_id": meeting["person_id"],
    }


def context_sources(prepared):
    output = []
    for name in ("question", "response"):
        row = prepared[name]
        if row is not None:
            output.append(
                {
                    "id": "CONSULTATION-" + name.upper(),
                    "kind": "ATTRIBUTED_HISTORICAL_STATEMENT",
                    "value": {
                        "text": row["content"],
                        "message_ref": row["ref"],
                        "speaker_role": "LEARNER" if name == "question" else "COMPANY",
                        "person_id": None if name == "question" else row["person_id"],
                        "authority": "STATEMENT_ONLY_NOT_CURRENT_SOURCE_AUTHORITY",
                    },
                }
            )
    return output


def source_manifest(sources):
    return [
        {
            **{k: v for k, v in source["value"].items() if k != "source_locations"},
            "source_id": source["id"],
            "locations": [
                {k: loc[k] for k in ("locator", "text_sha256")}
                for loc in source["value"]["source_locations"]
            ],
        }
        for source in sources
        if source["kind"] == "COMPANY_ORIGINAL_RECORD"
    ]


def validate_reply(result, prepared):
    relation = result.get("consultation_relation")
    require(
        relation in RELATIONS,
        "Company consultation reply requires an explicit relation",
        code="INVALID_MODEL_OUTPUT",
        status=502,
    )
    require(
        relation != "CORRECTS" or prepared["response"] is not None,
        "Correction must identify the exact prior company response",
        code="INVALID_MODEL_OUTPUT",
        status=502,
    )
    require(
        not result.get("proposed_actions"),
        "Consultation cannot execute proposed company actions",
        code="INVALID_MODEL_OUTPUT",
        status=502,
    )


def revalidate(engine, actor, state, payload, prepared, manifest):
    latest = prepare(engine, actor, state, payload)
    require(digest(latest) == digest(prepared), "Consultation context changed", status=409)
    if "source_records" in payload:
        from .company_persona import sources

        current_manifest = source_manifest(
            sources(
                engine,
                actor,
                state,
                prepared["person_id"],
                selected_records=payload["source_records"],
            )
        )
        require(
            digest(current_manifest) == digest(manifest),
            "Consultation source context changed",
            code="SOURCE_CONTEXT_UNAVAILABLE",
            status=403,
        )
    else:
        require(not manifest, "Unselected consultation source context forbidden")


def stored(prepared, *, result=None, manifest=None):
    value = {
        **prepared["requested"],
        "request_authorship": "LEARNER_REQUESTED_COMPANY_CONSULTATION",
        "context_sha256": prepared["context_sha256"],
    }
    if result is not None:
        validate_reply(result, prepared)
        value.update(
            relation=result["consultation_relation"],
            source_support="EXPLICIT_AUTHORIZED_ORIGINALS" if manifest else "SUPPORT_NOT_SUPPLIED",
            source_manifest=manifest or [],
            authority="ATTRIBUTED_COMPANY_STATEMENT_NOT_VERIFIED_CORRECTION",
        )
    return value
