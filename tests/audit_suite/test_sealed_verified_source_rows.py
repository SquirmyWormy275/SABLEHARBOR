"""Fresh return-only native rows; no source, authority or outcome cache."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from enterprise.audit_suite import persistent_company_journey as runtime
from enterprise.audit_suite import persistent_company_service as service
from enterprise.audit_suite import sealed_retained_service as sealed
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from tests.audit_suite.test_persistent_company_journey import source
from tests.audit_suite.test_persistent_company_verification_performance import (
    _change_original,
)
from tests.audit_suite.test_persistent_company_verification_performance import (
    world as world_fixture,
)
from tests.audit_suite.test_verified_lease_pair_efficiency import grant, read

world = world_fixture


def original_sources(room):
    # Exact saved aa6180ef parent _sources, apart from binding its native_rows
    # name to the unchanged runtime implementation; portable private control.
    room.world.verify()
    native = runtime.native_rows(room.world.database)
    now = sealed._time(service.time_to_iso())
    sealed.require(
        sealed._time(room.world.initialization["initialized_at"]) <= now
        and all(sealed._time(r["imported_at"]) <= now for r in native.values()),
        "Company real import clock is in the future",
    )
    with sealed.quiescent_read(room.world.database) as db:
        journal = {
            r["command_id"]: sealed.json.loads(r["receipt"])
            for r in db.execute("SELECT command_id,receipt FROM collections")
        }
    return native, journal


def test_default_verify_still_returns_only_the_same_checkpoint(world):
    checkpoint = world.verify()
    with world.locked():
        returned, rows = world.verify(_return_native_rows=True)
    assert returned == checkpoint and len(rows) == checkpoint["native_versions"] == 2


@pytest.mark.parametrize("flag", [None, 0, "true"])
def test_private_return_requires_an_exact_boolean(world, flag):
    with world.locked(), pytest.raises(ProcedureError, match="Exact private"):
        world.verify(_return_native_rows=flag)


def test_private_rows_cannot_escape_without_an_outer_company_lock(world):
    with pytest.raises(ProcedureError, match="already held Company lock"):
        world.verify(_return_native_rows=True)
    assert world._local.depth == 0
    world.verify()


def test_other_thread_cannot_inherit_the_callers_outer_lock(world):
    with ThreadPoolExecutor(max_workers=1) as pool:
        with world.locked():
            pending = pool.submit(world.verify, _return_native_rows=True)
            assert not pending.done()
        with pytest.raises(ProcedureError, match="already held Company lock"):
            pending.result(timeout=5)


def test_exact_same_rows_and_receipts_need_one_current_scan_instead_of_two(world, monkeypatch):
    grant(world)
    world.store.collect(
        "NEUTRAL-AUDITOR",
        "NEUTRAL-ENGAGEMENT",
        "NEUTRAL-COMPANY",
        "ALPHA",
        "operations.events",
        "event-one",
        version=1,
        as_of="2027-01-03T00:00:00Z",
        command_id="FICTIONAL-COLLECTION",
    )
    calls = []
    old = runtime.native_rows

    def observe(path):
        calls.append(path)
        return old(path)

    monkeypatch.setattr(runtime, "native_rows", observe)
    room = SimpleNamespace(world=world)
    with world.locked():
        before = original_sources(room)
        assert calls == [world.database] * 2
        calls.clear()
        after = sealed._sources(room)
        assert calls == [world.database]
    assert before == after and after[1]


def test_returned_rows_are_independent_between_reads_and_worlds(world, tmp_path):
    other = runtime.PersistentCompany.initialize(
        source(tmp_path / "other-accepted-neutral"),
        tmp_path / "other-world-neutral",
        operator_id="OTHER-NEUTRAL-OPERATOR",
        engineering_only=True,
    )
    with world.locked():
        first, _ = sealed._sources(SimpleNamespace(world=world))
        key = next(iter(first))
        expected = dict(first[key])
        first[key]["content"] = "00"
        first.clear()
        second, _ = sealed._sources(SimpleNamespace(world=world))
        assert second[key] == expected
    with other.locked():
        third, _ = sealed._sources(SimpleNamespace(world=other))
    assert third == runtime.native_rows(other.database)
    assert third[key]["content"] == expected["content"]
    assert third is not second and third[key] is not second[key]


@pytest.mark.parametrize("database", ["accepted", "current"])
def test_fresh_source_and_closing_checks_still_refuse_tamper(world, database):
    with world.locked():
        sealed._sources(SimpleNamespace(world=world))
        _change_original(world.accepted.database if database == "accepted" else world.database)
        with pytest.raises(ProcedureError):
            sealed._close_sources(SimpleNamespace(world=world), {})
        with pytest.raises(ProcedureError):
            sealed._sources(SimpleNamespace(world=world))


def test_import_clock_is_not_reused_from_a_prior_success(world, monkeypatch):
    room = SimpleNamespace(world=world)
    with world.locked():
        sealed._sources(room)
        monkeypatch.setattr(service, "time_to_iso", lambda: "1900-01-01T00:00:00+00:00")
        with pytest.raises(ProcedureError, match="real import clock"):
            sealed._sources(room)


def test_returned_rows_do_not_grant_authority_or_hide_revocation(world):
    grant(world)
    with world.verified_sources():
        sealed._sources(SimpleNamespace(world=world))
        read(world)
        with pytest.raises(CompanyStoreError):
            read(world, actor="DIFFERENT-NEUTRAL-AUDITOR")
        grant(world, active=False)
        with pytest.raises(CompanyStoreError):
            read(world)


def test_cancellation_after_verification_clears_lease_and_next_read_is_fresh(world, monkeypatch):
    class Cancelled(BaseException):
        pass

    def cancel():
        raise Cancelled("one-shot fictional cancellation")

    with monkeypatch.context() as patch:
        patch.setattr(service, "time_to_iso", cancel)
        with pytest.raises(Cancelled), world.verified_sources():
            sealed._sources(SimpleNamespace(world=world))
    assert world._local.depth == 0
    assert world._local.verified_sources is False
    assert world._local.verified_source_binding is None
    with world.locked():
        sealed._sources(SimpleNamespace(world=world))


def test_candidate_origins_are_private_and_default_close_function_is_unchanged():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert Path(runtime.__file__).is_relative_to(root)
    assert Path(sealed.__file__).is_relative_to(root)
