import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from enterprise.audit_suite.store import DomainError, Store


@pytest.fixture
def context(tmp_path):
    root = tmp_path / "private"
    store = Store(root)
    a = store.provision("Learner", ["learner"])
    b = store.provision("Other learner", ["learner"])
    state = store.create(a["id"], {"title": "Training", "simulated_at": "2027-01-01"}, "create")
    return store, a, b, state


def edit(command_id="change", revision=0):
    return {
        "command_id": command_id,
        "expected_revision": revision,
        "kind": "note.create",
        "payload": {"text": "Observed a document"},
    }


def reduce(state, command, actor):
    return {**state, "note": command["payload"]["text"], "note_actor": actor}


def test_connect_context_commits_or_rolls_back_and_always_closes(tmp_path):
    store = Store(tmp_path / "private")
    with store.connect() as committed:
        committed.execute("CREATE TABLE lifetime_probe (value INTEGER)")
        committed.execute("INSERT INTO lifetime_probe VALUES (1)")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        committed.execute("SELECT 1")

    with pytest.raises(RuntimeError, match="rollback"):
        with store.connect() as rolled_back:
            rolled_back.execute("INSERT INTO lifetime_probe VALUES (2)")
            raise RuntimeError("rollback")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        rolled_back.execute("SELECT 1")

    with store.connect() as check:
        assert [row["value"] for row in check.execute("SELECT value FROM lifetime_probe")] == [1]


def test_connect_context_releases_wal_and_shm_on_final_close(tmp_path):
    store = Store(tmp_path / "private")
    wal = store.db_path.with_name(store.db_path.name + "-wal")
    shm = store.db_path.with_name(store.db_path.name + "-shm")

    with store.connect() as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        db.execute("CREATE TABLE wal_probe (value INTEGER)")
        db.execute("INSERT INTO wal_probe VALUES (1)")
        assert wal.is_file() and shm.is_file()

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        db.execute("SELECT 1")
    assert not wal.exists() and not shm.exists()
    with store.connect() as check:
        assert check.execute("SELECT value FROM wal_probe").fetchone()[0] == 1


def test_isolation_revocation_and_csrf(context):
    store, a, b, state = context
    assert store.listing(b["id"]) == []
    with pytest.raises(DomainError, match="unavailable"):
        store.get(b["id"], state["id"])
    login = store.login(a["credential"])
    with pytest.raises(DomainError, match="request token"):
        store.session(login["token"], csrf="wrong", mutation=True)
    assert store.session(login["token"], csrf=login["csrf"], mutation=True)["id"] == a["id"]
    store.revoke(a["id"])
    with pytest.raises(DomainError, match="revoked"):
        store.session(login["token"])
    with pytest.raises(DomainError, match="revoked"):
        store.get(a["id"], state["id"])


def test_retries_revisions_and_history(context):
    store, a, b, state = context
    first = store.command(a["id"], state["id"], edit(), reduce, permissions={"learn"})
    retry = store.command(a["id"], state["id"], edit(), reduce, permissions={"learn"})
    assert retry == first
    with pytest.raises(DomainError, match="changed"):
        store.command(a["id"], state["id"], edit("another"), reduce, permissions={"learn"})
    altered = edit()
    altered["payload"]["text"] = "different"
    with pytest.raises(DomainError, match="already used"):
        store.command(a["id"], state["id"], altered, reduce, permissions={"learn"})
    assert len(store.history(a["id"], state["id"])) == 2
    with store.connect() as db, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        db.execute("DELETE FROM events")


def test_concurrent_writers_only_one_wins(context):
    store, a, _, state = context

    def submit(i):
        try:
            return store.command(a["id"], state["id"], edit(str(i)), reduce, permissions={"learn"})[
                "revision"
            ]
        except DomainError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert sorted(results) == [1, 409]


def test_real_clock_is_independent_of_simulation(context):
    store, a, _, state = context
    before = time.time()

    def advance(s, c, actor):
        return {**s, "simulated_at": "2099-12-31"}

    store.command(a["id"], state["id"], edit(), advance, permissions={"learn"})
    history = store.history(a["id"], state["id"])
    assert before <= history[-1]["recorded_at"] <= time.time()
    with store.connect() as db:
        db.execute("UPDATE principals SET expires=? WHERE id=?", (before - 1, a["id"]))
    with pytest.raises(DomainError, match="expired"):
        store.get(a["id"], state["id"])


def test_actor_injection_and_atomic_reducer_failure(context):
    store, a, b, state = context
    command = {**edit(), "actor": b["id"]}
    with pytest.raises(DomainError, match="only ID"):
        store.command(a["id"], state["id"], command, reduce, permissions={"learn"})

    def fail(s, c, actor):
        s["title"] = "partial edit"
        raise DomainError("deliberate failure")

    with pytest.raises(DomainError, match="deliberate"):
        store.command(a["id"], state["id"], edit(), fail, permissions={"learn"})
    assert store.get(a["id"], state["id"]) == state


def test_same_create_id_different_data_rejected(context):
    store, a, _, state = context
    assert (
        store.create(a["id"], {"title": "Training", "simulated_at": "2027-01-01"}, "create")
        == state
    )
    with pytest.raises(DomainError, match="different input"):
        store.create(a["id"], {"title": "Different"}, "create")


def test_preflight_replays_exact_receipt_but_rechecks_current_authority(context):
    store, a, _, state = context
    kwargs = {"permissions": {"learn"}}
    assert store.preflight(a["id"], state["id"], edit(), **kwargs) is None
    first = store.command(a["id"], state["id"], edit(), reduce, **kwargs)
    store.command(a["id"], state["id"], edit("second", 1), reduce, **kwargs)
    assert store.preflight(a["id"], state["id"], edit(), **kwargs) == first
    changed = edit()
    changed["payload"]["text"] = "changed"
    with pytest.raises(DomainError, match="already used"):
        store.preflight(a["id"], state["id"], changed, **kwargs)
    store.grant(state["id"], a["id"], "review")
    with pytest.raises(DomainError, match="unavailable"):
        store.preflight(a["id"], state["id"], edit(), **kwargs)
    store.revoke(a["id"])
    with pytest.raises(DomainError, match="revoked"):
        store.preflight(a["id"], state["id"], edit(), permissions={"review"})


def test_preflight_does_not_reserve_revision_or_bypass_final_authorization(context):
    store, a, _, state = context
    kwargs = {"permissions": {"learn"}}
    assert store.preflight(a["id"], state["id"], edit(), **kwargs) is None
    store.command(a["id"], state["id"], edit("racer"), reduce, **kwargs)
    with pytest.raises(DomainError, match="changed"):
        store.command(a["id"], state["id"], edit(), reduce, **kwargs)


def test_instructor_creation_has_explicit_instruct_membership(context):
    store, _, _, _ = context
    instructor = store.provision("Instructor", ["instructor"])
    state = store.create(instructor["id"], {"title": "Exercise"}, "create")
    assert store.membership(instructor["id"], state["id"]) == "instruct"
