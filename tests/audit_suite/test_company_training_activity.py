import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.company_training_activity import (
    TrainingCourse,
    TrainingMember,
    TrainingRecipe,
    generate_pair,
)

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return TrainingRecipe(
        "SH",
        "cycle-a",
        "cycle-b",
        "TRN-2027-01",
        "2027-01-01T00:00:00Z",
        "2027-03-01T00:00:00Z",
        "2027-01-31T17:00:00Z",
        "2027-02-01T09:00:00Z",
        "2027-02-03T10:00:00Z",
        (
            TrainingMember("AS-P006", "ROLE-32"),
            TrainingMember("AS-P007", "ROLE-33"),
            TrainingMember("AS-P008", "ROLE-34"),
        ),
        (
            TrainingCourse(
                "LOCAL-BASE",
                "Local exercise information handling",
                ("ROLE-32", "ROLE-33", "ROLE-34"),
            ),
            TrainingCourse(
                "LOCAL-CHANGE", "Local exercise change authorization", ("ROLE-33", "ROLE-34")
            ),
        ),
        "AS-P007",
        "LOCAL-CHANGE",
        (
            "One local role-based training cycle; course choices and deadlines are exercise "
            "assumptions, not accepted corporate policy."
        ),
    )


def test_paired_sources_same_cohort_observable_lateness_and_no_future_leak(tmp_path):
    tmp_path.chmod(0o700)
    result = generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())
    assert result["cohort_count"] == 3 and result["assignments_per_branch"] == 5
    store = CompanyStore(tmp_path / "company")
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
    native = {(r["branch"], r["system"], r["record"]): json.loads(r["content"]) for r in rows}
    for system, record in [
        ("training_roster", "ROSTER-TRN-2027-01"),
        ("training_matrix", "MATRIX-TRN-2027-01"),
    ]:
        assert native["cycle-a", system, record] == native["cycle-b", system, record]
    for branch, overdue, completed in [("cycle-a", 0, 5), ("cycle-b", 1, 4)]:
        report = native[branch, "training_monitoring", "MONITOR-TRN-2027-01-1"]
        assert report["overdue_count"] == overdue and report["completion_count"] == completed
        assert report["assigned_count"] == 5
        assert len(report["completion_sources"]) == completed
        for ref in report["completion_sources"]:
            assert ref["available_at"] <= report["as_of"]
        closing = native[branch, "training_monitoring", "MONITOR-TRN-2027-01-2"]
        assert closing["overdue_count"] == 0 and closing["completion_count"] == 5
        assert closing["late_completed_count"] == overdue
    assert len([r for r in rows if r["system"] == "training_followup"]) == 1
    store.grant("learner", "audit", "SH", "cycle-b", "training_completions")
    visible = store.list_records(
        "learner", "audit", "SH", "cycle-b", "training_completions", as_of="2027-01-31T18:00:00Z"
    )
    assert len(visible["records"]) == 4
    later = store.list_records(
        "learner", "audit", "SH", "cycle-b", "training_completions", as_of="2027-02-04T00:00:00Z"
    )
    assert len(later["records"]) == 5
    for row in rows:
        body = json.loads(row["content"])
        assert _time(body["recorded_at"]) == row["event_at"]
        assert "rubric" not in body and "mode" not in body and "findings" not in body
        assert body["policy_status"] == "LOCAL_COURSE_RULES_NOT_ACCEPTED_ENTERPRISE_POLICY"
    with pytest.raises(CompanyStoreError, match="New training store"):
        generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())


@pytest.mark.parametrize(
    "change",
    [
        {"cohort": (TrainingMember("UNKNOWN", "ROLE-32"), TrainingMember("AS-P007", "ROLE-33"))},
        {"cohort": (TrainingMember("AS-P006", "ROLE-33"), TrainingMember("AS-P007", "ROLE-32"))},
        {"late_course_id": "UNASSIGNED"},
        {"followup_at": "2027-01-31T16:00:00Z"},
        {"on_time_branch": "cycle-b"},
    ],
)
def test_bad_recipe_fails_without_published_source(tmp_path, change):
    tmp_path.chmod(0o700)
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "company", repository=ROOT, recipe=replace(recipe(), **change))
    assert not (tmp_path / "company").exists()


def test_late_source_bytes_not_in_earlier_reports_and_failed_build_unpublished(
    tmp_path, monkeypatch
):
    tmp_path.chmod(0o700)
    generate_pair(tmp_path / "complete", repository=ROOT, recipe=recipe())
    store = CompanyStore(tmp_path / "complete")
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
    by_identity = {(r["branch"], r["system"], r["record"]): r for r in rows}
    for row in rows:
        body = json.loads(row["content"])
        for field in ("completion_sources", "assignment_sources"):
            for ref in body.get(field, []):
                original = by_identity[row["branch"], ref["system"], ref["record"]]
                assert original["sha256"] == ref["sha256"]
                assert original["available_at"] <= row["available_at"]
    old_append = CompanyStore.append_version
    writes = []

    def broken(self, *args, **kwargs):
        writes.append(1)
        if len(writes) == 4:
            raise OSError("Injected staging failure")
        return old_append(self, *args, **kwargs)

    monkeypatch.setattr(CompanyStore, "append_version", broken)
    with pytest.raises(OSError, match="staging failure"):
        generate_pair(tmp_path / "failed", repository=ROOT, recipe=recipe())
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob("training-stage-*"))
