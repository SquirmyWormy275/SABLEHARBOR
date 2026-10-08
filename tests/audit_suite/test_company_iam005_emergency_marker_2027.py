"""Selected emergency marker source must preserve its adverse history and limits."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_iam005_emergency_marker_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path(__file__).resolve().parents[2]


def test_selected_source_joins_prior_company_history_and_keeps_messy_denials(tmp_path):
    tmp_path.chmod(0o700)
    run = tmp_path / "source"
    report = source.create(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    assert report == source.verify(
        run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY
    )
    receipt = json.loads((run / "RECEIPT.json").read_text())
    assert receipt["native_version_counts"] == {"CLEAN": 9, "MESSY": 16}
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["audit_task_credit"] is receipt["authored_iam005_clause_satisfied"] is False
    assert receipt["actual_phi_processing"] is False
    assert receipt["upstream_selected_refs"]["MESSY"]["sec_october_reconciliation"]["record"] == (
        "RECON-OCT-01"
    )
    assert receipt["upstream_selected_refs"]["MESSY"]["bcm_local_retest"]["version"] == 2
    assert receipt["upstream_selected_refs"]["MESSY"]["bcm_open_closure_gate"]["record"] == (
        "KEY-AND-CAPACITY"
    )
    assert receipt["upstream_late_refs"]["MESSY"]["sec_november_recheck"]["record"] == (
        "SECURITY-RECHECK-NOV-01"
    )
    context = source._context(REPOSITORY, PRIVATE_REPOSITORY)
    bodies = [json.loads(row["content"]) for row in source._rows(context, "MESSY")]
    assert [row["decision"] for row in bodies if row["action"].startswith("EVALUATE_")] == [
        "DENY",
        "DENY_NO_BYPASS",
    ]
    assert bodies[-1]["decision"] == "OPEN"
    assert bodies[-2]["decision"] == "NO_INDEPENDENT_ASSURANCE"
    assert (
        bodies[-2]["detail"]["reviewed_sec005_native_refs"]
        == receipt["upstream_late_refs"]["MESSY"]
    )
    for prior, later in zip(bodies, bodies[1:], strict=False):
        assert later["previous_source"]["record"] != ""
        assert later["event_at"] > prior["event_at"]


def test_unreviewed_attachment_fails_closed(tmp_path):
    tmp_path.chmod(0o700)
    run = tmp_path / "source"
    source.create(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    attachment = run / "unreviewed.txt"
    attachment.write_text("extra")
    attachment.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Exact three-file"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
