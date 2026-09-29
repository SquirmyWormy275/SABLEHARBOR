from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app


@pytest.mark.parametrize(
    "zone,initial_offset,march_offset,november_offset",
    [("America/Denver", "-07:00", "-06:00", "-07:00"), ("UTC", "+00:00", "+00:00", "+00:00")],
)
def test_api_date_only_fieldwork_clock_and_meeting_use_scope_timezone(
    tmp_path, zone, initial_offset, march_offset, november_offset
):
    app = create_app(tmp_path / "state", allowed_hosts=["testserver"])
    engine = app.state.engine
    user = engine.store.provision("Timezone learner", ["learner"])
    client = TestClient(app, base_url="https://testserver")
    login = client.post("/api/session", json={"credential": user["credential"]})
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    response = client.post(
        "/api/engagements",
        headers=headers,
        json={
            "title": "Dated API exercise",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {},
            "scope": {
                "programs": ["HIPAA"],
                "report_type": "Internal assessment",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2027-03-12",
                "timezone": zone,
                "boundaries": ["corporate"],
            },
        },
    )
    assert response.status_code == 200, response.text
    state = response.json()
    assert state["simulated_at"] == "2027-03-12T09:00:00" + initial_offset
    # Isolate clock behavior from generation/model availability using an explicit
    # fixture phase transition; every operation under test goes through the API.
    state = engine.store.command(
        user["id"],
        state["id"],
        {
            "command_id": "fixture-activation",
            "expected_revision": state["revision"],
            "kind": "fixture.activate",
            "payload": {},
        },
        lambda current, *_: {**current, "phase": "ACTIVE"},
        permissions={"learn"},
    )

    def command(kind, payload):
        nonlocal state
        response = client.post(
            "/api/engagements/" + state["id"] + "/commands",
            headers=headers,
            json={
                "command_id": kind + str(state["revision"]),
                "expected_revision": state["revision"],
                "kind": kind,
                "payload": payload,
            },
        )
        assert response.status_code == 200, response.text
        state = response.json()
        return state

    command("clock.advance", {"mode": "date", "target": "2027-03-15"})
    assert datetime.fromisoformat(state["simulated_at"]) == datetime.fromisoformat(
        "2027-03-15T09:00:00" + march_offset
    )
    explicit = "2027-03-16T18:30:00+02:00"
    command(
        "meeting.create",
        {
            "title": "Explicit-offset meeting",
            "person_id": state["people"][0]["id"],
            "scheduled_at": explicit,
        },
    )
    assert state["meetings"][-1]["scheduled_at"] == explicit
    command(
        "meeting.create",
        {
            "title": "Date-only meeting",
            "person_id": state["people"][0]["id"],
            "scheduled_at": "2027-11-08",
        },
    )
    assert state["meetings"][-1]["scheduled_at"] == "2027-11-08T09:00:00" + november_offset
    command("clock.advance", {"mode": "date", "target": "2027-11-08"})
    assert datetime.fromisoformat(state["simulated_at"]) == datetime.fromisoformat(
        "2027-11-08T09:00:00" + november_offset
    )
    assert datetime.fromisoformat(state["simulated_at"]).astimezone(ZoneInfo(zone)).hour == 9
