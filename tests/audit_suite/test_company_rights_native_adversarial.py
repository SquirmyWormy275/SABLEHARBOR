"""Adversarial contract for the opt-in company rights and legacy portal routes.

These assertions deliberately fail on the isolated producer branch until the
same rights boundary covers native discovery, collection, and retained bytes.
They are a handoff to the portal integration owner, not a deployment claim.
"""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.company_native_rights import NativeRecordClosure
from enterprise.audit_suite.company_rights_producer import (
    CompanyRightsProducer,
    RightsUnavailable,
)
from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_company_rights_http import decide, row, validate_record


@pytest.fixture
def protected_company(tmp_path):
    for name in ("rights", "checkpoint", "company"):
        (tmp_path / name).mkdir(mode=0o700)
    policy = tmp_path / "policy.json"
    policy.write_text('{"accepted":"test-only"}')
    raw = b"PRIVATE-SYNTHETIC-COMPANY-RECORD\n"
    producer_holder = {}
    closure_file = tmp_path / "native-closure.json"
    closure_file.write_text(
        json.dumps(
            {
                "version": 1,
                "source_commit": "a" * 40,
                "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
                "records": [
                    {
                        "company": "SH",
                        "branch": "base",
                        "system": "identity",
                        "record": "REC-1",
                        "version": 1,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "policy_record_id": "REC-1",
                        "repository_path": "docs/company.txt",
                    }
                ],
            }
        )
    )

    def factory(engine):
        producer = CompanyRightsProducer(
            store=engine.store,
            rights_root=tmp_path / "rights",
            checkpoint_root=tmp_path / "checkpoint",
            policy_file=policy,
            policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
            source_commit="a" * 40,
            source_bytes=lambda path: {"docs/company.txt": raw}[path],
            validate_record=validate_record,
            decide=decide,
            known_person_ids=frozenset({"PERSON-1"}),
        )
        producer_holder["producer"] = producer
        return producer

    app = create_app(
        tmp_path / "audit",
        company_root=tmp_path / "company",
        allowed_hosts=["testserver"],
        company_rights_factory=factory,
        company_native_rights_factory=lambda _engine, producer: NativeRecordClosure(
            producer=producer,
            manifest_file=closure_file,
            manifest_sha256=hashlib.sha256(closure_file.read_bytes()).hexdigest(),
        ),
    )
    engine = app.state.engine
    person = engine.store.provision("Auditor", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Protected source audit",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-06-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(person["id"], state, "create")
    engine.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    company = engine.company_store
    company.register_system("SH", "base", "identity", "owner")
    company.append_version(
        "SH",
        "base",
        "identity",
        "REC-1",
        expected_version=0,
        command_id="import",
        event_at="2026-09-01T00:00:00Z",
        available_at="2026-09-22T00:00:00Z",
        content=raw,
        provenance={"source_reference": "synthetic-test-original", "name": "company.txt"},
    )
    # An ordinary audit system grant must not act as a per-record disclosure
    # grant when the protected company rights producer is installed.
    company.grant(person["id"], state["id"], "SH", "base", "identity")
    client = TestClient(app, base_url="https://testserver")
    login = client.post("/api/session", json={"credential": person["credential"]})
    assert login.status_code == 200
    producer = producer_holder["producer"]
    producer.bind_person(
        principal_id=person["id"],
        engagement_id=state["id"],
        person_id="PERSON-1",
        tenant="SH",
        purpose="inspection",
        expected_revision=0,
    )
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, None),
        expected_revision=1,
    )
    return app, client, engine, state, producer, raw, login.json()["csrf_token"]


def _root(state):
    return f"/api/engagements/{state['id']}"


def _collect(client, state, csrf):
    return client.post(
        _root(state) + "/commands",
        headers={"X-CSRF-Token": csrf},
        json={
            "command_id": "collect",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {
                "system_id": "identity",
                "record_id": "REC-1",
                "version": 1,
                "request_id": "R1",
            },
        },
    )


def test_native_discovery_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, _ = protected_company
    root = _root(state)
    assert client.get(root + "/company/rights/records/REC-1").status_code == 403
    assert client.get(root + "/company/rights/count?q=PRIVATE").json() == {"count": 0}
    assert client.get(root + "/company/rights/search?q=PRIVATE").json()["records"] == []
    systems = client.get(root + "/company/systems")
    assert systems.status_code in {403, 404} or systems.json() == {"systems": []}


def test_native_record_metadata_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, _ = protected_company
    root = _root(state)
    records = client.get(root + "/company/systems/identity/records")
    assert records.status_code in {403, 404} or records.json()["records"] == []


def test_native_collection_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, csrf = protected_company
    assert _collect(client, state, csrf).status_code in {403, 404}


def test_retained_download_rechecks_deleted_company_record(protected_company):
    _, client, engine, state, producer, raw, _ = protected_company
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, ["read", "export"]),
        expected_revision=2,
    )
    # Model a source already collected into retained audit evidence before the
    # protected HTTP path is enabled or while the record was still permitted.
    saved = engine.command(
        state["created_by"],
        state["id"],
        {
            "command_id": "collect-prior",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {
                "system_id": "identity",
                "record_id": "REC-1",
                "version": 1,
                "request_id": "R1",
            },
        },
    )
    artifact_id = saved["artifacts"][0]["id"]
    url = _root(state) + f"/artifacts/{artifact_id}/download"
    before = client.get(url)
    assert before.status_code == 200, before.text
    producer.delete_record("REC-1")
    assert client.get(_root(state) + "/company/rights/records/REC-1").status_code == 403
    denied = client.get(url)
    missing = client.get(_root(state) + "/artifacts/ART-MISSING/download")
    assert denied.status_code == missing.status_code == 403
    assert denied.json() == missing.json()


def test_native_closure_rejects_wrong_version_bytes_path_and_changed_manifest(protected_company):
    app, client, engine, state, producer, raw, _ = protected_company
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, ["read", "export"]),
        expected_revision=2,
    )
    token = next(iter(client.cookies.values()))
    native = engine.company_store.read_version(
        state["created_by"],
        state["id"],
        "SH",
        "base",
        "identity",
        "REC-1",
        version=1,
        as_of="2026-09-29T00:00:00+00:00",
    )
    closure = app.state.company_native_rights
    assert (
        closure.authorize_version(
            session_token=token,
            engagement_id=state["id"],
            native=native,
            action="export",
        )
        == "REC-1"
    )
    for changed in (
        {**native, "version": 2},
        {**native, "record": "REC-OTHER"},
        {**native, "content": b"wrong bytes"},
        {**native, "sha256": "0" * 64},
    ):
        with pytest.raises(RightsUnavailable):
            closure.authorize_version(
                session_token=token,
                engagement_id=state["id"],
                native=changed,
                action="export",
            )
    path = closure.manifest_file
    original = path.read_bytes()
    try:
        altered = json.loads(original)
        altered["records"][0]["repository_path"] = "docs/other.txt"
        path.write_text(json.dumps(altered))
        with pytest.raises(RightsUnavailable, match="manifest changed"):
            closure.authorize_version(
                session_token=token,
                engagement_id=state["id"],
                native=native,
                action="export",
            )
    finally:
        path.write_bytes(original)


def test_retained_company_export_rechecks_native_grant_and_person_revocation(protected_company):
    _, client, engine, state, producer, raw, _ = protected_company
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, ["read", "export"]),
        expected_revision=2,
    )
    saved = engine.command(
        state["created_by"],
        state["id"],
        {
            "command_id": "collect-prior",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {
                "system_id": "identity",
                "record_id": "REC-1",
                "version": 1,
                "request_id": "R1",
            },
        },
    )
    url = _root(state) + f"/artifacts/{saved['artifacts'][0]['id']}/download"
    assert client.get(url).status_code == 200
    engine.company_store.grant(
        state["created_by"],
        state["id"],
        "SH",
        "base",
        "identity",
        active=False,
    )
    assert client.get(url).status_code == 403
    engine.company_store.grant(
        state["created_by"],
        state["id"],
        "SH",
        "base",
        "identity",
        active=True,
    )
    producer.set_person_revoked("PERSON-1", revoked=True)
    assert client.get(url).status_code == 403
