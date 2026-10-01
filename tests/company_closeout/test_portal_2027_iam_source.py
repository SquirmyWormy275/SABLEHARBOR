"""The 2027 IAM input must retain its unsupported census and due-count gaps."""

import copy
import json
from pathlib import Path

import pytest

from enterprise.operations.completed_period import build
from tools.company_closeout.portal_2027_iam_source import derive, sha256

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "enterprise/operations/source/portal_2027_iam_opening_2026_09_29.json"
EXPORT = ROOT / "enterprise/operations/portal_2027_iam/opening_candidates_v0.1.json"


@pytest.fixture(scope="module")
def inputs():
    config = json.loads(SOURCE.read_text())
    policy = json.loads((ROOT / config["source_paths"]["iam_procedure"]).read_text())
    records = build()
    release = config["accepted_august_release"]
    records["repository_source_commit"] = release["source_commit"]
    records["repository_source_available_at"] = release["source_available_at"]
    return records, config, policy


def test_bounded_candidate_denominator_and_generated_export(inputs):
    result = derive(*inputs)
    assert result == json.loads(EXPORT.read_text())
    assert result["august_employee_principal_pairs"] == 702
    assert result["last_supported_september_person_principal_pairs"] == 701
    assert result["excluded_nonemployee_directors"] == 7
    assert result["confirmed_2027_opening_person_principal_pairs"] is None
    candidates = result["opening_candidates"]
    assert len({row["person_id"] for row in candidates}) == 701
    assert all(row["service_id_at_2027_opening"] is None for row in candidates)
    assert all(row["system_account_id_at_2027_opening"] is None for row in candidates)
    assert all(row["privileged_at_2027_opening"] is None for row in candidates)
    assert "SH-EMP-ESS-0054" not in {row["person_id"] for row in candidates}
    assert result["september_december_bridge"]["unrepresented_jml_count"] is None
    assert (
        result["september_december_bridge"]["supported_september_state_effective_as_of"]
        == "2026-09-15"
    )
    assert (
        result["september_december_bridge"]["public_release_known_on_not_before"]
        == "2026-09-22T23:50:07Z"
    )
    q1 = result["q1_due_event_schedule"][0]
    assert q1["privileged_review_due_count"] is None
    assert q1["missing_performance_count"] is None
    assert q1["observed_performance_source_count"] == 0
    assert result["case_branches"]["A"] == result["case_branches"]["B"]


def test_pinned_controlling_sources_have_not_changed(inputs):
    _, config, _ = inputs
    for path_key, hash_key in (
        ("august_roster_and_event", "august_roster_and_event_sha256"),
        ("iam_procedure", "iam_procedure_sha256"),
    ):
        assert sha256(ROOT / config["source_paths"][path_key]) == config["source_paths"][hash_key]


@pytest.mark.parametrize(
    "change,reason",
    [
        (
            lambda r, c, p: r["tables"]["access"].append(copy.deepcopy(r["tables"]["access"][0])),
            "Duplicate person_id",
        ),
        (lambda r, c, p: r["tables"]["access"].pop(), "population differs"),
        (lambda r, c, p: r["tables"]["change_events"].clear(), "September JML event"),
        (
            lambda r, c, p: r["tables"]["change_events"][0].update(
                effective_at="2027-01-04T17:00:00-07:00"
            ),
            "Known September exit",
        ),
        (
            lambda r, c, p: c["bridge"].update(september_december_jml_population_complete=True),
            "Unreconciled Sep-Dec bridge",
        ),
        (
            lambda r, c, p: c["bridge"].update(
                public_release_known_on_not_before="2026-09-15T00:00:00Z"
            ),
            "Unreconciled Sep-Dec bridge",
        ),
        (lambda r, c, p: c["opening"].update(confirmed_active_person_count=701), "promoted"),
        (lambda r, c, p: c["q1_iam_007"].update(privileged_review_due_count=701), "promoted"),
        (lambda r, c, p: c["q1_iam_007"].update(known_2027_jml_event_ids=["FAKE"]), "promoted"),
        (
            lambda r, c, p: c["case_branches"]["B"].update(company_delta_state="NONE"),
            "Unaccepted A/B",
        ),
        (
            lambda r, c, p: c.update(fact_status="COMPLETED_2027_ACTUAL"),
            "presented as completed",
        ),
        (
            lambda r, c, p: next(x for x in p if x["control_id"] == "SH-IAM-007").update(
                procedure="Annual review"
            ),
            "draft procedure",
        ),
    ],
)
def test_false_completion_and_wrong_period_rejected(inputs, change, reason):
    records, config, policy = copy.deepcopy(inputs)
    change(records, config, policy)
    with pytest.raises(ValueError, match=reason):
        derive(records, config, policy)
