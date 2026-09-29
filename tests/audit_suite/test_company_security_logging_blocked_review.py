"""Independent blocked-attempt source linkage and historical collection checks."""

import copy
import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from enterprise.audit_suite import company_security_logging_activity as logging
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_security_logging_activity import ROOT
from tests.audit_suite.test_company_security_logging_activity import inputs as base_inputs
from tests.audit_suite.test_company_security_logging_collection import exercise


@pytest.fixture
def inputs(tmp_path):
    source, recipe = base_inputs.__wrapped__(tmp_path)
    return source, replace(
        recipe, source_branch="release-a", source_scenario="BLOCKED_THEN_ALLOWED"
    )


def rows(root):
    with CompanyStore(root)._db() as db:
        return [
            dict(row)
            for row in db.execute("SELECT * FROM versions ORDER BY branch,system,record,version")
        ]


def test_blocked_observation_has_exact_native_chain_and_historical_gap(inputs, tmp_path):
    source, recipe = inputs
    before = (source / "company.sqlite3").read_bytes()
    native, pin = logging.read_originals(source)
    selected = [r for r in native if r["branch"] == recipe.source_branch]
    assert not any(
        r["system"] == "local_releases" and r["record"] == "RELEASE-PROPOSED" for r in selected
    )
    gates = sorted(
        (r for r in selected if r["system"] == "release_gate"), key=lambda r: r["event_at"]
    )
    assert [json.loads(r["content"])["decision"] for r in gates] == ["BLOCKED", "ALLOWED"]
    output = tmp_path / "logging"
    logging.generate_pair(output, repository=ROOT, source_root=source, recipe=recipe)
    actual = rows(output)
    for branch in (recipe.complete_branch, recipe.omission_branch):
        data = {
            (r["system"], r["record"], r["version"]): (r, json.loads(r["content"]))
            for r in actual
            if r["branch"] == branch
        }
        events = [data["publisher_events", f"EVENT-{n}", 1][1]["event"] for n in (1, 2)]
        assert [event["authorization_decision"] for event in events] == ["BLOCKED", "ALLOWED"]
        previous = ""
        for gate, event in zip(gates, events, strict=True):
            for field in ("company", "branch", "system", "record", "version", "sha256"):
                assert event["upstream"][field] == gate[field]
            assert event["upstream"]["source_store_id"] == recipe.source_store_id
            assert event["source_event_at"] == gate["event_at"]
            assert event["previous_event_sha256"] == previous
            previous = sha(encoded({k: v for k, v in event.items() if k != "event_sha256"}))
            assert previous == event["event_sha256"]
            original = data["publisher_originals", gate["record"], 1][0]
            assert original["content"] == gate["content"]
            assert original["sha256"] == gate["sha256"]
        alerts = [
            (r, body) for (system, _, _), (r, body) in data.items() if system == "detection_alerts"
        ]
        assert not any(body["rule_id"] == "LOCAL-AUTHORIZATION-OVERRIDE" for _, body in alerts)
        blocked = [
            (r, body) for r, body in alerts if body["rule_id"] == "LOCAL-AUTHORIZATION-BLOCKED"
        ]
        assert len(blocked) == 1
        alert_row, alert = blocked[0]
        assert alert_row["record"] == "BLOCKED-OBS-1"
        assert alert["severity"] == "LOCAL_EXERCISE_INFORMATIONAL"
        assert alert["source_event_sha256"] == events[0]["event_sha256"]
        ingestion_row, ingestion = data["ingestion_journal", "INGEST-1", 1]
        assert alert_row["event_at"] == ingestion_row["event_at"] == ingestion["received_at"]
        assert ingestion["event"] == events[0]
        assert ingestion["received_at"] >= events[0]["source_event_at"]
        for field in ("company", "branch", "system", "record", "version", "sha256"):
            assert alert["ingestion"][field] == ingestion_row[field]
        initial = data["coverage_reconciliation", "COVERAGE-INITIAL", 1][1]
        final = data["coverage_reconciliation", "COVERAGE-BACKFILL", 1][1]
        assert initial["missing_sequences"] == ([1] if branch == recipe.omission_branch else [])
        assert final["missing_sequences"] == []
        assert final["historical_gap_report_superseded"] is False
        if branch == recipe.omission_branch:
            assert data["collector_configuration", "COLLECTOR-CONFIG", 1][1][
                "excluded_authorization_decisions"
            ] == ["BLOCKED"]
            assert (
                data["collector_configuration", "COLLECTOR-CONFIG", 2][1][
                    "excluded_authorization_decisions"
                ]
                == []
            )
            assert final["backfilled_sequences"] == [1]
            assert ingestion["ingestion_lag_seconds"] > recipe.local_max_ingestion_lag_seconds
    assert (source / "company.sqlite3").read_bytes() == before
    assert logging.read_originals(source)[1] == pin


@pytest.mark.parametrize("fault", ["blocked_gate", "wrong_artifact", "unqualified", "availability"])
def test_repinned_release_requires_consistent_allowed_artifact(
    inputs, tmp_path, monkeypatch, fault
):
    source, recipe = inputs
    native, _ = logging.read_originals(source)
    changed = copy.deepcopy(native)
    gate = next(
        r
        for r in changed
        if r["branch"] == recipe.source_branch
        and r["system"] == "release_gate"
        and r["record"] == "GATE-PROPOSED"
    )
    release = next(
        r
        for r in changed
        if r["branch"] == recipe.source_branch and r["system"] == "local_releases"
    )
    body = json.loads(release["content"])
    if fault == "blocked_gate":
        body["gate"] = {
            "system_id": gate["system"],
            "record_id": gate["record"],
            "version": gate["version"],
            "sha256": gate["sha256"],
            "available_at": gate["available_at"],
        }
    elif fault == "wrong_artifact":
        body["artifact"] = json.loads(gate["content"])["artifact"]
    elif fault == "unqualified":
        body["classification"] = "UNQUALIFIED_RELEASE"
    else:
        release["available_at"] = (
            datetime.fromisoformat(release["event_at"]) - timedelta(seconds=1)
        ).isoformat()
    release["content"] = encoded(body)
    release["sha256"] = sha(release["content"])
    pin = sha(encoded([{k: v for k, v in row.items() if k != "content"} for row in changed]))
    monkeypatch.setattr(logging, "read_originals", lambda _: (changed, pin))
    with pytest.raises(CompanyStoreError):
        logging.generate_pair(
            tmp_path / "invalid",
            repository=ROOT,
            source_root=source,
            recipe=replace(recipe, source_versions_sha256=pin),
        )
    assert not (tmp_path / "invalid").exists()


def test_blocked_pair_exact_originals_collect_with_versions_and_replay(inputs, tmp_path):
    source, recipe = inputs
    before = (source / "company.sqlite3").read_bytes()
    output = tmp_path / "logging"
    logging.generate_pair(output, repository=ROOT, source_root=source, recipe=recipe)
    originals = rows(output)
    result = exercise(
        output,
        tmp_path / "audit",
        company_id=recipe.company_id,
        branches=[recipe.complete_branch, recipe.omission_branch],
    )
    assert sum(row["artifact_count"] for row in result["engagements"]) == len(originals)
    assert result["temporary_grants_revoked"] is True
    assert rows(output) == originals
    assert (source / "company.sqlite3").read_bytes() == before
