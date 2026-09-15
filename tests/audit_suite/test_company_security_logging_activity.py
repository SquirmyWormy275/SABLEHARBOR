import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_change_activity import (
    ChangeRecipe,
)
from enterprise.audit_suite.company_change_activity import (
    generate_pair as change_pair,
)
from enterprise.audit_suite.company_configuration_activity import read_originals
from enterprise.audit_suite.company_security_logging_activity import (
    LoggingRecipe,
    event_chain,
    generate_pair,
    ingest,
    reconcile,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "change"
    change_pair(
        source,
        repository=ROOT,
        recipe=ChangeRecipe(
            "SH",
            "release-a",
            "release-b",
            "CYCLE",
            "2027-02-01T00:00:00Z",
            "2027-02-03T00:00:00Z",
            "Local reference release rule only",
        ),
    )
    _, pin = read_originals(source)
    return source, LoggingRecipe(
        "SH", "change-original", pin, "release-b", "logging-a", "logging-b", "LOCAL-RELEASE-AUTH"
    )


def values(store):
    with store._db() as db:
        return {
            (r["branch"], r["system"], r["record"], r["version"]): json.loads(r["content"])
            for r in db.execute("SELECT * FROM versions")
        }


def test_native_filter_gap_backfill_and_originals_preserved(inputs, tmp_path):
    source, recipe = inputs
    original_rows, original_pin = read_originals(source)
    result = generate_pair(tmp_path / "logging", repository=ROOT, source_root=source, recipe=recipe)
    store = CompanyStore(tmp_path / "logging")
    data = values(store)
    assert result["assignment"]["primary_person_id"] == "AS-P008"
    assert result["assignment"]["operating_reviewer_person_id"] == "AS-P007"
    for system, record in [
        ("source_inventory", "SOURCE-INVENTORY"),
        ("publisher_events", "EVENT-1"),
        ("publisher_events", "EVENT-2"),
    ]:
        assert data["logging-a", system, record, 1] == data["logging-b", system, record, 1]
    complete = data["logging-a", "coverage_reconciliation", "COVERAGE-INITIAL", 1]
    gap = data["logging-b", "coverage_reconciliation", "COVERAGE-INITIAL", 1]
    assert complete["missing_sequences"] == []
    assert gap["missing_sequences"] == [1] and gap["collector_sequences"] == [2]
    recovered = data["logging-b", "coverage_reconciliation", "COVERAGE-BACKFILL", 1]
    assert recovered["missing_sequences"] == [] and recovered["backfilled_sequences"] == [1]
    assert recovered["late_ingestion"][0]["exceeds_local_lag_threshold"] is True
    assert recovered["historical_gap_report_superseded"] is False
    original_first = data["logging-a", "ingestion_journal", "INGEST-1", 1]
    later_first = data["logging-b", "ingestion_journal", "INGEST-1", 1]
    assert original_first["event"] == later_first["event"]
    assert original_first["received_at"] < later_first["received_at"]
    assert data["logging-b", "collector_configuration", "COLLECTOR-CONFIG", 1][
        "excluded_authorization_decisions"
    ] == ["OVERRIDE_USED"]
    assert (
        data["logging-b", "collector_configuration", "COLLECTOR-CONFIG", 2][
            "excluded_authorization_decisions"
        ]
        == []
    )
    assert (
        data["logging-b", "detection_alerts", "AUTH-ALERT-1", 1]["recorded_at"]
        == later_first["received_at"]
    )
    assert ("logging-b", "response_tickets", "RESPONSE-BACKFILL-1", 1) in data
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
        copies = list(
            db.execute(
                "SELECT branch,record,sha256,content FROM versions "
                "WHERE system='publisher_originals'"
            )
        )
    originals = {
        (r["record"], r["sha256"]): r["content"]
        for r in original_rows
        if r["branch"] == "release-b" and r["system"] == "release_gate"
    }
    assert len(copies) == 4
    assert all(originals[r["record"], r["sha256"]] == r["content"] for r in copies)
    assert read_originals(source)[1] == original_pin
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "logging", repository=ROOT, source_root=source, recipe=recipe)


@pytest.mark.parametrize("mutation", ["claimed_hash", "body", "duplicate", "publisher_hash"])
def test_reconciliation_detects_actual_collector_and_publisher_corruption(mutation):
    events = event_chain(
        [
            {
                "source_event_at": "2027-01-01T00:00:00+00:00",
                "authorization_decision": "OVERRIDE_USED",
            }
        ]
    )
    received = ingest(events, excluded_decisions=[])
    broken = copy.deepcopy(received)
    if mutation == "claimed_hash":
        broken[0]["event"]["event_sha256"] = "f" * 64
    elif mutation == "body":
        broken[0]["event"]["authorization_decision"] = "ALLOWED"
    elif mutation == "duplicate":
        broken.append(copy.deepcopy(broken[0]))
    else:
        events[0]["event_sha256"] = "f" * 64
    if mutation in {"duplicate", "publisher_hash"}:
        with pytest.raises(CompanyStoreError):
            reconcile(events, broken)
    else:
        result = reconcile(events, broken)
        assert result["hash_mismatches"] == [1] and result["invalid_collector_hash_claims"] == [1]


def test_source_pin_or_wrong_branch_fails_before_publication(inputs, tmp_path):
    source, recipe = inputs
    for name, bad in [
        ("bad-pin", replace(recipe, source_versions_sha256="0" * 64)),
        ("wrong-branch", replace(recipe, source_branch="release-a")),
    ]:
        with pytest.raises(CompanyStoreError):
            generate_pair(tmp_path / name, repository=ROOT, source_root=source, recipe=bad)
        assert not (tmp_path / name).exists()


def test_direct_logging_output_cannot_extend_original_source_tree(inputs):
    source, recipe = inputs
    before = (source / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="outside original source tree"):
        generate_pair(source / "nested", repository=ROOT, source_root=source, recipe=recipe)
    assert not (source / "nested").exists()
    assert (source / "company.sqlite3").read_bytes() == before
