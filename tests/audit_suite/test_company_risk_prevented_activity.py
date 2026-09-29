from dataclasses import replace

import pytest

from enterprise.audit_suite.company_configuration_activity import read_originals
from enterprise.audit_suite.company_risk_assessment_activity import generate_pair
from enterprise.audit_suite.company_security_logging_activity import LoggingRecipe
from enterprise.audit_suite.company_security_logging_activity import generate_pair as log_pair
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_risk_assessment_activity import (
    ROOT,
    make_recipe,
    versions,
)
from tests.audit_suite.test_company_risk_assessment_activity import (
    inputs as override_inputs,
)


@pytest.fixture
def prevented_inputs(tmp_path):
    roots, original = override_inputs.__wrapped__(tmp_path)
    _, pin = read_originals(roots["change"])
    roots["log"] = tmp_path / "blocked-log"
    log_pair(
        roots["log"],
        repository=ROOT,
        source_root=roots["change"],
        recipe=LoggingRecipe(
            "SABLEHARBOR",
            "change-original",
            pin,
            "release-a",
            "logging-a",
            "logging-b",
            "LOCAL-RELEASE",
            source_scenario="BLOCKED_THEN_ALLOWED",
        ),
    )
    selectors = {
        g.id: (g.source_refs[0].branch, {(r.system, r.record, r.version) for r in g.source_refs})
        for g in original.source_groups
    }
    selectors["log"] = (
        "logging-a",
        {("publisher_events", "EVENT-1", 1), ("detection_alerts", "BLOCKED-OBS-1", 1)},
    )
    selectors["change"] = (
        "release-a",
        {
            ("release_gate", "GATE-PROPOSED", 1),
            ("release_gate", "GATE-CORRECTED", 1),
            ("local_releases", "RELEASE-CORRECTED", 1),
        },
    )
    return roots, replace(make_recipe(roots, selectors), change_observation="BLOCKED_THEN_ALLOWED")


def test_actual_prevented_sources_remain_facts_separate_from_future_scenario(
    prevented_inputs, tmp_path
):
    roots, recipe = prevented_inputs
    original = {k: (p / "company.sqlite3").read_bytes() for k, p in roots.items()}
    out = tmp_path / "risk-prevented"
    result = generate_pair(out, repository=ROOT, source_roots=roots, recipe=recipe)
    assert len(result["records"]) == 20
    rows = versions(out)
    assert all(original[k] == (p / "company.sqlite3").read_bytes() for k, p in roots.items())
    import json

    ledgers = [json.loads(r["content"]) for r in rows if r["system"] == "risk_input_ledger"]
    assert ledgers
    text = json.dumps(ledgers)
    assert "PREVENTED_LOCAL_ATTEMPT" in text
    assert "HYPOTHETICAL_FUTURE_PREVENTION_FAILURE_NOT_OBSERVED_BYPASS" in text
    assert "OVERRIDE_USED" not in text
    assert "observed_supplier_outage" in text and "NOT_ESTABLISHED" in text
    assert "RELEASE-PROPOSED" not in text


@pytest.mark.parametrize("mode", [None, False, "AUTO", "OVERRIDE_THEN_ALLOWED"])
def test_mode_cannot_relabel_blocked_source(prevented_inputs, tmp_path, mode):
    roots, recipe = prevented_inputs
    out = tmp_path / "invalid"
    with pytest.raises(CompanyStoreError):
        generate_pair(
            out,
            repository=ROOT,
            source_roots=roots,
            recipe=replace(recipe, change_observation=mode),
        )
    assert not out.exists()
