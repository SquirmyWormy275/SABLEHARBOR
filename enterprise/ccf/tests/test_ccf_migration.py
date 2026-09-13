"""History migration must reproduce exact prior states without altering its source."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from enterprise.ccf.operations import examples, migration, store, testing
from enterprise.ccf.tests.test_operations import plans  # noqa: F401


@pytest.fixture
def legacy(tmp_path, plans):  # noqa: F811
    repo = tmp_path / "legacy-repo"
    modules = repo / "enterprise/ccf/operations"
    modules.mkdir(parents=True)
    for module in (store, testing):
        (modules / Path(module.__file__).name).write_text(
            Path(module.__file__).read_text() + "\n# Trusted historical fixture\n"
        )
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "user.name=CCF Test",
            "-c",
            "user.email=ccf@example.invalid",
            "commit",
            "-qm",
            "historical fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    source = tmp_path / "original.sqlite3"
    with migration.legacy_runtime(repo, "HEAD") as (runtime, commit):
        tokens = runtime.initialize(source, plans, examples.principals(["B"]))
        runtime.now = lambda: examples.AT
        db = runtime.connect(source)
        try:
            p = plans["COLLECT:SH-IAM-004:B"]
            runtime.command(
                db,
                tokens["DEMO-PREPARER"],
                "CASE",
                "create",
                dict(plan_id=p["id"], scope=examples.scope()),
                0,
            )
        finally:
            db.close()
    return repo, source, commit


def test_verified_migration_copies_history_and_preserves_source(legacy, tmp_path):
    repo, source, commit = legacy
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "migrated"
    receipt = migration.migrate(source, output, commit, repo)
    assert receipt["cases"] == 1 and receipt["original_unchanged"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    db = store.connect(output / "workflow.sqlite3")
    try:
        assert store.replay(db)["CASE"]["state"] == "AWAITING_POPULATION"
    finally:
        db.close()
    with pytest.raises(ValueError, match="new directory"):
        migration.migrate(source, output, commit, repo)


def test_migration_rejects_changed_history(legacy, tmp_path, monkeypatch):
    repo, source, commit = legacy
    original = store.replay

    def changed(db):
        states = original(db)
        states["CASE"]["state"] = "REVIEWED_PASS"
        return states

    monkeypatch.setattr(store, "replay", changed)
    out = tmp_path / "bad"
    with pytest.raises(ValueError, match="changes retained"):
        migration.migrate(source, out, commit, repo)
    assert not out.exists()


def test_migration_preserves_failed_history_and_revoked_credentials(legacy, tmp_path, monkeypatch):
    """Use a locally pinned fixture commit, never assume CI has PR146 Git history."""
    repo, _, commit = legacy
    bundle = tmp_path / "historical-workflow"
    with migration.legacy_runtime(repo, commit) as (runtime, resolved):
        assert resolved == commit
        # The original termination example exercises failure, same-period retest,
        # and a later independently passed case without building all 24 adapters.
        with monkeypatch.context() as patch:
            patch.setattr(examples, "store", runtime)
            patch.setattr(testing, "ADAPTERS", {"SH-IAM-004": "termination"})
            fixture_plans = {
                "COLLECT:SH-IAM-004:B": dict(
                    id="COLLECT:SH-IAM-004:B",
                    control_id="SH-IAM-004",
                    boundary_id="B",
                    adapter="termination",
                    criteria={"BASE": "Retain original failed revocation timing"},
                )
            }
            summary = examples.build(bundle, fixture_plans)
        assert summary["cases"] == 3 and summary["historical_failure_preserved"]
        preparer = (bundle / "DEMO-PREPARER.credential").read_text().strip()
        reviewer = (bundle / "DEMO-REVIEWER.credential").read_text().strip()
        admin = (bundle / "DEMO-ADMIN.credential").read_text().strip()
        source = bundle / "workflow.sqlite3"
        runtime.now = lambda: "2026-09-12T11:00:00+00:00"
        db = runtime.connect(source)
        try:
            runtime.revoke(db, admin, "DEMO-PREPARER")
            before = runtime.replay(db)
            original_tables = {
                table: [tuple(row) for row in db.execute(f"SELECT * FROM {table}")]
                for table in ("principal", "event", "revocation")
            }
        finally:
            db.close()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "migrated-full-history"
    receipt = migration.migrate(source, output, commit, repo)
    assert receipt["cases"] == 3 and receipt["legacy_commit"] == commit
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
    monkeypatch.setattr(store, "now", lambda: "2026-09-12T11:01:00+00:00")
    db = store.connect(output / "workflow.sqlite3")
    try:
        assert store.replay(db) == before
        for table, original_rows in original_tables.items():
            assert [tuple(row) for row in db.execute(f"SELECT * FROM {table}")] == original_rows
        failed = store.replay(db)["DEMO-termination-negative"]
        assert failed["original_outcome"] == "FAIL"
        assert failed["historical_failure"]
        assert failed["state"] == "CLOSED_PROSPECTIVE_VALIDATION"
        assert [s["result"]["outcome"] for s in failed["submissions"]] == ["FAIL", "PASS"]
        assert failed["closure"]["validation_case_id"] == "DEMO-termination-prospective"
        assert store.authenticate(db, preparer) == "DEMO-PREPARER"
        with pytest.raises(ValueError, match="current scoped permission"):
            store.command(
                db,
                preparer,
                "AFTER-REVOCATION",
                "create",
                dict(plan_id="COLLECT:SH-IAM-004:B", scope=examples.scope()),
                0,
            )
        with pytest.raises(ValueError, match="current scoped permission"):
            store.report(db, preparer)
        assert len(store.report(db, reviewer)["cases"]) == 3
    finally:
        db.close()
