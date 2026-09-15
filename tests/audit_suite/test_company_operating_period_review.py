"""Independent native ledger replay, dependency and reporting boundaries."""

import json
import shutil
from copy import deepcopy

import pytest

from enterprise.audit_suite import company_operating_period as period
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_operating_period import ROOT, action
from tests.audit_suite.test_company_operating_period import setup as native_setup
from tools.audit_suite.company_operating_period import report as publish_report


@pytest.fixture
def setup(tmp_path):
    return native_setup.__wrapped__(tmp_path)


@pytest.mark.parametrize("parent_skipped", [False, True])
def test_dependency_failure_can_be_explicitly_skipped_without_execution_claim(
    setup, parent_skipped
):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    if parent_skipped:
        period.record_occurrence(store, **action(group, disposition="SKIPPED", sources=[]))
    period.record_occurrence(
        store,
        **action(
            group,
            occurrence_id="NEXT",
            command_id="NEXT-SKIP",
            disposition="SKIPPED",
            recorded_at="2027-05-10T00:00:00Z",
            sources=[],
            reason="Prerequisite was not executed",
        ),
    )
    report = period.report_period(store, period_id=plan["period_id"], as_of="2027-05-17T00:00:00Z")
    assert report["occurrences"][1]["state"] == "SKIP_RECORDED"
    record = report["occurrences"][1]["history"][0]
    assert record["predecessor_refs"] == record["sources"] == []
    assert record["declared_dependency_ids"] == ["FIRST"]
    assert record["predecessor_execution"] == "NOT_ASSERTED"
    assert report["operation_execution"] == "NOT_PERFORMED_BY_LEDGER"


def test_executed_occurrence_still_rejects_skipped_predecessor(setup):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    prior = period.record_occurrence(store, **action(group, disposition="SKIPPED", sources=[]))
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        period.record_occurrence(
            store,
            **action(
                group,
                occurrence_id="NEXT",
                command_id="NEXT",
                recorded_at="2027-05-10T00:00:00Z",
                predecessor_refs=[
                    {
                        "occurrence_id": "FIRST",
                        "version": prior["version"],
                        "sha256": prior["sha256"],
                    }
                ],
            ),
        )
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("lexical_alias", [False, True])
def test_one_physical_source_cannot_be_presented_as_two_labels(setup, lexical_alias):
    store, _, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    alias = {**deepcopy(group), "source_store_id": "second-label"}
    if lexical_alias:
        from pathlib import Path

        (Path(group["root"]) / "child").mkdir(mode=0o700)
        alias["root"] = group["root"] + "/child/.."
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        period.record_occurrence(store, **action(group, sources=[group, alias]))
    assert store.path.read_bytes() == before


def test_replay_cannot_rebind_same_label_and_bytes_to_another_physical_source(setup, tmp_path):
    store, native, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    command = action(group)
    original = period.record_occurrence(store, **command)
    assert period.record_occurrence(store, **command) == original
    copy = tmp_path / "source-copy"
    shutil.copytree(native.path.parent, copy)
    other = {**deepcopy(group), "root": str(copy)}
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        period.record_occurrence(store, **action(other))
    assert store.path.read_bytes() == before


def test_offset_asof_cutoff_preserves_historical_skip_then_correction(setup):
    store, native, plan, group = setup
    period.create_period(store, repository=ROOT, plan=plan)
    period.record_occurrence(store, **action(group, disposition="SKIPPED", sources=[]))
    period.record_occurrence(
        store,
        **action(
            group, command_id="FIRST-2", expected_version=1, recorded_at="2027-04-17T00:00:00Z"
        ),
    )
    before = (store.path.read_bytes(), native.path.read_bytes())
    early = period.report_period(
        store, period_id=plan["period_id"], as_of="2027-04-16T16:59:59-07:00"
    )
    at = period.report_period(store, period_id=plan["period_id"], as_of="2027-04-16T17:00:00-07:00")
    assert early["occurrences"][0]["state"] == "SKIP_RECORDED"
    assert at["occurrences"][0]["state"] == "SOURCE_ASSERTION_RECORDED"
    assert len(early["occurrences"][0]["history"]) == 1
    assert len(at["occurrences"][0]["history"]) == 2
    assert before == (store.path.read_bytes(), native.path.read_bytes())


def test_cli_report_is_readonly_and_pins_qualified_report_not_execution(setup, tmp_path):
    store, native, plan, _ = setup
    period.create_period(store, repository=ROOT, plan=plan)
    before = (store.path.read_bytes(), native.path.read_bytes())
    destination = tmp_path / "report"
    manifest = publish_report(
        store.path.parent, plan["period_id"], "2028-01-01T00:00:00Z", destination
    )
    output = json.loads((destination / "REPORT.json").read_bytes())
    assert output["due_count"] == output["missing_due_count"] == 2
    assert output["whole_company_year"] == "NOT_ESTABLISHED"
    assert output["population_acceptance"] == "NOT_PERFORMED"
    assert manifest["audit_created"] is manifest["operation_executed_by_report"] is False
    assert before == (store.path.read_bytes(), native.path.read_bytes())
    assert str(native.path.parent) not in (destination / "REPORT.json").read_text()
