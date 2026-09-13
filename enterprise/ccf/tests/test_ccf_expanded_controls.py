"""Original record assertions exercise errors independently of fixture status labels."""

import copy

import pytest

from enterprise.ccf.operations import examples, testing

NEW = tuple(list(testing.ADAPTERS.values())[8:])


def plan(adapter):
    return dict(
        adapter=adapter, boundary_id="B", criteria={"BASE": "Inspect full original procedure"}
    )


def evaluate(adapter, records, population=None, submission=None):
    return testing.evaluate(
        plan(adapter),
        examples.scope(),
        population or examples.population(records),
        submission or examples.submission(plan(adapter), records),
        examples.AT,
    )


@pytest.mark.parametrize("adapter", NEW)
def test_new_positive_negative_and_missing_human_work(adapter):
    rows = [examples.record(adapter, "B")]
    assert evaluate(adapter, rows)["outcome"] == "PASS"
    rows[0] = examples.record(adapter, "B", failed=True)
    result = evaluate(adapter, rows)
    assert result["outcome"] == "FAIL"
    assert any(not value for value in result["checks"][0]["assertions"].values())
    rows[0] = examples.record(adapter, "B")
    sub = examples.submission(plan(adapter), rows)
    sub["manual_tests"] = {}
    assert evaluate(adapter, rows, submission=sub)["outcome"] == "NOT_RUN"


@pytest.mark.parametrize("adapter", NEW)
def test_every_contract_field_is_required_and_typed(adapter):
    original = examples.record(adapter, "B")
    for field, value in original["data"].items():
        rows = [copy.deepcopy(original)]
        del rows[0]["data"][field]
        assert evaluate(adapter, rows)["outcome"] == "NOT_RUN", (adapter, field)
        # Null cannot be coerced into a successful original-record assertion.
        rows = [copy.deepcopy(original)]
        rows[0]["data"][field] = None
        assert evaluate(adapter, rows)["outcome"] != "PASS", (adapter, field)
        if isinstance(value, list):
            rows[0]["data"][field] = ["DUPLICATE", "DUPLICATE"]
            assert evaluate(adapter, rows)["outcome"] == "NOT_RUN", (adapter, field)
        elif type(value) is bool:
            rows[0]["data"][field] = 1
            assert evaluate(adapter, rows)["outcome"] == "NOT_RUN", (adapter, field)
        elif type(value) in (int, float):
            for invalid in (True, -1, float("nan"), float("inf"), "1"):
                rows[0]["data"][field] = invalid
                assert evaluate(adapter, rows)["outcome"] == "NOT_RUN", (adapter, field)
        elif isinstance(value, str) and "T09:" in value:
            rows[0]["data"][field] = value.split("+")[0]
            assert evaluate(adapter, rows)["outcome"] == "NOT_RUN", (adapter, field)


@pytest.mark.parametrize(
    "adapter,field,value",
    [
        ("identity_creation", "approved_at", "2026-09-09T12:00:00+00:00"),
        ("access_grant", "approver_id", "UNAUTHORIZED"),
        ("mover_access", "approved_at", "2026-09-09T12:00:00+00:00"),
        ("privilege_expiry", "activated_at", "2026-09-09T12:00:00+00:00"),
        ("service_account", "rotated_at", "2026-09-09T12:00:00+00:00"),
        ("revision_review", "reviewed_at", "2026-09-09T12:00:00+00:00"),
        ("release_tests", "passed_test_ids", ["DEMO-SECURITY"]),
        ("deployment_artifact", "authorized_identity_ids", []),
        ("asset_inventory", "owned_asset_ids", []),
        ("disposal", "authorized_approver_ids", []),
        ("exception_validity", "observed_at", "2026-09-09T09:30:00+00:00"),
        ("delegated_decision", "decided_at", "2026-09-09T09:30:00+00:00"),
        ("conduct_acknowledgment", "acknowledged_at", "2026-09-09T08:00:00+00:00"),
        ("log_coverage", "max_observed_gap_seconds", 61),
        ("corrective_retest", "retester_id", "DEMO-ENGINEER"),
        ("change_notice", "required_lead_seconds", 7200),
    ],
)
def test_adversarial_inversions_and_omissions(adapter, field, value):
    rows = [examples.record(adapter, "B")]
    rows[0]["data"][field] = value
    assert evaluate(adapter, rows)["outcome"] == "FAIL"


@pytest.mark.parametrize("adapter", NEW)
def test_wrong_record_kind_cannot_hide_in_reconciled_population(adapter):
    rows = [examples.record(adapter, "B")]
    unrelated = copy.deepcopy(rows[0])
    unrelated.update(id="DEMO-UNTESTED", kind="manual_attachment")
    rows.append(unrelated)
    assert evaluate(adapter, rows)["outcome"] == "NOT_RUN"


def test_empty_inventory_cannot_vacuously_pass_and_extra_rights_are_detected():
    row = examples.record("asset_inventory", "B")
    for key in ("discovered_asset_ids", "registered_asset_ids", "owned_asset_ids"):
        row["data"][key] = []
    assert evaluate("asset_inventory", [row])["outcome"] == "FAIL"
    row = examples.record("service_account", "B")
    row["data"]["actual_right_ids"].append("DEMO-ROOT")
    assert evaluate("service_account", [row])["outcome"] == "FAIL"


def test_conflicting_release_results_and_notice_hash_substitution_fail():
    row = examples.record("release_tests", "B")
    row["data"]["failed_test_ids"] = ["DEMO-SECURITY"]
    assert evaluate("release_tests", [row])["outcome"] == "FAIL"
    row = examples.record("change_notice", "B")
    row["data"]["delivered_notice_sha256"] = "f" * 64
    assert evaluate("change_notice", [row])["outcome"] == "FAIL"


def test_population_contract_rejects_duplicate_registered_ids():
    rows = [examples.record("asset_inventory", "B")]
    pop = examples.population(rows)
    pop["expected_ids"] *= 2
    with pytest.raises(ValueError, match="unique"):
        evaluate("asset_inventory", rows, population=pop)


def test_review_cannot_claim_removal_before_decision():
    row = examples.record("access_review", "B")
    row["data"]["removed_at"] = "2026-09-09T08:00:00+00:00"
    assert evaluate("access_review", [row])["outcome"] == "FAIL"
