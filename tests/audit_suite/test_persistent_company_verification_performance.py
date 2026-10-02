"""Warm parsing never replaces byte pins or fresh current-row verification."""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Event

import pytest

from enterprise.audit_suite import persistent_company_journey as runtime
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from tests.audit_suite.test_persistent_company_journey import source


@pytest.fixture
def world(tmp_path):
    tmp_path.chmod(0o700)
    accepted = source(tmp_path / "accepted-neutral")
    return runtime.PersistentCompany.initialize(
        accepted,
        tmp_path / "persistent-neutral",
        operator_id="COMPANY-OPERATOR-NEUTRAL",
        engineering_only=True,
    )


def test_warm_baseline_is_immutable_and_only_current_rows_are_read_again(world, monkeypatch):
    baseline, digest, systems, schema = world._verified_baseline()
    key = next(iter(baseline))
    with pytest.raises(TypeError):
        baseline[key] = {}
    with pytest.raises(TypeError):
        baseline[key]["content"] = "00"
    assert digest == runtime.rows_sha(baseline)
    assert isinstance(systems, tuple) and isinstance(systems[0], tuple)
    assert schema
    actual_reads = []
    original = runtime.native_rows

    def observe(path):
        actual_reads.append(path)
        return original(path)

    monkeypatch.setattr(runtime, "native_rows", observe)
    for _ in range(3):
        world.verify()
    assert actual_reads == [world.database] * 3


def _change_original(path):
    # An adversarial author-owned neutral fixture only. Restore the exact trigger
    # to challenge row comparison, rather than rely on a missing-trigger guard.
    with closing(sqlite3.connect(path)) as db:
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET origin=origin || 'changed' WHERE branch='ALPHA'")
        db.execute(trigger)
        db.commit()


def test_warm_baseline_still_hashes_all_bytes_despite_preserved_timestamps(world):
    world.verify()
    before = world.accepted.database.stat()
    _change_original(world.accepted.database)
    os.utime(world.accepted.database, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(ProcedureError, match="Accepted library pin changed"):
        world.verify()


def test_warm_current_rows_are_not_cached_even_with_exact_restored_triggers(world):
    world.verify()
    _change_original(world.database)
    with pytest.raises(ProcedureError, match="Accepted company history was changed"):
        world.verify()


def test_verified_source_operation_checks_entry_exit_without_cross_call_cache(world, monkeypatch):
    calls = []
    original = world.verify

    def observed():
        calls.append(True)
        return original()

    monkeypatch.setattr(world, "verify", observed)
    for _ in range(2):
        with world.verified_sources():
            for _ in range(10):
                world.require_runtime()
    assert len(calls) == 4
    world.require_runtime()
    assert len(calls) == 5


def test_verified_source_operation_rejects_changed_original_at_exit(world):
    with pytest.raises(ProcedureError, match="Accepted company history was changed"):
        with world.verified_sources():
            _change_original(world.database)
    assert not world._local.verified_sources
    with pytest.raises(ProcedureError):
        world.require_runtime()


def test_verified_source_operation_rejects_changed_accepted_bytes_at_exit(world):
    before = world.accepted.database.stat()
    with pytest.raises(ProcedureError, match="Accepted library pin changed"):
        with world.verified_sources():
            _change_original(world.accepted.database)
            os.utime(world.accepted.database, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert not world._local.verified_sources


def test_verified_source_operation_rejects_business_append_and_nested_lease(world):
    with world.verified_sources():
        with pytest.raises(ProcedureError, match="Business history append"):
            world.append(world.operator, {}, b"invalid")
        with pytest.raises(ProcedureError, match="Distinct verified source operation"):
            with world.verified_sources():
                pass
    world.require_runtime()


def test_verified_source_operation_failure_restores_fresh_checks(world, monkeypatch):
    calls = []
    original = world.verify

    def observed():
        calls.append(True)
        return original()

    monkeypatch.setattr(world, "verify", observed)
    with pytest.raises(RuntimeError, match="body failure"):
        with world.verified_sources():
            raise RuntimeError("body failure")
    assert not world._local.verified_sources and len(calls) == 2
    world.require_runtime()
    assert len(calls) == 3


def test_verified_source_operation_still_checks_current_revocation_and_clock(world):
    key = ("NEUTRAL-COMPANY", "ALPHA", "operations.events")
    with world.verified_sources():
        world.store.grant("NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, active=True)
        row = world.store.read_version(
            "NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, "event-one",
            version=1, as_of="2027-01-03T00:00:00Z",
        )
        assert row["version"] == 1
        with pytest.raises(CompanyStoreError):
            world.store.read_version(
                "NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, "event-one",
                version=1, as_of="2027-01-01T00:00:00Z",
            )
        world.store.grant("NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, active=False)
        with pytest.raises(CompanyStoreError):
            world.store.read_version(
                "NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, "event-one",
                version=1, as_of="2027-01-03T00:00:00Z",
            )


def test_verified_source_operation_blocks_other_managed_thread_until_fresh_exit(world):
    entered, finished = Event(), Event()

    def grant():
        entered.set()
        world.store.grant(
            "OTHER-NEUTRAL-AUDITOR", "OTHER-NEUTRAL-ENGAGEMENT",
            "NEUTRAL-COMPANY", "ALPHA", "operations.events", active=True,
        )
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with world.verified_sources():
            future = pool.submit(grant)
            assert entered.wait(5)
            assert not finished.wait(0.05)
        future.result(timeout=5)
    assert finished.is_set()
