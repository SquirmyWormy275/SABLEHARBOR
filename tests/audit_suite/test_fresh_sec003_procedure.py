"""Population/custody and contradiction checks using neutral native examples."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import (
    ProcedureError,
    analyze,
    discover_history,
    verify_audit_journal,
)
from enterprise.audit_suite.store import Store


@pytest.fixture
def native(tmp_path):
    root = tmp_path / "native"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    store.register_system("EXAMPLE", "selected", "events", "operator")
    for record in ("record-a", "record-b", "record-c"):
        for version in range(3):
            store.append_version(
                "EXAMPLE",
                "selected",
                "events",
                record,
                expected_version=version,
                command_id=f"{record}-{version}",
                event_at=f"2027-01-0{version + 1}T00:00:00Z",
                available_at=f"2027-01-0{version + 1}T00:01:00Z",
                content=f'{{"example_version":{version + 1}}}'.encode(),
                provenance={"source_reference": "neutral-event"},
            )
    store.grant("auditor", "fresh", "EXAMPLE", "selected", "events")
    return store


def test_discovery_reads_all_immutable_versions_across_keyset_pages(native):
    rows, pages = discover_history(
        native,
        "auditor",
        "fresh",
        "EXAMPLE",
        "selected",
        as_of="2027-01-04T00:00:00Z",
        page_size=2,
    )
    assert len(rows) == 9
    assert len(pages) == 2
    assert pages[0]["next_after_record"] == "record-b"
    assert {r["version"] for r in rows} == {1, 2, 3}
    assert len({(r["record"], r["version"]) for r in rows}) == 9


def test_discovery_uses_authorized_cutoff_without_future_correction(native):
    rows, _ = discover_history(
        native,
        "auditor",
        "fresh",
        "EXAMPLE",
        "selected",
        as_of="2027-01-02T12:00:00Z",
        page_size=1,
    )
    assert len(rows) == 6
    assert {r["version"] for r in rows} == {1, 2}


def test_missing_predecessor_fails_incomplete_instead_of_inventing_history(native):
    # A damaged disposable example, never an actual company or frozen source.
    with native._db() as db:
        db.execute("DROP TRIGGER no_version_delete")
        db.execute("DELETE FROM versions WHERE record='record-a' AND version=2")
    with pytest.raises(ProcedureError, match="Incomplete visible immutable"):
        discover_history(
            native, "auditor", "fresh", "EXAMPLE", "selected", as_of="2027-01-04T00:00:00Z"
        )


def test_other_branch_and_revoked_system_are_not_discoverable(native):
    with pytest.raises(ProcedureError, match="not granted"):
        discover_history(
            native,
            "other-auditor",
            "fresh",
            "EXAMPLE",
            "selected",
            as_of="2027-01-04T00:00:00Z",
            systems=["events"],
        )
    native.grant("auditor", "fresh", "EXAMPLE", "selected", "events", active=False)
    with pytest.raises(ProcedureError, match="not granted"):
        discover_history(
            native,
            "auditor",
            "fresh",
            "EXAMPLE",
            "selected",
            as_of="2027-01-04T00:00:00Z",
            systems=["events"],
        )


def neutral_trace():
    def item(system, record, detail, day, *, actor="security-operator", action="example"):
        source = {
            "system": system,
            "record": record,
            "sha256": "1" * 64,
            "event_at": f"2027-10-{day:02}T10:00:00+00:00",
            "available_at": f"2027-10-{day:02}T10:01:00+00:00",
        }
        return {
            "source": source,
            "document": {"actor_id": actor, "action": action, "detail": detail},
        }

    sec = [
        item(
            "vulnerability_inventory",
            "CENSUS-OCT-01",
            {"observed_asset_ids": ["asset-b"], "observed_count": 1},
            12,
        ),
        item(
            "vulnerability_baseline",
            "BASELINE-OCT-01",
            {"covered_asset_ids": ["asset-b"], "baseline_current": False},
            13,
        ),
        item(
            "vulnerability_schedule",
            "SCHEDULE-OCT-01",
            {"scheduled_asset_ids": ["asset-b"], "reported_asset_count": 2},
            14,
        ),
        item(
            "vulnerability_advisory",
            "advisory-one",
            {"advisory": {"affected_asset_id": "asset-b"}},
            15,
        ),
        item(
            "vulnerability_scan",
            "SCAN-OCT-01",
            {
                "observed_asset_ids": ["asset-b"],
                "observed_count": 1,
                "reported_count": 2,
                "finding_asset_ids": [],
                "false_clean": False,
            },
            16,
        ),
        item("vulnerability_reconciliation", "RECON-OCT-01", {"decision": "accepted"}, 17),
        item(
            "vulnerability_scan",
            "detection-one",
            {"observed_asset_ids": ["asset-a", "asset-b"], "finding_asset_ids": ["asset-b"]},
            17,
        ),
        item("vulnerability_triage", "triage-one", {"asset_id": "asset-b"}, 18),
        item("vulnerability_approval", "approval-one", {"asset_id": "asset-b"}, 19),
        item("vulnerability_remediation", "fix-one", {"asset_id": "asset-b"}, 20),
        item(
            "vulnerability_scan",
            "retest-one",
            {"observed_asset_ids": ["asset-a", "asset-b"], "finding_asset_ids": []},
            21,
            action="DATA_ONLY_RETEST",
        ),
        item("vulnerability_reconciliation", "close-one", {"selected_finding_closed": True}, 22),
    ]
    upstream = [
        {
            "source": {"system": "security_inventory"},
            "document": {"assets": [{"id": "asset-a"}, {"id": "asset-b"}]},
        },
        {
            "source": {"system": "security_baseline"},
            "document": {"selected_asset_ids": ["asset-a", "asset-b"]},
        },
    ]
    plan = {
        "asset_ids": ["asset-a", "asset-b"],
        "advisory_id": "advisory-one",
        "deep_trace_asset_id": "asset-b",
    }
    return sec, upstream, plan


def test_missed_observed_target_is_unexplained_even_if_false_clean_flag_denies_it():
    sec, upstream, plan = neutral_trace()
    result = analyze(sec, upstream, plan)
    assert result["october_coverage"]["missing_assets"] == ["asset-a"]
    assert result["causal_discrepancy"]["disposition"] == "UNEXPLAINED_FALSE_CLEAN"
    assert result["causal_discrepancy"]["omission_explains_missed_advisory"] is False
    assert len(result["count_contradictions"]) == 2
    assert result["conclusion"] == "LIMITATION"
    assert result["full_enterprise_clause_supported"] is False


def test_correction_does_not_rewrite_october_and_bad_approval_chronology_is_visible():
    sec, upstream, plan = neutral_trace()
    original = deepcopy(sec)
    next(r for r in sec if r["source"]["system"] == "vulnerability_approval")["source"][
        "available_at"
    ] = "2027-10-25T10:00:00Z"
    result = analyze(sec, upstream, plan)
    assert result["approval_fix_retest_chronology_supported"] is False
    assert result["current_retest"]["coverage_complete_selected"] is True
    assert result["october_coverage"]["scan"] == 1
    assert next(r for r in sec if r["source"]["record"] == "SCAN-OCT-01") == next(
        r for r in original if r["source"]["record"] == "SCAN-OCT-01"
    )


def test_upstream_inventory_mismatch_cannot_be_accepted_as_selected_completeness():
    sec, upstream, plan = neutral_trace()
    upstream[0]["document"]["assets"].append({"id": "unexpected-asset"})
    with pytest.raises(ProcedureError, match="declared cohort"):
        analyze(sec, upstream, plan)


def test_verification_checks_actual_immutable_engine_history_and_role_separation(tmp_path):
    store = Store(tmp_path / "workroom")
    operator = store.provision("Example source operator", ["instructor"])["id"]
    auditor = store.provision("Example auditor", ["learner"])["id"]
    reviewer = store.provision("Example reviewer", ["reviewer"])["id"]
    zero = {"artifacts": [], "workpapers": [], "populations": [], "selections": [], "reviews": []}
    final = store.create(
        operator, {**zero, "tasks": [{"status": "NOT_STARTED", "conclusion": "NOT_RUN"}]}, "create"
    )
    store.grant(final["id"], auditor, "learn")
    store.grant(final["id"], reviewer, "review")
    start = {
        "operator_id": operator,
        "auditor_id": auditor,
        "reviewer_id": reviewer,
        "zero_workroom_counts": {k: 0 for k in zero},
    }
    verify_audit_journal(store.db_path, final, start)
    wrong_identity = {**start, "reviewer_id": auditor}
    with pytest.raises(ProcedureError, match="membership separation"):
        verify_audit_journal(store.db_path, final, wrong_identity)
    # Corrupt a neutral disposable journal to exercise the independent hash check.
    with store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET hash='tampered'")
    with store.connect() as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    with pytest.raises(ProcedureError, match="event hash differs"):
        verify_audit_journal(store.db_path, final, start)
