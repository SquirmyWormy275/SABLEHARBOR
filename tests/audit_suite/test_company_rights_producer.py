"""Portal producer contract; no test grant is inferred from an audit role."""

import hashlib
import json
import sqlite3
import time
from datetime import datetime

import pytest

from enterprise.audit_suite.company_rights_producer import (
    AUDIENCE,
    CompanyRightsProducer,
    RightsUnavailable,
    VerifiedCaseContext,
    pinned_git_source_reader,
)
from enterprise.audit_suite.engine import COLLECTIONS, Engine
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


def temporal_decide(records, record_id, subject, action, at, *, revoked_ids, tombstones):
    row = records[record_id]
    moment = datetime.fromisoformat(at)
    if moment < datetime.fromisoformat(row["available_at"]):
        return "DENY"
    if moment < datetime.fromisoformat(row["effective_at"]):
        return "DENY"
    if not any(
        moment >= datetime.fromisoformat(grant["start"])
        and (grant["end"] is None or moment < datetime.fromisoformat(grant["end"]))
        for grant in row["grants"]
    ):
        return "DENY"
    return policy_decide(
        records,
        record_id,
        subject,
        action,
        at,
        revoked_ids=revoked_ids,
        tombstones=tombstones,
    )


def case_producer(setup, *, resolver=None, decider=temporal_decide):
    original, store, _, _, policy, _ = setup
    return CompanyRightsProducer(
        store=store,
        rights_root=original.rights_root,
        checkpoint_root=original.checkpoint_root,
        policy_file=policy,
        policy_sha256=original.policy_sha256,
        source_commit=COMMIT,
        source_bytes=original.source_bytes,
        validate_record=policy_validator,
        decide=decider,
        known_person_ids=original.known_person_ids,
        case_as_of=resolver,
    )


def set_case_time(store, value):
    state = {"id": "ENG-1"}
    if value is not None:
        state["simulated_at"] = value
    with store.connect() as db:
        db.execute("UPDATE engagements SET state=? WHERE id='ENG-1'", (json.dumps(state),))


def future_case(setup):
    original, store, _, _, _, _ = setup
    populated(setup, actions=["read", "count"])
    future = record(actions=["read", "count"])
    future["available_at"] = future["effective_at"] = "2027-08-31T00:00:00+00:00"
    future["grants"][0]["start"] = "2027-08-31T00:00:00+00:00"
    original.put_record(future, expected_revision=2)
    set_case_time(store, "2028-01-01T00:00:00+00:00")
    return {"time": "2028-01-01T00:00:00+00:00"}


def approved_resolver(store, session, approved):
    expected_session = store._key_hash(session["token"])

    def resolve(context):
        if context.session_id != expected_session or context.engagement_id != "ENG-1":
            raise RightsUnavailable("Approved case identity mismatch")
        return approved.get("time")

    return resolve


def test_verified_engagement_case_time_allows_future_record_with_fresh_wall_authority(setup):
    original, store, principal, session, _, _ = setup
    approved = future_case(setup)
    wall = case_producer(setup, resolver=None)
    with pytest.raises(RightsUnavailable):
        wall.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    seen = []

    trusted = approved_resolver(store, session, approved)

    def verified_resolver(context):
        seen.append(context)
        return trusted(context)

    producer = case_producer(setup, resolver=verified_resolver)
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
    assert producer.visible_population(
        session_token=session["token"],
        engagement_id="ENG-1",
        candidates=[{"path": "docs/source.txt", "content": CONTENT}],
        action="count",
        complete=True,
    ) == [{"path": "docs/source.txt", "content": CONTENT}]
    assert producer.case_time(session_token=session["token"], engagement_id="ENG-1") == (
        "2028-01-01T00:00:00+00:00"
    )
    assert seen and all(isinstance(context, VerifiedCaseContext) for context in seen)
    assert all(context.principal_id == principal["id"] for context in seen)
    assert all(context.session_id == store._key_hash(session["token"]) for context in seen)
    assert all(
        context.engagement_id == "ENG-1" and context.person_id == "PERSON-1" for context in seen
    )
    assert original.case_as_of is None


def test_case_time_cannot_refresh_expired_wall_session_or_restored_rights(setup):
    _, store, _, session, _, _ = setup
    approved = future_case(setup)
    producer = case_producer(setup, resolver=approved_resolver(store, session, approved))
    with store.connect() as db:
        db.execute(
            "UPDATE sessions SET expires=? WHERE token_hash=?",
            (time.time() - 1, store._key_hash(session["token"])),
        )
    with pytest.raises(DomainError):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    with store.connect() as db:
        db.execute(
            "UPDATE sessions SET expires=? WHERE token_hash=?",
            (time.time() + 3600, store._key_hash(session["token"])),
        )
    with sqlite3.connect(producer.checkpoint_db) as db:
        db.execute("UPDATE state SET rights_revision=2")
    with pytest.raises(RightsUnavailable, match="restored"):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )


def test_invalid_or_missing_server_case_time_fails_closed(setup):
    _, store, _, session, _, _ = setup
    approved = future_case(setup)
    producer = case_producer(setup, resolver=approved_resolver(store, session, approved))
    for value in ("2028-01-01", "not-an-instant", None):
        approved["time"] = value
        with pytest.raises(RightsUnavailable, match="case clock"):
            producer.authorize_disclosure(
                session_token=session["token"],
                engagement_id="ENG-1",
                path="docs/source.txt",
                content=CONTENT,
                action="read",
            )


def test_case_time_change_during_direct_disclosure_fails_closed(setup):
    _, store, _, session, _, _ = setup
    approved = future_case(setup)
    calls = 0

    def changing_decider(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = temporal_decide(*args, **kwargs)
        if calls == 1:
            approved["time"] = "2026-09-22T00:00:00+00:00"
        return result

    producer = case_producer(
        setup, resolver=approved_resolver(store, session, approved), decider=changing_decider
    )
    with pytest.raises(RightsUnavailable, match="case clock changed"):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id="ENG-1",
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    assert calls == 1


def test_case_time_change_during_complete_population_discards_count(setup, monkeypatch):
    _, store, _, session, _, _ = setup
    approved = future_case(setup)
    producer = case_producer(setup, resolver=approved_resolver(store, session, approved))
    original = producer.authorize_disclosure

    def changing(**kwargs):
        result = original(**kwargs)
        approved["time"] = "2026-09-22T00:00:00+00:00"
        return result

    monkeypatch.setattr(producer, "authorize_disclosure", changing)
    with pytest.raises(RightsUnavailable, match="case clock changed"):
        producer.visible_population(
            session_token=session["token"],
            engagement_id="ENG-1",
            candidates=[{"path": "docs/source.txt", "content": CONTENT}],
            action="count",
            complete=True,
        )


@pytest.mark.parametrize("operation", ["direct", "population", "case_time"])
def test_final_case_callback_cannot_revoke_rights_after_last_check(setup, operation):
    _, store, _, session, _, _ = setup
    approved = future_case(setup)
    calls = 0
    producer = None
    trusted = approved_resolver(store, session, approved)
    revoke_on = {"direct": 2, "population": 4, "case_time": 2}[operation]

    def revoking_resolver(context):
        nonlocal calls
        calls += 1
        if calls == revoke_on:
            producer.set_person_revoked("PERSON-1", revoked=True)
        return trusted(context)

    producer = case_producer(setup, resolver=revoking_resolver)
    with pytest.raises(RightsUnavailable):
        if operation == "direct":
            producer.authorize_disclosure(
                session_token=session["token"],
                engagement_id="ENG-1",
                path="docs/source.txt",
                content=CONTENT,
                action="read",
            )
        elif operation == "population":
            producer.visible_population(
                session_token=session["token"],
                engagement_id="ENG-1",
                candidates=[{"path": "docs/source.txt", "content": CONTENT}],
                action="count",
                complete=True,
            )
        else:
            producer.case_time(session_token=session["token"], engagement_id="ENG-1")
    assert calls >= revoke_on


def test_mutated_candidate_cannot_change_disclosed_population(setup, monkeypatch):
    producer, _, _, session, _, _ = setup
    populated(setup, actions=["count"])
    candidate = {"path": "docs/source.txt", "content": CONTENT}
    original = producer.authorize_disclosure

    def changing(**kwargs):
        result = original(**kwargs)
        candidate["content"] = b"unclassified changed bytes"
        return result

    monkeypatch.setattr(producer, "authorize_disclosure", changing)
    with pytest.raises(RightsUnavailable, match="candidate population changed"):
        producer.visible_population(
            session_token=session["token"],
            engagement_id="ENG-1",
            candidates=[candidate],
            action="count",
            complete=True,
        )


def test_learner_clock_advance_does_not_create_approved_company_case_time(tmp_path):
    engine = Engine(tmp_path / "runtime")
    learner = engine.store.provision("Scenario learner", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Case clock boundary",
        phase="ACTIVE",
        simulated_at="2027-01-03T09:00:00+00:00",
        scope={
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
            "boundaries": ["unit"],
        },
        controls=[{"id": "C1", "owner_ids": ["P1"], "implementation_version": "v1"}],
        people=[{"id": "P1"}],
    )
    created = engine.store.create(learner["id"], state, "create")
    session = engine.store.login(learner["credential"])
    rights_root, checkpoint_root = tmp_path / "rights", tmp_path / "checkpoint"
    rights_root.mkdir(mode=0o700)
    checkpoint_root.mkdir(mode=0o700)
    policy = tmp_path / "policy.json"
    policy.write_text('{"accepted":"test-only"}')
    common = dict(
        store=engine.store,
        rights_root=rights_root,
        checkpoint_root=checkpoint_root,
        policy_file=policy,
        policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
        source_commit=COMMIT,
        source_bytes=lambda path: CONTENT,
        validate_record=policy_validator,
        decide=temporal_decide,
        known_person_ids=frozenset({"PERSON-1"}),
    )
    producer = CompanyRightsProducer(**common)
    producer.bind_person(
        principal_id=learner["id"],
        engagement_id=created["id"],
        person_id="PERSON-1",
        tenant="SH",
        purpose="inspection",
        expected_revision=0,
    )
    future = record(actions=["read"])
    future["available_at"] = future["effective_at"] = "2028-01-05T00:00:00+00:00"
    future["grants"][0]["start"] = "2028-01-05T00:00:00+00:00"
    producer.put_record(future, expected_revision=1)
    advanced = engine.command(
        learner["id"],
        created["id"],
        {
            "command_id": "learner-advance",
            "expected_revision": created["revision"],
            "kind": "clock.advance",
            "payload": {"mode": "TARGET_DATE", "target": "2028-01-10"},
        },
    )
    assert advanced["simulated_at"].startswith("2028-01-10")
    with pytest.raises(RightsUnavailable):
        producer.authorize_disclosure(
            session_token=session["token"],
            engagement_id=created["id"],
            path="docs/source.txt",
            content=CONTENT,
            action="read",
        )
    approved = {}
    verified = CompanyRightsProducer(
        **common, case_as_of=lambda context: approved.get(context.engagement_id)
    )
    with pytest.raises(RightsUnavailable, match="case clock"):
        verified.authorize_disclosure(
            session_token=session["token"],
            engagement_id=created["id"],
            path="docs/source.txt",
            content=CONTENT,
            action="read",
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
