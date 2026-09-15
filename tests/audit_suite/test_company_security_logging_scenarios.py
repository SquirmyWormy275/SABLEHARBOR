# Fixture imported for pytest discovery.
# ruff: noqa: F811
from dataclasses import replace

import pytest

from enterprise.audit_suite import company_security_logging_activity as logging
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_security_logging_activity import (  # noqa:F401
    ROOT,
    inputs,
    values,
)


def test_blocked_source_observation_depends_on_actual_ingestion(inputs, tmp_path):
    source, recipe = inputs
    original = (source / "company.sqlite3").read_bytes()
    result = logging.generate_pair(
        tmp_path / "blocked",
        repository=ROOT,
        source_root=source,
        recipe=replace(recipe, source_branch="release-a", source_scenario="BLOCKED_THEN_ALLOWED"),
    )
    assert len(result["records"]) == 32
    records = values(CompanyStore(tmp_path / "blocked"))
    for branch in ("logging-a", "logging-b"):
        observation = records[branch, "detection_alerts", "BLOCKED-OBS-1", 1]
        event = records[branch, "publisher_events", "EVENT-1", 1]["event"]
        assert event["authorization_decision"] == "BLOCKED"
        assert observation["rule_id"] == "LOCAL-AUTHORIZATION-BLOCKED"
        assert observation["severity"] == "LOCAL_EXERCISE_INFORMATIONAL"
        assert observation["source_event_sha256"] == event["event_sha256"]
        assert (branch, "detection_alerts", "AUTH-ALERT-1", 1) not in records
    first = records["logging-a", "detection_alerts", "BLOCKED-OBS-1", 1]
    late = records["logging-b", "detection_alerts", "BLOCKED-OBS-1", 1]
    assert first["recorded_at"] < late["recorded_at"]
    assert records["logging-b", "coverage_reconciliation", "COVERAGE-INITIAL", 1][
        "missing_sequences"
    ] == [1]
    assert (
        records["logging-b", "coverage_reconciliation", "COVERAGE-BACKFILL", 1]["missing_sequences"]
        == []
    )
    assert (source / "company.sqlite3").read_bytes() == original


@pytest.mark.parametrize("scenario", [None, False, "LATEST", "blocked"])
def test_invalid_source_scenario_fails_before_publication(inputs, tmp_path, scenario):
    source, recipe = inputs
    with pytest.raises(CompanyStoreError):
        logging.generate_pair(
            tmp_path / "bad",
            repository=ROOT,
            source_root=source,
            recipe=replace(recipe, source_scenario=scenario),
        )
    assert not (tmp_path / "bad").exists()


def test_blocked_mode_cannot_relabel_override_source(inputs, tmp_path):
    source, recipe = inputs
    with pytest.raises(CompanyStoreError, match="authorization scenario"):
        logging.generate_pair(
            tmp_path / "bad",
            repository=ROOT,
            source_root=source,
            recipe=replace(recipe, source_scenario="BLOCKED_THEN_ALLOWED"),
        )
    assert not (tmp_path / "bad").exists()


def test_source_changed_during_generation_prevents_publication(inputs, tmp_path, monkeypatch):
    source, recipe = inputs
    reader = logging.read_originals
    calls = 0

    def changed(root):
        nonlocal calls
        calls += 1
        rows, pin = reader(root)
        return rows, pin if calls == 1 else "0" * 64

    monkeypatch.setattr(logging, "read_originals", changed)
    with pytest.raises(CompanyStoreError, match="changed during"):
        logging.generate_pair(tmp_path / "bad", repository=ROOT, source_root=source, recipe=recipe)
    assert calls == 2
    assert not (tmp_path / "bad").exists()
