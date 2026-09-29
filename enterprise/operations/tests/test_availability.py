import copy
import os
import subprocess
from datetime import datetime, timedelta

import pytest

from enterprise.operations.availability import PREVIEW, apply, repository_context
from enterprise.operations.completed_period import SOURCE, build, read, validate, visible_rows
from enterprise.operations.september_custody import as_of


def test_committed_repository_time_is_deterministic_and_dirty_preview_denied(tmp_path):
    env = os.environ | {
        "GIT_AUTHOR_DATE": "2026-09-15T03:10:00Z",
        "GIT_COMMITTER_DATE": "2026-09-15T03:10:00Z",
    }

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, env=env, text=True)

    git("init", "-q")
    git("config", "user.name", "Synthetic validation")
    git("config", "user.email", "test@example.invalid")
    (tmp_path / "source.txt").write_text("declared source\n")
    git("add", "source.txt")
    git("commit", "-qm", "Synthetic source test")
    context = repository_context(tmp_path)
    assert context == repository_context(tmp_path)
    assert context["repository_source_available_at"] == "2026-09-15T03:10:00Z"
    row = dict(
        available_at="2026-09-15T00:00:00Z",
        recorded_at="2026-09-15T00:00:00Z",
        effective_period="2026-08",
        acceptance_state="PENDING_REPOSITORY_ACCEPTANCE",
    )
    result = apply(dict(available_at=row["available_at"], rows=[row]), context)
    assert row["authored_day"] == "2026-09-15"
    assert row["declared_available_precision"] == "DAY"
    assert row["recorded_at"] == row["available_at"] == "2026-09-15T03:10:00Z"
    assert row["acceptance_state"] == "PENDING_REPOSITORY_ACCEPTANCE"
    assert visible_rows([row], as_of="2026-08-31", known_on="2026-09-15T03:09:59Z") == []
    assert visible_rows([row], as_of="2026-08-31", known_on="2026-09-15T03:10:00Z") == [row]
    (tmp_path / "source.txt").write_text("new uncommitted fact\n")
    dirty = repository_context(tmp_path)
    assert dirty["publication_state"] == PREVIEW
    assert not dirty["publishable_source_snapshot"]
    preview = apply(copy.deepcopy(result), dirty)
    assert visible_rows(preview["rows"], as_of="2026-08-31", known_on="2026-09-16T00:00:00Z") == []
    assert visible_rows(
        preview["rows"], as_of="2026-08-31", known_on="2026-09-16T00:00:00Z", allow_preview=True
    )


def test_all_generated_records_and_receipts_have_repository_floor():
    result = build()
    floor = datetime.fromisoformat(result["repository_source_available_at"])
    before = (floor - timedelta(microseconds=1)).isoformat()
    for rows in result["tables"].values():
        assert all(datetime.fromisoformat(r["available_at"]) >= floor for r in rows)
        assert visible_rows(rows, as_of="2031-12-31", known_on=before, allow_preview=True) == []
    broken = copy.deepcopy(result["tables"])
    broken["settlements"][0]["available_at"] = before
    with pytest.raises(ValueError, match="earlier known-on"):
        validate(read(SOURCE), broken)


def test_custody_query_does_not_leak_dirty_or_precommit_events():
    event = dict(
        effective_at="2026-09-14T14:00:00-06:00",
        available_at="2026-09-15T03:10:00Z",
        publication_state=PREVIEW,
    )
    packet = {"events": [event]}
    assert (
        as_of(packet, effective_at="2026-09-15T00:00:00Z", known_on="2026-09-16T00:00:00Z") is None
    )
    assert (
        as_of(
            packet,
            effective_at="2026-09-15T00:00:00Z",
            known_on="2026-09-15T03:09:59Z",
            allow_preview=True,
        )
        is None
    )
    event["publication_state"] = "COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE"
    assert (
        as_of(packet, effective_at="2026-09-15T00:00:00Z", known_on="2026-09-15T03:10:00Z") == event
    )
