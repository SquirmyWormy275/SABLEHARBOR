"""Opt-in portal HTTP disclosure uses explicit company rights, not audit system grants."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.company_rights_producer import CompanyRightsProducer
from enterprise.audit_suite.service import create_app


def validate_record(row):
    """Test-only stand-in; live configuration must use accepted policy code."""
    if (
        not row.get("record_id")
        or not row.get("source_sha256")
        or not isinstance(row.get("grants"), list)
    ):
        raise ValueError("Exact policy row required")
    return row


def decide(records, record_id, subject, action, now, *, revoked_ids, tombstones):
    row = records[record_id]
    if (
        subject["id"] in revoked_ids
        or record_id in tombstones
        or row["tenant"] != subject["tenant"]
        or subject["purpose"] not in row["purposes"]
        or datetime.fromisoformat(now) < datetime.fromisoformat(row["available_at"])
    ):
        return "DENY"
    return (
        "ALLOW"
        if any(
            grant["subject_id"] == subject["id"]
            and grant["purpose"] == subject["purpose"]
            and action in grant["actions"]
            for grant in row["grants"]
        )
        else "DENY"
    )


@pytest.fixture
def workspace(tmp_path):
    for name in ("rights", "checkpoint", "company"):
        (tmp_path / name).mkdir(mode=0o700)
    policy = tmp_path / "policy.json"
    policy.write_text('{"accepted":"test-only"}')
    sources = {
        "docs/allowed.txt": b"Synthetic allowed company fact.\n",
        "docs/denied.txt": b"Synthetic denied company fact.\n",
    }
    selected = {}

    def factory(engine):
        producer = CompanyRightsProducer(
            store=engine.store,
            rights_root=tmp_path / "rights",
            checkpoint_root=tmp_path / "checkpoint",
            policy_file=policy,
            policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
            source_commit="a" * 40,
            source_bytes=lambda path: sources[path],
            validate_record=validate_record,
            decide=decide,
            known_person_ids=frozenset({"PERSON-1"}),
        )
        selected["producer"] = producer
        return producer

    app = create_app(
        tmp_path / "audit",
        company_root=tmp_path / "company",
        allowed_hosts=["testserver"],
        company_rights_factory=factory,
    )
    store = app.state.engine.store
    person = store.provision("Auditor", ["learner"])
    with store.connect() as db:
        db.execute("INSERT INTO engagements VALUES(?,?,?)", ("ENG-1", 0, "{}"))
    store.grant("ENG-1", person["id"], "learn")
    company = app.state.engine.company_store
    company.register_system("SH", "base", "IAM", "owner")
    company.grant(person["id"], "ENG-1", "SH", "base", "IAM")
    client = TestClient(app, base_url="https://testserver")
    root = "/api/engagements/ENG-1/company/rights"
    return client, selected["producer"], store, person, policy, sources, root


def row(record_id, path, content, actions):
    return {
        "record_id": record_id,
        "repository_path": path,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "source_version": "1",
        "tenant": "SH",
        "owner_id": "OWNER-1",
        "class_id": "WORKING_OPERATIONS",
        "effective_at": "2026-09-22T00:00:00+00:00",
        "available_at": "2026-09-22T00:00:00+00:00",
        "purposes": ["inspection"],
        "restriction_reason": "Synthetic test selection",
        "restriction_authority": "TEST-ONLY",
        "challenge_route": "Information Governance",
        "review_due": "2026-12-21T00:00:00+00:00",
        "sources": [],
        "grants": (
            []
            if actions is None
            else [
                {
                    "subject_id": "PERSON-1",
                    "purpose": "inspection",
                    "actions": actions,
                    "start": "2026-09-22T00:00:00+00:00",
                    "end": None,
                }
            ]
        ),
    }


def bind(producer, person, *, tenant="SH", purpose="inspection", revision=0):
    return producer.bind_person(
        principal_id=person["id"],
        engagement_id="ENG-1",
        person_id="PERSON-1",
        tenant=tenant,
        purpose=purpose,
        expected_revision=revision,
    )


def test_http_boundary_requires_explicit_trusted_factory(tmp_path):
    app = create_app(tmp_path / "audit", allowed_hosts=["testserver"])
    store = app.state.engine.store
    person = store.provision("Auditor", ["learner"])
    with store.connect() as db:
        db.execute("INSERT INTO engagements VALUES(?,?,?)", ("ENG-1", 0, "{}"))
    store.grant("ENG-1", person["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    client.post("/api/session", json={"credential": person["credential"]})
    assert client.get("/api/engagements/ENG-1/company/rights/count?q=Synthetic").status_code == 503


def test_http_defaults_closed_and_never_uses_system_grant_as_record_right(workspace):
    client, producer, _, person, _, sources, root = workspace
    direct = root + "/records/REC-1"
    assert client.get(direct).status_code == 401
    assert client.post("/api/session", json={"credential": person["credential"]}).status_code == 200
    assert client.get(direct).status_code == 403  # Native IAM system grant is insufficient.
    assert client.get(direct + "?person_id=PERSON-1").status_code == 422
    bind(producer, person)
    producer.put_record(
        row("REC-1", "docs/allowed.txt", sources["docs/allowed.txt"], None), expected_revision=1
    )
    assert client.get(direct).status_code == 403  # No implicit record grant.
    assert client.get(root + "/search?q=Synthetic").json() == {
        "records": [],
        "next_offset": None,
    }
    assert client.get(root + "/count?q=Synthetic").json() == {"count": 0}
    bearer = TestClient(client.app, base_url="https://testserver")
    assert (
        bearer.get(direct, headers={"Authorization": "Bearer " + person["credential"]}).status_code
        == 401
    )


def test_http_exact_actions_filter_before_paging_and_count(workspace):
    client, producer, _, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    producer.put_record(
        row("A-DENIED", "docs/denied.txt", sources["docs/denied.txt"], None), expected_revision=1
    )
    producer.put_record(
        row(
            "B-ALLOW",
            "docs/allowed.txt",
            sources["docs/allowed.txt"],
            ["read", "search", "snippet", "count", "export"],
        ),
        expected_revision=2,
    )
    direct = root + "/records/B-ALLOW"
    direct_response = client.get(direct)
    assert direct_response.content == sources["docs/allowed.txt"]
    assert direct_response.headers["cache-control"] == "no-store, private"
    snippet_response = client.get(direct + "/snippet")
    assert snippet_response.headers["cache-control"] == "no-store, private"
    assert snippet_response.json() == {
        "record_id": "B-ALLOW",
        "snippet": sources["docs/allowed.txt"].decode(),
    }
    exported = client.get(direct + "/export")
    assert exported.status_code == 200 and exported.content == sources["docs/allowed.txt"]
    assert exported.headers["cache-control"] == "no-store, private"
    assert client.get(root + "/search?q=Synthetic&limit=1&offset=0").json() == {
        "records": [{"record_id": "B-ALLOW"}],
        "next_offset": None,
    }
    assert client.get(root + "/count?q=Synthetic").json() == {"count": 1}
    assert client.get(root + "/records/A-DENIED").status_code == 403
    assert client.get(root + "/search?q=Synthetic&limit=0").status_code == 422
    assert client.get(root + "/search?q=Synthetic&purpose=inspection").status_code == 422
    assert client.get(root + "/count?q=Synthetic&offset=1").status_code == 422


def test_http_stale_wrong_subject_deleted_and_revoked_fail_closed(workspace):
    client, producer, _, person, policy, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    producer.put_record(
        row(
            "REC-1",
            "docs/allowed.txt",
            sources["docs/allowed.txt"],
            ["read", "search", "count", "export"],
        ),
        expected_revision=1,
    )
    direct = root + "/records/REC-1"
    assert client.get(direct).status_code == 200
    bind(producer, person, tenant="OTHER", revision=2)
    assert client.get(direct).status_code == 403
    bind(producer, person, purpose="other", revision=3)
    assert client.get(direct).status_code == 403
    bind(producer, person, revision=4)
    assert client.get(direct).status_code == 200
    sources["docs/allowed.txt"] = b"changed"
    assert client.get(direct).status_code == 403
    assert client.get(root + "/search?q=Synthetic").status_code == 403
    sources["docs/allowed.txt"] = b"Synthetic allowed company fact.\n"
    policy.write_text("{}")
    assert client.get(direct).status_code == 403
    policy.write_text('{"accepted":"test-only"}')
    producer.delete_record("REC-1")
    producer.record_restore("REC-1")
    assert client.get(direct).status_code == 403
    producer.set_person_revoked("PERSON-1", revoked=True)
    assert client.get(root + "/count?q=Synthetic").status_code == 403


def test_http_revision_change_during_search_discards_whole_page(workspace, monkeypatch):
    client, producer, _, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    producer.put_record(
        row("REC-1", "docs/allowed.txt", sources["docs/allowed.txt"], ["search", "count"]),
        expected_revision=1,
    )
    original = producer.visible_population

    def changing(**kwargs):
        result = original(**kwargs)
        producer.bind_person(
            principal_id=person["id"],
            engagement_id="ENG-1",
            person_id="PERSON-1",
            tenant="SH",
            purpose="inspection",
            expected_revision=2,
        )
        return result

    monkeypatch.setattr(producer, "visible_population", changing)
    assert client.get(root + "/search?q=Synthetic").status_code == 403


def test_http_only_granted_action_and_authenticated_cookie(workspace):
    client, producer, store, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    producer.put_record(
        row("REC-1", "docs/allowed.txt", sources["docs/allowed.txt"], ["read"]),
        expected_revision=1,
    )
    direct = root + "/records/REC-1"
    assert client.get(direct).status_code == 200
    assert client.get(direct + "/snippet").status_code == 403
    assert client.get(direct + "/export").status_code == 403
    assert client.get(root + "/search?q=Synthetic").json()["records"] == []
    assert client.get(root + "/count?q=Synthetic").json()["count"] == 0
    assert (
        client.get(direct, headers={"Authorization": "Bearer " + person["credential"]}).status_code
        == 401
    )
    store.revoke(person["id"])
    assert client.get(direct).status_code == 401


def test_http_revocation_during_direct_decision_discards_bytes(workspace, monkeypatch):
    client, producer, _, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    producer.put_record(
        row("REC-1", "docs/allowed.txt", sources["docs/allowed.txt"], ["read"]),
        expected_revision=1,
    )

    def revoke_during_decision(*args, **kwargs):
        producer.set_person_revoked("PERSON-1", revoked=True)
        return "ALLOW"

    monkeypatch.setattr(producer, "decide", revoke_during_decision)
    response = client.get(root + "/records/REC-1")
    assert response.status_code == 403
    assert sources["docs/allowed.txt"] not in response.content


def test_future_source_is_unavailable_by_wall_time(workspace):
    client, producer, _, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    future = row("REC-2027", "docs/allowed.txt", sources["docs/allowed.txt"], ["read", "count"])
    future["available_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    producer.put_record(future, expected_revision=1)
    assert client.get(root + "/records/REC-2027").status_code == 403
    assert client.get(root + "/count?q=Synthetic").json() == {"count": 0}


def test_http_rechecks_server_engagement_case_time_before_direct_and_count(workspace, monkeypatch):
    client, producer, _, person, _, sources, root = workspace
    client.post("/api/session", json={"credential": person["credential"]})
    bind(producer, person)
    future = row("REC-1", "docs/allowed.txt", sources["docs/allowed.txt"], ["read", "count"])
    future["available_at"] = "2027-08-31T00:00:00+00:00"
    producer.put_record(future, expected_revision=1)

    approved = {"time": "2028-01-01T00:00:00+00:00"}

    # Test-only independently approved clock, injected as trusted server code.
    def case_resolver(context):
        assert context.engagement_id == "ENG-1" and context.person_id == "PERSON-1"
        return approved["time"]

    producer.case_as_of = case_resolver
    assert client.get(root + "/records/REC-1").status_code == 200
    assert client.get(root + "/count?q=Synthetic").json() == {"count": 1}

    original_direct = producer.authorize_disclosure

    def changing_direct(**kwargs):
        result = original_direct(**kwargs)
        approved["time"] = "2026-09-22T00:00:00+00:00"
        return result

    monkeypatch.setattr(producer, "authorize_disclosure", changing_direct)
    assert client.get(root + "/records/REC-1").status_code == 403
    monkeypatch.setattr(producer, "authorize_disclosure", original_direct)

    approved["time"] = "2028-01-01T00:00:00+00:00"
    original_population = producer.visible_population

    def changing_population(**kwargs):
        result = original_population(**kwargs)
        approved["time"] = "2026-09-22T00:00:00+00:00"
        return result

    monkeypatch.setattr(producer, "visible_population", changing_population)
    assert client.get(root + "/count?q=Synthetic").status_code == 403
