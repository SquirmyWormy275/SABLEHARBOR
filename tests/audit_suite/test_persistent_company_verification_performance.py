"""Warm parsing never replaces byte pins or fresh current-row verification."""

import ast
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
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
            "NEUTRAL-AUDITOR",
            "NEUTRAL-ENGAGEMENT",
            *key,
            "event-one",
            version=1,
            as_of="2027-01-03T00:00:00Z",
        )
        assert row["version"] == 1
        with pytest.raises(CompanyStoreError):
            world.store.read_version(
                "NEUTRAL-AUDITOR",
                "NEUTRAL-ENGAGEMENT",
                *key,
                "event-one",
                version=1,
                as_of="2027-01-01T00:00:00Z",
            )
        world.store.grant("NEUTRAL-AUDITOR", "NEUTRAL-ENGAGEMENT", *key, active=False)
        with pytest.raises(CompanyStoreError):
            world.store.read_version(
                "NEUTRAL-AUDITOR",
                "NEUTRAL-ENGAGEMENT",
                *key,
                "event-one",
                version=1,
                as_of="2027-01-03T00:00:00Z",
            )


def test_verified_source_operation_blocks_other_managed_thread_until_fresh_exit(world):
    entered, finished = Event(), Event()

    def grant():
        entered.set()
        world.store.grant(
            "OTHER-NEUTRAL-AUDITOR",
            "OTHER-NEUTRAL-ENGAGEMENT",
            "NEUTRAL-COMPANY",
            "ALPHA",
            "operations.events",
            active=True,
        )
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with world.verified_sources():
            future = pool.submit(grant)
            assert entered.wait(5)
            assert not finished.wait(0.05)
        future.result(timeout=5)
    assert finished.is_set()


# Deterministic one-shot TLS publication/cleanup cancellation boundaries.


def method_ast():
    tree = ast.parse(Path(runtime.__file__).read_text())
    cls = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PersistentCompany"
    )
    return next(
        n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "verified_sources"
    )


def flag_assignment(node, value):
    return (
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and node.value.value is value
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Attribute)
        and node.targets[0].attr == "verified_sources"
    )


def publication_line(boundary):
    method = method_ast()
    for node in ast.walk(method):
        if not hasattr(node, "body") or not isinstance(node.body, list):
            continue
        for index, member in enumerate(node.body):
            if flag_assignment(member, True):
                return (
                    member.lineno if boundary == "token_published" else node.body[index + 1].lineno
                )
    raise AssertionError("Actual entry publication boundary not found")


def interrupt_at(world, line, failure):
    code = runtime.PersistentCompany.verified_sources.__wrapped__.__code__
    seen = []

    def trace(frame, event, arg):
        if frame.f_code is code and event == "line" and frame.f_lineno == line:
            seen.append(
                (
                    getattr(world._local, "verified_sources", False),
                    getattr(world._local, "verified_source_binding", None),
                    getattr(world._local, "depth", 0),
                )
            )
            raise failure
        return trace

    return trace, seen


@pytest.mark.parametrize("boundary", ["token_published", "flag_published"])
def test_entry_publication_base_exception_clears_real_TLS_and_reverifies(
    world,
    monkeypatch,
    boundary,
):
    calls = []
    verify = world.verify

    def observed():
        calls.append(True)
        return verify()

    monkeypatch.setattr(world, "verify", observed)
    failure = KeyboardInterrupt("neutral entry publication cancellation")
    trace, seen = interrupt_at(world, publication_line(boundary), failure)
    prior = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            with world.verified_sources():
                raise AssertionError("Cancelled entry must not yield its body")
    finally:
        sys.settrace(prior)
    assert caught.value is failure
    assert len(seen) == 1 and seen[0][1] is not None and seen[0][2] > 0
    assert seen[0][0] is (boundary == "flag_published")
    assert not getattr(world._local, "verified_sources", False)
    assert getattr(world._local, "verified_source_binding", None) is None
    assert getattr(world._local, "depth", 0) == 0
    assert len(calls) == 2  # Actual opening plus full closing verification.
    world.require_runtime()
    assert len(calls) == 3  # Cancellation cannot enable later deferred checks.
    with world.verified_sources():
        world.require_runtime()
    assert len(calls) == 5


def test_exit_reset_interruption_clears_real_TLS_and_reverifies(world, monkeypatch):
    """Separate diagnostic: cancellation before the first closing reset."""
    resets = [n.lineno for n in ast.walk(method_ast()) if flag_assignment(n, False)]
    if not resets:
        resets = [
            n.lineno
            for n in ast.walk(method_ast())
            if isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and n.value.func.attr == "update"
            and any(
                k.arg == "verified_sources"
                and isinstance(k.value, ast.Constant)
                and k.value.value is False
                for k in n.value.keywords
            )
        ]
    assert len(resets) == 1
    line = resets[0]
    calls = []
    verify = world.verify

    def observed():
        calls.append(True)
        return verify()

    monkeypatch.setattr(world, "verify", observed)
    failure = KeyboardInterrupt("neutral closing reset cancellation")
    trace, seen = interrupt_at(world, line, failure)
    prior = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            with world.verified_sources():
                world.require_runtime()
    finally:
        sys.settrace(prior)
    assert caught.value is failure and len(seen) == 1
    assert seen[0][0] is True and seen[0][1] is not None
    assert not getattr(world._local, "verified_sources", False)
    assert getattr(world._local, "verified_source_binding", None) is None
    assert len(calls) == 2
    assert getattr(world._local, "depth", 0) == 0
    closed_fd = world._local.fd
    import os

    with pytest.raises(OSError):
        os.fstat(closed_fd)
    world.require_runtime()
    assert len(calls) == 3
    with world.verified_sources():
        world.require_runtime()
    assert len(calls) == 5
    # Repeat one independent fault while the lease begins inside an existing
    # outer lock. A cancelled nested lease must end before the caller continues.
    with world.locked():
        trace, seen = interrupt_at(world, line, failure)
        sys.settrace(trace)
        try:
            with pytest.raises(KeyboardInterrupt) as caught:
                with world.verified_sources():
                    world.require_runtime()
        finally:
            sys.settrace(prior)
        assert caught.value is failure and len(seen) == 1
        assert not getattr(world._local, "verified_sources", False)
        assert getattr(world._local, "verified_source_binding", None) is None
        assert world._local.depth == 1
        assert len(calls) == 7
        world.require_runtime()
        assert len(calls) == 8
    assert world._local.depth == 0
    with pytest.raises(OSError):
        os.fstat(world._local.fd)
