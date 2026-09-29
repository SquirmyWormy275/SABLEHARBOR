"""Independent causal/provenance review of prevented-attempt risk interpretation."""

import copy
import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from enterprise.audit_suite import company_risk_assessment_activity as risk
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_risk_assessment_activity import ROOT, versions
from tests.audit_suite.test_company_risk_prevented_activity import prevented_inputs as base_inputs


@pytest.fixture
def inputs(tmp_path):
    return base_inputs.__wrapped__(tmp_path)


def test_prevented_risk_ledger_keeps_exact_facts_hypotheses_and_authority_separate(
    inputs, tmp_path
):
    roots, recipe = inputs
    before = {key: (root / "company.sqlite3").read_bytes() for key, root in roots.items()}
    output = tmp_path / "reviewed-risk"
    risk.generate_pair(output, repository=ROOT, source_roots=roots, recipe=recipe)
    raw = versions(output)
    assert len(raw) == 20
    records = {
        (r["branch"], r["system"], r["record"], r["version"]): json.loads(r["content"]) for r in raw
    }
    groups = {g.id: g for g in recipe.source_groups}
    ledgers = []
    for branch in recipe.branch_ids:
        ledger = records[branch, "risk_input_ledger", "INPUT-LEDGER", 1]
        ledgers.append(ledger["inputs"])
        assert ledger["likelihood_basis"] == "LOCAL_ASSUMPTION_NOT_INFERRED_FROM_SINGLE_OBSERVATION"
        assert (
            len(
                {
                    ledger["coordinator_id"],
                    ledger["quality_reviewer_id"],
                    ledger["independent_assurance_contact_id"],
                }
            )
            == 3
        )
        internal = ledger["inputs"]["INTERNAL_CHANGE"]
        facts = internal["observations"]
        assert facts["historical_gate_decision"] == "BLOCKED"
        assert facts["observed_bypass"] is False
        assert facts["observation_kind"] == "PREVENTED_LOCAL_ATTEMPT"
        assert facts["later_gate_decision"] == "ALLOWED"
        assert facts["alert_rule"] == "LOCAL-AUTHORIZATION-BLOCKED"
        assert (
            internal["scenario_status"]
            == "HYPOTHETICAL_FUTURE_PREVENTION_FAILURE_NOT_OBSERVED_BYPASS"
        )
        expected = {
            (g.source_store_id, *(getattr(ref, f) for f in risk.FIELDS))
            for key in ("log", "change")
            for g in [groups[key]]
            for ref in g.source_refs
        }
        assert {
            (ref["source_store_id"], *(ref[f] for f in risk.FIELDS))
            for ref in internal["source_records"]
        } == expected
        assert any(ref["record"] == "RELEASE-CORRECTED" for ref in internal["source_records"])
        assert not any(ref["record"] == "RELEASE-PROPOSED" for ref in internal["source_records"])
        external = ledger["inputs"]["EXTERNAL_DEPENDENCY"]["observations"]
        assert external["provider_operating"] is False and external["contract_executed"] is False
        assert external["incident_cause"] == "NOT_ESTABLISHED_FROM_PROBE_RECORDS"
        assert external["observed_supplier_outage"] == "NOT_ESTABLISHED"
        assert external["incident_and_provider_observations_are_separate"] is True
        check = records[branch, "risk_reconciliation", "INPUT-CHECK", 1]
        assert check["missing_declared_input_ids"] == (
            [] if branch == recipe.branch_ids[0] else ["INTERNAL_CHANGE"]
        )
    assert ledgers[0] == ledgers[1]
    for body in records.values():
        assert body["assurance_activity"] == "NOT_PERFORMED"
        assert body["risk_acceptance"] == "NOT_PERFORMED"
        assert body["board_ratification"] == "NOT_ASSERTED"
        assert body["signatures"] == "NONE_CREATED"
        for assessment in body.get("risks", []):
            assert (
                assessment["method"]
                == "LOCAL_ORDINAL_LIKELIHOOD_TIMES_IMPACT_NOT_EMPIRICAL_PROBABILITY"
            )
            assert assessment["residual_status"] == "CONDITIONAL_PROJECTION_NOT_DEMONSTRATED"
            assert assessment["treatment_status"] == "PROPOSED_NOT_IMPLEMENTED_OR_AUTHORIZED"
    assert all(
        (roots[key] / "company.sqlite3").read_bytes() == value for key, value in before.items()
    )


@pytest.mark.parametrize("fault", ["authorization_unavailable", "wrong_released_artifact"])
def test_repinned_corrected_release_requires_available_exact_authorization(
    inputs, tmp_path, monkeypatch, fault
):
    roots, recipe = inputs
    group = next(g for g in recipe.source_groups if g.id == "change")
    rows, _ = risk.read_inputs(roots["change"], group.source_refs)
    changed = copy.deepcopy(rows)
    gate = next(r for r in changed if r["record"] == "GATE-CORRECTED")
    release = next(r for r in changed if r["record"] == "RELEASE-CORRECTED")
    if fault == "authorization_unavailable":
        gate["available_at"] = (
            datetime.fromisoformat(release["event_at"]) + timedelta(seconds=1)
        ).isoformat()
    else:
        proposed = next(r for r in changed if r["record"] == "GATE-PROPOSED")
        body = json.loads(release["content"])
        body["artifact"] = json.loads(proposed["content"])["artifact"]
        release["content"] = encoded(body)
        release["sha256"] = sha(release["content"])
    pin = sha(encoded([{k: v for k, v in row.items() if k != "content"} for row in changed]))
    replacement = replace(
        group,
        source_refs=tuple(
            risk.RiskSourceRef(**{f: row[f] for f in risk.FIELDS}) for row in changed
        ),
        source_versions_sha256=pin,
    )
    recipe = replace(
        recipe,
        source_groups=tuple(replacement if g.id == "change" else g for g in recipe.source_groups),
    )
    original = risk.read_inputs
    monkeypatch.setattr(
        risk,
        "read_inputs",
        lambda root, refs: (changed, pin) if root == roots["change"] else original(root, refs),
    )
    with pytest.raises(CompanyStoreError):
        risk.generate_pair(tmp_path / "invalid", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "invalid").exists()
