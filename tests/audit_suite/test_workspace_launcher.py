"""Public CLEAN/MESSY workspace launcher against a small slice of the Git company records."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.service import create_app
from tools.audit_suite import workspace_launcher as launcher

SYSTEM = "person-access-history.denominator_snapshot"


@pytest.fixture
def small_history(monkeypatch):
    """Keep the real manifest, bytes and provenance but import only a few systems."""
    original = launcher.history_records

    def subset(history):
        records, systems, provenance = original(history)
        chosen = {SYSTEM, *sorted({s["system"] for s in systems})[:2]}
        return (
            [r for r in records if r["system"] in chosen],
            [s for s in systems if s["system"] in chosen],
            provenance,
        )

    monkeypatch.setattr(launcher, "history_records", subset)
    monkeypatch.setattr(launcher, "MODES", {"CLEAN": launcher.MODES["CLEAN"]})


def client_for(root, role, paths):
    app = create_app(
        paths["state"],
        company_root=paths["company"],
        company_bindings=paths["bindings"],
        allowed_hosts=["testserver"],
    )
    client = TestClient(app, base_url="https://testserver")
    credential = json.loads((root / "credentials" / f"clean-{role}.json").read_text())
    login = client.post("/api/session", json={"credential": credential["credential"]})
    return client, login


def command(client, csrf, engagement, state, kind, payload, command_id):
    response = client.post(
        f"/api/engagements/{engagement}/commands",
        headers={"X-CSRF-Token": csrf},
        json={
            "command_id": command_id,
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_setup_binds_activates_and_collects_exact_company_original(tmp_path, small_history):
    root = tmp_path / "workspace"
    launcher.private_directory(root)
    summary = launcher.setup_mode(root, "CLEAN", 1)
    assert summary["branch"] == "HARBOR-OPERATIONS-A"
    assert summary["phase"] == "READY"
    assert summary["systems"] == 3
    for role in launcher.ROLES:
        path = root / "credentials" / f"clean-{role}.json"
        assert path.stat().st_mode & 0o777 == 0o600
    paths = launcher.mode_paths(root, "CLEAN")
    with pytest.raises(launcher.LauncherError, match="already exists"):
        launcher.setup_mode(root, "CLEAN", 1)

    client, login = client_for(root, "auditor", paths)
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    engagement = summary["engagement_id"]
    state = client.get(f"/api/engagements/{engagement}").json()
    assert state["company_source_binding"]["branch"] == "HARBOR-OPERATIONS-A"
    state = command(client, csrf, engagement, state, "kickoff.start", {}, "kickoff")
    control = state["controls"][0]
    state = command(
        client,
        csrf,
        engagement,
        state,
        "pbc.create",
        {
            "title": "Access denominators",
            "purpose": "Monthly access populations",
            "control_id": control["id"],
            "boundary_id": state["scope"]["boundaries"][0],
        },
        "request",
    )
    request_id = state["requests"][-1]["id"]
    state = command(
        client, csrf, engagement, state, "pbc.issue", {"request_id": request_id}, "issue"
    )
    systems = client.get(f"/api/engagements/{engagement}/company/systems").json()["systems"]
    assert SYSTEM in {s["system"] for s in systems}
    records = client.get(f"/api/engagements/{engagement}/company/systems/{SYSTEM}/records")
    first = records.json()["records"][0]
    state = command(
        client,
        csrf,
        engagement,
        state,
        "company.collect",
        {
            "system_id": SYSTEM,
            "record_id": first["record"],
            "version": first["version"],
            "request_id": request_id,
        },
        "collect",
    )
    artifact = state["artifacts"][-1]
    download = client.get(f"/api/engagements/{engagement}/artifacts/{artifact['id']}/download")
    assert download.status_code == 200
    manifest = json.loads((launcher.RECORDS / "manifest.json").read_text())
    delivered = next(
        r
        for r in manifest["records"]
        if r["history_id"] == "history-01"
        and r["system"] == SYSTEM
        and r["record"] == first["record"]
        and r["version"] == first["version"]
    )
    assert hashlib.sha256(download.content).hexdigest() == delivered["sha256"]


def test_reissued_credentials_revoke_previous_roles(tmp_path, small_history):
    root = tmp_path / "workspace"
    launcher.private_directory(root)
    summary = launcher.setup_mode(root, "CLEAN", 1)
    paths = launcher.mode_paths(root, "CLEAN")
    previous = json.loads((root / "credentials/clean-auditor.json").read_text())["credential"]
    assert launcher.reissue_credentials(root, 1) == {"CLEAN": sorted(launcher.ROLES)}
    client, login = client_for(root, "auditor", paths)
    assert login.status_code == 200
    listing = client.get("/api/bootstrap").json()["engagements"]
    assert [e["id"] for e in listing] == [summary["engagement_id"]]
    assert client.post("/api/session", json={"credential": previous}).status_code == 401
    assert launcher.status(root)["modes"]["CLEAN"]["status"] == "STOPPED"
