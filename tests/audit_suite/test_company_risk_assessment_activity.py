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
from enterprise.audit_suite.company_incident_activity import generate_incident
from enterprise.audit_suite.company_provider_intake_activity import generate_pair as provider_pair
from enterprise.audit_suite.company_risk_assessment_activity import (
    FIELDS,
    RiskAssessmentRecipe,
    RiskScenario,
    RiskSourceGroup,
    RiskSourceRef,
    generate_pair,
    read_inputs,
    score,
)
from enterprise.audit_suite.company_security_logging_activity import (
    LoggingRecipe,
)
from enterprise.audit_suite.company_security_logging_activity import (
    generate_pair as log_pair,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_incident_activity import recipe as incident_recipe
from tests.audit_suite.test_company_provider_intake_activity import recipe as provider_recipe

ROOT = Path(__file__).resolve().parents[2]


def versions(root):
    with CompanyStore(root)._db() as db:
        return [
            dict(r)
            for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record,version")
        ]


def make_recipe(roots, selectors, change_label="change-original"):
    groups = []
    for group, (branch, selected) in selectors.items():
        rows = [
            r
            for r in versions(roots[group])
            if r["branch"] == branch and (r["system"], r["record"], r["version"]) in selected
        ]
        assert len(rows) == len(selected)
        refs = tuple(RiskSourceRef(**{k: r[k] for k in FIELDS}) for r in rows)
        _, pin = read_inputs(roots[group], refs)
        groups.append(
            RiskSourceGroup(
                group, change_label if group == "change" else group + "-original", refs, pin
            )
        )
    return RiskAssessmentRecipe(
        "SABLEHARBOR",
        ("risk-a", "risk-b"),
        tuple(groups),
        (
            RiskScenario(
                "LOCAL-DEPENDENCY",
                "EXTERNAL_DEPENDENCY",
                "AS-P007",
                2,
                4,
                1,
                3,
                "Propose dependency contingency exercise; no accepted commitment.",
                "Locally assumed ordinal likelihood; incident does not establish supplier cause.",
            ),
            RiskScenario(
                "LOCAL-CHANGE",
                "INTERNAL_CHANGE",
                "P005",
                3,
                3,
                2,
                2,
                "Propose periodic gate challenge; implementation not demonstrated.",
                "Hypothetical recurrence after recorded correction; not current exposure proof.",
            ),
        ),
        "2027-04-01T00:00:00Z",
        "2027-04-01T00:00:00Z",
        "2027-06-28T09:00:00Z",
        "2027-06-29T09:00:00Z",
        "2027-06-30T09:00:00Z",
        "2027-06-30T10:00:00Z",
        "2027-07-01T00:00:00Z",
        "Local ordinal one-to-five factors and quarter-end input reconciliation only.",
    )


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    roots = {key: tmp_path / key for key in ("change", "log", "incident", "provider")}
    change_pair(
        roots["change"],
        repository=ROOT,
        recipe=ChangeRecipe(
            "SABLEHARBOR",
            "release-a",
            "release-b",
            "CYCLE",
            "2027-02-01T00:00:00Z",
            "2027-02-03T00:00:00Z",
            "Local reference release rule only",
        ),
    )
    _, pin = read_originals(roots["change"])
    log_pair(
        roots["log"],
        repository=ROOT,
        source_root=roots["change"],
        recipe=LoggingRecipe(
            "SABLEHARBOR",
            "change-original",
            pin,
            "release-b",
            "logging-a",
            "logging-b",
            "LOCAL-RELEASE",
        ),
    )
    roots["incident"].mkdir(mode=0o700)
    generate_incident(
        CompanyStore(roots["incident"]),
        repository=ROOT,
        recipe=replace(incident_recipe(), company_id="SABLEHARBOR"),
    )
    provider_pair(roots["provider"], repository=ROOT, recipe=provider_recipe())
    selectors = {
        "incident": (
            "incident-clean",
            {
                ("monitoring", "INC-01-monitoring", 1),
                ("postincident_review", "INC-01-postincident_review", 1),
            },
        ),
        "provider": (
            "provider-complete",
            {
                ("planned_dependency_inventory", "DEPENDENCIES", 1),
                ("vendor_register", "CP-IDACORE", 1),
            },
        ),
        "log": (
            "logging-a",
            {("publisher_events", "EVENT-1", 1), ("detection_alerts", "AUTH-ALERT-1", 1)},
        ),
        "change": (
            "release-b",
            {
                ("release_gate", "GATE-PROPOSED", 1),
                ("local_releases", "RELEASE-PROPOSED", 1),
                ("release_gate", "GATE-CORRECTED", 1),
            },
        ),
    }
    return roots, make_recipe(roots, selectors)


def test_actual_input_omission_backfill_preserves_originals(tmp_path, inputs):
    roots, recipe = inputs
    before = {g: sha((p / "company.sqlite3").read_bytes()) for g, p in roots.items()}
    result = generate_pair(tmp_path / "out", repository=ROOT, source_roots=roots, recipe=recipe)
    rows = versions(tmp_path / "out")
    assert len(rows) == 20
    assert result["audit_created"] is result["grants_created"] is False
    assert before == {g: sha((p / "company.sqlite3").read_bytes()) for g, p in roots.items()}
    bodies = {(r["branch"], r["record"], r["version"]): json.loads(r["content"]) for r in rows}
    assert all(sha(r["content"]) == r["sha256"] for r in rows)
    for branch in recipe.branch_ids:
        for body in (v for (b, _, _), v in bodies.items() if b == branch):
            assert body["risk_acceptance"] == "NOT_PERFORMED"
            assert body["assurance_activity"] == "NOT_PERFORMED"
    with CompanyStore(tmp_path / "out")._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    ledger = [r for r in rows if r["system"] == "risk_input_ledger"]
    assert ledger[0]["content"] == ledger[1]["content"]
    assessments = {
        (r["branch"], r["version"]): json.loads(r["content"])
        for r in rows
        if r["system"] == "risk_assessments"
    }
    assert len(assessments["risk-a", 1]["risks"]) == 2
    assert len(assessments["risk-b", 1]["risks"]) == 1
    assert len(assessments["risk-b", 2]["risks"]) == 2
    checks = {
        (r["branch"], r["version"]): json.loads(r["content"])
        for r in rows
        if r["system"] == "risk_reconciliation"
    }
    assert checks["risk-b", 1]["missing_declared_input_ids"] == ["INTERNAL_CHANGE"]
    assert checks["risk-b", 2]["missing_declared_input_ids"] == []
    assert checks["risk-a", 1]["missing_declared_input_ids"] == []
    for r in assessments["risk-b", 2]["risks"]:
        assert r["inherent_local_score"] == r["likelihood"] * r["impact"]
        assert r["residual_status"] == "CONDITIONAL_PROJECTION_NOT_DEMONSTRATED"
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "out", repository=ROOT, source_roots=roots, recipe=recipe)


@pytest.mark.parametrize("value", [True, 1.0, 0, 6, "2"])
def test_factors_are_explicit_ordinal_integers(value):
    with pytest.raises(CompanyStoreError):
        score(RiskScenario("R", "INTERNAL_CHANGE", "P005", value, 2, 1, 1, "proposal", "assumed"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("period_end_exclusive", "2027-07-01T01:00:00Z"),
        ("input_at", "2027-01-01T00:00:00Z"),
        ("local_method_basis", ""),
    ],
)
def test_invalid_recipe_has_no_output(tmp_path, inputs, field, value):
    roots, recipe = inputs
    with pytest.raises(CompanyStoreError):
        generate_pair(
            tmp_path / "out",
            repository=ROOT,
            source_roots=roots,
            recipe=replace(recipe, **{field: value}),
        )
    assert not (tmp_path / "out").exists()


def test_coordination_cannot_replace_management_owner(tmp_path, inputs):
    roots, recipe = inputs
    changed = replace(
        recipe,
        scenarios=(
            replace(recipe.scenarios[0], management_owner_id="AS-P005"),
            recipe.scenarios[1],
        ),
    )
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "out", repository=ROOT, source_roots=roots, recipe=changed)


def test_producer_identity_and_output_boundary(tmp_path, inputs):
    roots, recipe = inputs
    groups = tuple(
        replace(g, source_store_id="different-original") if g.id == "change" else g
        for g in recipe.source_groups
    )
    with pytest.raises(CompanyStoreError):
        generate_pair(
            tmp_path / "out",
            repository=ROOT,
            source_roots=roots,
            recipe=replace(recipe, source_groups=groups),
        )
    with pytest.raises(CompanyStoreError):
        generate_pair(
            roots["change"] / "nested", repository=ROOT, source_roots=roots, recipe=recipe
        )


@pytest.mark.parametrize(
    "mutation",
    ["missing_hashes", "stale_hash", "wrong_provider", "review_before_probe", "alert_before_event"],
)
def test_pinned_but_incoherent_native_sources_rejected(tmp_path, inputs, monkeypatch, mutation):
    import enterprise.audit_suite.company_risk_assessment_activity as module
    from enterprise.audit_suite.operating_source_bridge import encoded

    roots, recipe = inputs
    original = module.read_inputs

    def changed(root, refs):
        rows, pin = original(root, refs)
        for row in rows:
            body = json.loads(row["content"])
            if mutation == "missing_hashes":
                if row["system"] == "publisher_events":
                    body["event"].pop("event_sha256")
                if row["system"] == "detection_alerts":
                    body.pop("source_event_sha256")
            if mutation == "stale_hash" and row["system"] == "publisher_events":
                body["event"]["sequence"] = 99
            if mutation == "wrong_provider" and row["system"] == "vendor_register":
                body["provider"]["provider_id"] = "UNRELATED"
            if mutation == "review_before_probe" and row["system"] == "postincident_review":
                row["event_at"] = "2027-03-01T00:00:00+00:00"
            if mutation == "alert_before_event" and row["system"] == "detection_alerts":
                row["event_at"] = "2027-01-01T00:00:00+00:00"
            row["content"] = encoded(body)
        return rows, pin

    monkeypatch.setattr(module, "read_inputs", changed)
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "out", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "out").exists()
