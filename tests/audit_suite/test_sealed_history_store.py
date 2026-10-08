"""Actual ordinary Store commands across an unchanged prefix and new tail."""

import hashlib
import time
from pathlib import Path

import pytest

from enterprise.audit_suite.recovery import _history
from enterprise.audit_suite.sealed_history_store import SealedHistoryStore, prepare_tail
from enterprise.audit_suite.store import DomainError, Store


@pytest.mark.parametrize("case", ["unsigned", "foreign", "future", "credential", "Boolean"])
def test_every_issued_history_record_validates_before_initial_physical_pin_waiver(pair, case):
    original, sealed, operator, _, _, _, before = pair
    token = "f" * 64
    now = time.time()
    with sealed.connect() as db:
        sealed.verify_projection(db)
        credential = db.execute(
            "SELECT token_hash FROM principals WHERE id=?", (operator["id"],)
        ).fetchone()[0]
    value = {
        "token_hash": token,
        "principal": operator["id"],
        "csrf": "owned-neutral-csrf",
        "expires": now + 3600,
        "authenticated_at": now,
        "prefix_sha256": sealed.prefix["sha256"],
        "engagement": sealed.prefix["engagement"],
        "credential_token_hash": credential,
    }
    if case == "unsigned":
        body, signature = "{}", "00"
    else:
        if case == "foreign":
            value["principal"] = "UNREGISTERED-PRINCIPAL"
        elif case == "future":
            value["authenticated_at"] = now + 86400
            value["expires"] = value["authenticated_at"] + 3600
        elif case == "credential":
            value["credential_token_hash"] = "0" * 64
        elif case == "Boolean":
            value["authenticated_at"] = True
            value["expires"] = 3601
        body, signature = sealed.session_authority.issue(value)
    with sealed.connect() as db:
        db.execute("INSERT INTO issued_sessions VALUES (?,?,?)", (token, body, signature))
    reopened = SealedHistoryStore(original.root, sealed.manifest_path, sealed.manifest_sha256)
    with reopened.connect() as db, pytest.raises(DomainError):
        reopened.verify_projection(db)
    assert sha(original.db_path) == before


def test_loggedout_rotated_historical_issuance_validates_own_old_credential_edition(pair):
    original, sealed, operator, _, _, _, before = pair
    issued = sealed.login(operator["credential"])
    sealed.logout(issued["token"])
    rotated = sealed.rotate_credential(operator["id"], lifetime=3600)
    new_session = sealed.login(rotated["credential"])
    sealed.logout(new_session["token"])
    reopened = SealedHistoryStore(
        original.root,
        sealed.manifest_path,
        sealed.manifest_sha256,
        authority_head=sealed.authority_head,
        session_revocations=sealed.session_authority.known_revocations,
    )
    with reopened.connect() as db:
        reopened.verify_projection(db)
        assert db.execute("SELECT COUNT(*) FROM issued_sessions").fetchone()[0] == 2
        assert not db.execute("SELECT * FROM sessions").fetchone()
    assert sha(original.db_path) == before


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def append(store, actor, eid, command_id, text):
    current = store.get(actor, eid)
    return store.command(
        actor,
        eid,
        {
            "command_id": command_id,
            "expected_revision": current["revision"],
            "kind": "neutral.note",
            "payload": {"text": text},
        },
        lambda state, command, person: state | {"note": command["payload"]["text"]},
        permissions={"instruct"},
    )


@pytest.fixture
def pair(tmp_path):
    tmp_path.chmod(0o700)
    original = Store(tmp_path / "original")
    operator = original.provision("Neutral original operator", ["instructor"])
    learner = original.provision("Neutral original learner", ["learner"])
    state = original.create(
        operator["id"],
        {
            "engineering_neutral_only": True,
            "mode": "CLEAN",
            "tasks": [],
            "artifacts": [],
            "scope": {"soc2_categories": ["Security"]},
            "simulated_at": "2027-12-31T09:00:00Z",
        },
        "neutral-birth",
    )
    original.grant(state["id"], learner["id"], "learn")
    append(original, operator["id"], state["id"], "prefix-note", "literal prefix note")
    session = original.login(operator["credential"])
    before = sha(original.db_path)
    choice = prepare_tail(original, operator["id"], state["id"], tmp_path / "new-tail")
    sealed = SealedHistoryStore(original.root, choice["path"], choice["sha256"])
    assert sha(original.db_path) == before
    return original, sealed, operator, learner, state["id"], session, before


def test_same_identity_append_keeps_prefix_bytes_and_complete_history(pair):
    original, sealed, operator, learner, eid, session, before = pair
    assert sealed.get(learner["id"], eid)["revision"] == 1
    state = append(sealed, operator["id"], eid, "tail-note", "genuine new tail note")
    assert state["id"] == eid and state["revision"] == 2
    with sealed.connect() as db:
        rows = list(db.execute("SELECT revision,previous_hash,hash FROM events ORDER BY revision"))
        assert [r["revision"] for r in rows] == [0, 1, 2]
        assert rows[2]["previous_hash"] == rows[1]["hash"]
        assert db.execute("SELECT COUNT(*) FROM main.event_tail").fetchone()[0] == 1
        assert _history(db)[eid]["events"] == 3
    assert sha(original.db_path) == before
    assert sealed.session(session["token"])["id"] == operator["id"]


def test_original_command_replay_is_exact_and_does_not_append(pair):
    original, sealed, operator, _, eid, _, before = pair
    current = sealed.get(operator["id"], eid)
    command = {
        "command_id": "prefix-note",
        "expected_revision": 0,
        "kind": "neutral.note",
        "payload": {"text": "literal prefix note"},
    }
    replay = sealed.command(
        operator["id"],
        eid,
        command,
        lambda *a: pytest.fail("Replay must not run reducer"),
        permissions={"instruct"},
    )
    assert replay == current
    with sealed.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM main.event_tail").fetchone()[0] == 0
    assert sha(original.db_path) == before


def test_ordinary_rotation_invalidates_old_key_and_all_sessions(pair):
    original, sealed, operator, _, eid, session, before = pair
    old = sealed.get(operator["id"], eid)
    new = sealed.rotate_credential(operator["id"], lifetime=3600)
    assert new["id"] == operator["id"]
    assert sealed.authenticate(new["credential"])["roles"] == ["instructor"]
    assert sealed.get(operator["id"], eid) == old
    with pytest.raises(DomainError):
        sealed.authenticate(operator["credential"])
    with pytest.raises(DomainError):
        sealed.session(session["token"])
    fresh = sealed.login(new["credential"])
    assert sealed.session(fresh["token"])["id"] == operator["id"]
    assert sha(original.db_path) == before


@pytest.mark.parametrize("lifetime", [True, 0, 59, 7 * 86400 + 1])
def test_rotation_lifetime_is_strictly_bounded(pair, lifetime):
    _, sealed, operator, _, _, _, _ = pair
    with pytest.raises(DomainError, match="lifetime"):
        sealed.rotate_credential(operator["id"], lifetime=lifetime)


def test_revoked_identity_cannot_be_reactivated(pair):
    _, sealed, operator, _, _, _, _ = pair
    sealed.revoke(operator["id"])
    with pytest.raises(DomainError, match="non-revoked"):
        sealed.rotate_credential(operator["id"])


def test_arbitrary_expiry_edit_has_no_rotation_authority(pair):
    _, sealed, operator, _, _, _, _ = pair
    with sealed.connect() as db:
        db.execute("UPDATE principals SET expires=expires+10000 WHERE id=?", (operator["id"],))
    with pytest.raises(DomainError, match="rotation history"):
        sealed.authenticate(operator["credential"])


def test_changed_prefix_refuses_even_if_mtime_restored(pair):
    original, sealed, operator, _, eid, _, _ = pair
    import os

    old = original.db_path.stat()
    with original.db_path.open("r+b") as stream:
        stream.seek(100)
        byte = stream.read(1)
        stream.seek(100)
        stream.write(bytes([byte[0] ^ 1]))
    os.utime(original.db_path, ns=(old.st_atime_ns, old.st_mtime_ns))
    with pytest.raises(DomainError, match="prefix"):
        sealed.get(operator["id"], eid)


def test_no_new_engagement_or_principal_and_no_overwrite(pair, tmp_path):
    original, sealed, operator, _, eid, _, _ = pair
    with pytest.raises(DomainError, match="new engagement"):
        sealed.create(operator["id"], {}, "new-birth")
    with pytest.raises(DomainError, match="identities"):
        sealed.provision("New person", ["instructor"])
    with pytest.raises(FileExistsError):
        prepare_tail(original, operator["id"], eid, tmp_path / "new-tail")


def test_repaired_deleted_old_session_does_not_become_a_new_login(pair):
    import time

    _, sealed, operator, _, _, session, _ = pair
    with sealed.connect() as db:
        old = dict(
            db.execute(
                "SELECT * FROM sessions WHERE token_hash=?", (sealed._key_hash(session["token"]),)
            ).fetchone()
        )
    sealed.rotate_credential(operator["id"], lifetime=3600)
    old.update(authenticated_at=time.time(), expires=time.time() + 3600)
    old["expires"] = old["authenticated_at"] + 3600
    with sealed.connect() as db:
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", tuple(old.values()))
    with pytest.raises(DomainError, match="Original session"):
        sealed.session(session["token"])


def test_repaired_new_session_issuance_cannot_restore_old_rotated_credential(pair):
    import time

    _, sealed, operator, _, _, _, _ = pair
    session = sealed.login(operator["credential"])
    with sealed.connect() as db:
        old = dict(
            db.execute(
                "SELECT * FROM sessions WHERE token_hash=?", (sealed._key_hash(session["token"]),)
            ).fetchone()
        )
    sealed.rotate_credential(operator["id"], lifetime=3600)
    old["authenticated_at"] = time.time()
    old["expires"] = old["authenticated_at"] + 3600
    with sealed.connect() as db:
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", tuple(old.values()))
    with pytest.raises(DomainError, match="Signed login issuance"):
        sealed.session(session["token"])


def test_resealed_revoked_flag_has_no_reactivation_authority(pair):
    _, sealed, operator, _, _, _, _ = pair
    sealed.revoke(operator["id"])
    with sealed.connect() as db:
        db.execute("UPDATE principals SET revoked=0 WHERE id=?", (operator["id"],))
    with pytest.raises(DomainError, match="signed rotation history"):
        sealed.authenticate(operator["credential"])


def test_logout_tombstone_refuses_exact_signed_session_restoration_and_reopen(pair):
    _, sealed, operator, _, _, _, _ = pair
    session = sealed.login(operator["credential"])
    with sealed.connect() as db:
        old = tuple(
            db.execute(
                "SELECT * FROM sessions WHERE token_hash=?", (sealed._key_hash(session["token"]),)
            ).fetchone()
        )
    sealed.logout(session["token"])
    with sealed.connect() as db:
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", old)
    with pytest.raises(DomainError, match="Signed logout"):
        sealed.session(session["token"])
    with pytest.raises(DomainError, match="unknown inventory"):
        SealedHistoryStore(sealed.root, sealed.manifest_path, sealed.manifest_sha256)
    reopened = SealedHistoryStore(
        sealed.root,
        sealed.manifest_path,
        sealed.manifest_sha256,
        session_revocations=sealed.session_authority.known_revocations,
    )
    with pytest.raises(DomainError, match="Signed logout"):
        reopened.session(session["token"])


def test_removed_known_logout_tombstone_refuses_after_startup(pair):
    _, sealed, operator, _, _, _, _ = pair
    session = sealed.login(operator["credential"])
    sealed.logout(session["token"])
    member = sealed.session_authority.revocations / (sealed._key_hash(session["token"]) + ".json")
    member.unlink()
    with pytest.raises(DomainError, match="revocation removed"):
        sealed.authenticate(operator["credential"])


def test_membership_cannot_promote_original_learner_role(pair):
    _, sealed, _, learner, eid, _, _ = pair
    with pytest.raises(DomainError, match="original role"):
        sealed.grant(eid, learner["id"], "instruct")


def test_normal_login_logout_reopen_with_explicit_inventory_keeps_original_sessions(pair):
    original, sealed, operator, _, _, prefix_session, before = pair
    with sealed.connect() as db:
        initial = [tuple(row) for row in db.execute("SELECT * FROM sessions ORDER BY 1")]
        sealed.verify_projection(db)
    session = sealed.login(operator["credential"])
    sealed.logout(session["token"])
    with sealed.connect() as db:
        assert [tuple(row) for row in db.execute("SELECT * FROM sessions ORDER BY 1")] == initial
        assert db.execute("SELECT COUNT(*) FROM issued_sessions").fetchone()[0] == 1
    reopened = SealedHistoryStore(
        sealed.root,
        sealed.manifest_path,
        sealed.manifest_sha256,
        session_revocations=sealed.session_authority.known_revocations,
    )
    with reopened.connect() as db:
        reopened.verify_projection(db)
    assert reopened.session(prefix_session["token"])["id"] == operator["id"]
    with pytest.raises(DomainError):
        reopened.session(session["token"])
    assert sha(original.db_path) == before


def test_session_inventory_rejects_list_of_pairs_instead_of_exact_mapping(pair):
    _, sealed, _, _, _, _, _ = pair
    with pytest.raises(DomainError, match="exact mapping"):
        SealedHistoryStore(
            sealed.root, sealed.manifest_path, sealed.manifest_sha256, session_revocations=[]
        )


def test_changed_known_logout_tombstone_refuses_after_startup(pair):
    _, sealed, operator, _, _, _, _ = pair
    session = sealed.login(operator["credential"])
    sealed.logout(session["token"])
    member = sealed.session_authority.revocations / (sealed._key_hash(session["token"]) + ".json")
    member.write_bytes(member.read_bytes() + b" ")
    with pytest.raises(DomainError, match="revocation changed"):
        sealed.authenticate(operator["credential"])


def test_logout_interruption_after_tombstone_keeps_denial_despite_database_rollback(
    pair, monkeypatch
):
    _, sealed, operator, _, _, _, _ = pair
    session = sealed.login(operator["credential"])
    logout = sealed.session_authority.logout

    def interrupted(*args):
        logout(*args)
        raise RuntimeError("Owned neutral simulated database-commit interruption")

    monkeypatch.setattr(sealed.session_authority, "logout", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        sealed.logout(session["token"])
    with sealed.connect() as db:
        assert (
            db.execute(
                "SELECT 1 FROM sessions WHERE token_hash=?", (sealed._key_hash(session["token"]),)
            ).fetchone()
            is not None
        )
    with pytest.raises(DomainError, match="Signed logout"):
        sealed.session(session["token"])
    reopened = SealedHistoryStore(
        sealed.root,
        sealed.manifest_path,
        sealed.manifest_sha256,
        session_revocations=sealed.session_authority.known_revocations,
    )
    with pytest.raises(DomainError, match="Signed logout"):
        reopened.session(session["token"])


def test_history_layout_fallback_then_supported_locations_rebuilds_freshly(pair, monkeypatch):
    import os

    from enterprise.audit_suite import history_inspection as history
    from enterprise.audit_suite.history_locators import UnsupportedLayout

    original, _, operator, _, eid, _, _ = pair
    prepare = history.prepare_locations

    def unavailable(*args):
        raise UnsupportedLayout("Owned neutral initial unsupported layout")

    with original.connect() as db:
        current = db.execute("SELECT revision,state FROM engagements WHERE id=?", (eid,)).fetchone()
        fd = os.open(original.db_path, os.O_RDONLY)
        try:
            monkeypatch.setattr(history, "prepare_locations", unavailable)
            first, previous = history._scan(db, eid, current, {0, current["revision"]}, fd)
            assert previous["locations"] is None
            monkeypatch.setattr(history, "prepare_locations", prepare)
            second, rebuilt = history._scan(
                db, eid, current, {0, current["revision"]}, fd, previous_integrity=previous
            )
            assert second == first
            assert rebuilt["locations"] is not None
        finally:
            os.close(fd)
