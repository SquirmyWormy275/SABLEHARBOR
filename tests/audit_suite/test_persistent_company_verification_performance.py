"""Warm parsing never replaces byte pins or fresh current-row verification."""

import os
import sqlite3
from contextlib import closing

import pytest

from enterprise.audit_suite import persistent_company_journey as runtime
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
