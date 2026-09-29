"""Portal producer contract; no test grant is inferred from an audit role."""

import hashlib
import sqlite3

import pytest

from enterprise.audit_suite.company_rights_producer import (
    AUDIENCE,
    CompanyRightsProducer,
    RightsUnavailable,
    pinned_git_source_reader,
)
from enterprise.audit_suite.store import DomainError, Store

CONTENT = b"synthetic company record\n"
COMMIT = "a" * 40


def policy_validator(row):
    """Stand-in for the accepted policy validator on this older audit branch."""
    for key in ("record_id", "repository_path", "source_sha256", "tenant", "owner_id", "class_id"):
        if not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(key)
    if not isinstance(row.get("purposes"), list) or not row["purposes"]:
        raise ValueError("purposes")
    grants = row.get("grants")
    if not isinstance(grants, list):
        raise ValueError("grants")
    for grant in grants:
        if not grant.get("subject_id") or not grant.get("purpose") or not grant.get("actions"):
            raise ValueError("grant")
    return row


def policy_decide(records, record_id, subject, action, now, *, revoked_ids, tombstones):
    """Test fixture only; cross-repo receipt uses the accepted policy decide."""
    row = records[record_id]
    if (
        subject["id"] in revoked_ids
        or record_id in tombstones
        or row["tenant"] != subject["tenant"]
        or subject["purpose"] not in row["purposes"]
    ):
        return "DENY"
    if any(
        grant["subject_id"] == subject["id"]
        and grant["purpose"] == subject["purpose"]
        and action in grant["actions"]
        for grant in row["grants"]
    ):
        return "ALLOW"
    return "DENY"


@pytest.fixture
def setup(tmp_path):
    audit_root = tmp_path / "audit"
    rights_root = tmp_path / "rights"
    checkpoint_root = tmp_path / "checkpoint"
    for root in (audit_root, rights_root, checkpoint_root):
        root.mkdir(mode=0o700)
    store = Store(audit_root)
    principal = store.provision("Test reviewer", ["reviewer"])
    with store.connect() as db:
        db.execute("INSERT INTO engagements VALUES(?,?,?)", ("ENG-1", 0, "{}"))
    store.grant("ENG-1", principal["id"], "review")
    session = store.login(principal["credential"])
    policy = tmp_path / "policy.json"
    policy.write_text('{"accepted":"test-only"}')
    sources = {"docs/source.txt": CONTENT}
    producer = CompanyRightsProducer(
        store=store,
        rights_root=rights_root,
        checkpoint_root=checkpoint_root,
        policy_file=policy,
        policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
        source_commit=COMMIT,
        source_bytes=lambda path: sources[path],
        validate_record=policy_validator,
        decide=policy_decide,
        known_person_ids=frozenset({"PERSON-1", "PERSON-2"}),
    )
    return producer, store, principal, session, policy, sources


def record(*, actions=None):
    return {
        "record_id": "REC-1",
        "repository_path": "docs/source.txt",
        "source_sha256": hashlib.sha256(CONTENT).hexdigest(),
        "source_version": "1",
        "tenant": "SH",
        "owner_id": "OWNER-1",
        "class_id": "WORKING_OPERATIONS",
        "available_at": "2026-09-22T00:00:00+00:00",
        "effective_at": "2026-09-22T00:00:00+00:00",
        "purposes": ["inspection"],
        "restriction_reason": "Business working",
        "restriction_authority": "POLICY-1",
        "challenge_route": "Information Governance",
        "review_due": "2026-12-21T00:00:00+00:00",
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


def populated(setup, *, actions=None):
    producer, _, principal, _, _, _ = setup
    producer.bind_person(
        principal_id=principal["id"],
        engagement_id="ENG-1",
        person_id="PERSON-1",
        tenant="SH",
        purpose="inspection",
        expected_revision=0,
    )
    producer.put_record(record(actions=actions), expected_revision=1)
    return producer


def test_explicit_session_binding_source_and_gateway_schema(setup):
    producer, store, principal, session, _, _ = setup
    with pytest.raises(RightsUnavailable, match="binding"):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    with pytest.raises(RightsUnavailable, match="population"):
        producer.bind_person(
            principal_id=principal["id"],
            engagement_id="ENG-1",
            person_id="OUTSIDER",
            tenant="SH",
            purpose="inspection",
            expected_revision=0,
        )
    producer = populated(setup, actions=["read", "snippet", "count", "answer", "export"])
    snap = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    checkpoint = producer.checkpoint()
    assert snap["audience"] == AUDIENCE
    assert snap["source_commit"] == COMMIT
    assert snap["rights_revision"] == "revision-2"
    assert snap["revocation_epoch"] == checkpoint["epoch"] == "epoch-2"
    assert snap["assertion"]["id"] == "PERSON-1"
    assert snap["assertion"]["session_id"] == store._key_hash(session["token"])
    assert snap["assertion"]["engagement_id"] == "ENG-1"
    assert snap["records"]["REC-1"]["grants"][0]["actions"] == [
        "read",
        "snippet",
        "count",
        "answer",
        "export",
    ]
    assert snap["records"]["REC-1"]["source_sha256"] == hashlib.sha256(CONTENT).hexdigest()
    assert (
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
        == "REC-1"
    )
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=b"wrong bytes",
            action="read",
        )
    assert producer.visible_population(
        session_token=session["token"],
        engagement_id="ENG-1",
        candidates=[
            {"path": "docs/source.txt", "content": CONTENT},
            {"path": "docs/source.txt", "content": b"wrong bytes"},
        ],
        action="count",
        complete=True,
    ) == [{"path": "docs/source.txt", "content": CONTENT}]
    with pytest.raises(RightsUnavailable, match="Complete"):
        producer.visible_population(
            session_token=session["token"],
            engagement_id="ENG-1",
            candidates=[],
            action="count",
            complete=False,
        )
    with pytest.raises(RightsUnavailable, match="revision"):
        producer.put_record(record(), expected_revision=1)
    store.logout(session["token"])
    with pytest.raises(DomainError):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")


def test_bearer_other_engagement_revoked_principal_and_missing_grants_fail(setup):
    producer, store, principal, session, _, _ = setup
    producer = populated(setup)
    snap = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    assert snap["records"]["REC-1"]["grants"] == []
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    for token, engagement in ((principal["credential"], "ENG-1"), (session["token"], "ENG-OTHER")):
        with pytest.raises(DomainError):
            producer.snapshot(session_token=token, engagement_id=engagement)
    store.revoke(principal["id"])
    with pytest.raises(DomainError):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")


def test_wrong_tenant_purpose_and_stale_authentication(setup):
    producer, store, principal, session, _, _ = setup
    producer = populated(setup, actions=["read"])
    producer.bind_person(
        principal_id=principal["id"],
        engagement_id="ENG-1",
        person_id="PERSON-1",
        tenant="OTHER",
        purpose="inspection",
        expected_revision=2,
    )
    snap = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    row = snap["records"]["REC-1"]
    assert row["tenant"] != snap["assertion"]["tenant"]
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    producer.bind_person(
        principal_id=principal["id"],
        engagement_id="ENG-1",
        person_id="PERSON-1",
        tenant="SH",
        purpose="other",
        expected_revision=3,
    )
    snap = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    assert snap["assertion"]["purpose"] not in snap["records"]["REC-1"]["purposes"]
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    with store.connect() as db:
        db.execute(
            "UPDATE sessions SET authenticated_at=NULL WHERE token_hash=?",
            (store._key_hash(session["token"]),),
        )
    with pytest.raises(DomainError):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")


def test_source_policy_and_validator_failure_stops_snapshot(setup):
    producer, _, _, session, policy, sources = setup
    producer = populated(setup, actions=["read"])
    sources["docs/source.txt"] = b"changed"
    with pytest.raises(RightsUnavailable, match="Source bytes"):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    sources["docs/source.txt"] = CONTENT
    policy.write_text("{}")
    with pytest.raises(RightsUnavailable, match="policy pin"):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")


def test_checkpoint_revocation_deletion_hold_and_restore_are_monotonic(setup):
    producer, _, _, session, _, _ = setup
    producer = populated(setup, actions=["read", "export"])
    old = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    assert producer.set_hold("REC-1", held=True) == 3
    held = producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    assert held["records"]["REC-1"]["legal_hold"] is True
    assert old["revocation_epoch"] != producer.checkpoint()["epoch"]
    assert (
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
        == "REC-1"
    )
    assert producer.delete_record("REC-1") == 4
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    assert producer.record_restore("REC-1") == 5
    assert producer.checkpoint()["tombstones"] == ["REC-1"]
    assert producer.set_person_revoked("PERSON-1", revoked=True) == 6
    with pytest.raises(RightsUnavailable, match="revoked"):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    assert producer.checkpoint()["revoked_ids"] == ["PERSON-1"]


def test_old_rights_backup_cannot_pass_new_checkpoint(setup):
    producer, _, _, session, _, _ = setup
    producer = populated(setup, actions=["read"])
    producer.put_record(record(actions=["read", "export"]), expected_revision=2)
    with sqlite3.connect(producer.rights_db) as db:
        db.execute("UPDATE state SET revision=2")
    with pytest.raises(RightsUnavailable, match="restored"):
        producer.snapshot(session_token=session["token"], engagement_id="ENG-1")
    with pytest.raises(RightsUnavailable, match="restored"):
        producer.checkpoint()


def test_rights_change_during_population_filter_fails_whole_result(setup, monkeypatch):
    producer, _, principal, session, _, _ = setup
    producer = populated(setup, actions=["count"])
    original = producer.authorize_disclosure

    def changing(**kwargs):
        result = original(**kwargs)
        producer.bind_person(
            principal_id=principal["id"],
            engagement_id="ENG-1",
            person_id="PERSON-1",
            tenant="SH",
            purpose="inspection",
            expected_revision=2,
        )
        return result

    monkeypatch.setattr(producer, "authorize_disclosure", changing)
    with pytest.raises(RightsUnavailable, match="changed"):
        producer.visible_population(
            session_token=session["token"],
            engagement_id="ENG-1",
            candidates=[{"path": "docs/source.txt", "content": CONTENT}],
            action="count",
            complete=True,
        )


def test_pinned_git_reader_uses_commit_not_working_copy(tmp_path):
    import subprocess

    repo = tmp_path / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "record.txt").write_bytes(CONTENT)
    subprocess.run(["git", "-C", str(repo), "add", "record.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "source",
        ],
        check=True,
    )
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    reader = pinned_git_source_reader(repo, commit)
    (repo / "record.txt").write_bytes(b"later working copy")
    assert reader("record.txt") == CONTENT
    with pytest.raises(RightsUnavailable):
        reader("../record.txt")
