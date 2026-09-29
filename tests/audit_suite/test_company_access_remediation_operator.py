import copy
import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import pytest

from enterprise.audit_suite import company_activity_linked_plan as linked
from enterprise.audit_suite import company_activity_producer_plan as producer
from enterprise.audit_suite.company_lifecycle_activity import LifecycleSourceRef, read_inputs
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_activity_period import recipe as period_recipe
from tools.audit_suite import generate_company_activity as operator

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


@pytest.fixture
def prepared(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "identity"
    operator.run(
        "identity-period",
        write(tmp_path / "identity.json", asdict(period_recipe())),
        source,
        repository=ROOT,
    )
    selectors = [
        ("review_population", "PRIV-2027-Q2", 1),
        ("review_decisions", "PRIV-2027-Q2", 1),
        ("review_reconciliation", "PRIV-2027-Q2", 1),
        ("application", "MOVE-Q2-application", 2),
        ("hr", "MOVE-Q2-hr", 3),
    ]
    with sqlite3.connect(
        (source / "company/company.sqlite3").as_uri() + "?mode=ro", uri=True
    ) as db:
        refs = tuple(
            LifecycleSourceRef(
                *db.execute(
                    "SELECT company,branch,system,record,version,sha256 FROM versions "
                    "WHERE branch=? AND system=? AND record=? AND version=?",
                    ("activity-messy", *selector),
                ).fetchone()
            )
            for selector in selectors
        )
    _, pin = read_inputs(source / "company", refs)
    recipe = dict(
        company_id="SH",
        source_store_id="identity-b",
        source_refs=[asdict(ref) for ref in refs],
        source_versions_sha256=pin,
        branch_ids=["removal-a", "removal-b"],
        campaign_id="REM-Q2",
        subject_person_id="P015",
        input_at="2027-07-01T09:00:00Z",
        request_at="2027-07-01T09:05:00Z",
        execute_at="2027-07-01T09:10:00Z",
        verify_at="2027-07-01T09:15:00Z",
        escalate_at="2027-07-01T09:20:00Z",
        correction_at="2027-07-01T09:30:00Z",
        closeout_at="2027-07-01T09:35:00Z",
        local_requirement_basis=(
            "Qualified local removal and independent operating probe; no assurance claim"
        ),
    )
    return source, recipe


@pytest.mark.parametrize("route", ["operator", "existing-v2", "producer-v3"])
def test_actual_removal_operator_and_pinned_source_routes(tmp_path, prepared, route):
    source, recipe = prepared
    original = (source / "company/company.sqlite3").read_bytes()
    destination = tmp_path / "result"
    if route == "operator":
        operator.run(
            "access-remediation",
            write(tmp_path / "recipe.json", recipe),
            destination,
            repository=ROOT,
            source_root=source / "company",
        )
        output = destination
    else:
        job = dict(
            id="removal",
            kind="access-remediation",
            depends_on=[],
            recipe=copy.deepcopy(recipe),
            sources={"source": "identity"},
        )
        if route == "existing-v2":
            plan = dict(
                format=linked.FORMAT,
                inputs={
                    "identity": {
                        "root": str(source / "company"),
                        "manifest_sha256": hashlib.sha256(
                            (source / "MANIFEST.json").read_bytes()
                        ).hexdigest(),
                    }
                },
                jobs=[job],
            )
            runner = linked
        else:
            del job["recipe"]["source_versions_sha256"]
            job["depends_on"] = ["identity"]
            job["sources"] = {
                "source": {"source_job": "identity", "metadata_mode": producer.CAPTURE}
            }
            plan = dict(
                format=producer.FORMAT,
                inputs={},
                jobs=[
                    dict(
                        id="identity",
                        kind="identity-period",
                        depends_on=[],
                        recipe=asdict(period_recipe()),
                        sources={},
                    ),
                    job,
                ],
            )
            runner = producer
        result = runner.run(write(tmp_path / "plan.json", plan), destination, repository=ROOT)
        assert result["status"] == "COMPLETE", result
        output = destination / "jobs/removal"
        frozen = json.loads((destination / "recipes/removal.json").read_bytes())
        assert frozen["source_refs"] == recipe["source_refs"]
        assert len(frozen["source_versions_sha256"]) == 64
    manifest = json.loads((output / "MANIFEST.json").read_bytes())
    assert manifest["kind"] == "access-remediation"
    assert manifest["counts"]["versions"] > 0
    assert manifest["counts"]["grants"] == manifest["counts"]["collections"] == 0
    assert (source / "company/company.sqlite3").read_bytes() == original
    for member, pin in manifest["members"].items():
        assert hashlib.sha256((output / member).read_bytes()).hexdigest() == pin


def test_removal_existing_route_checks_actual_input_cutoff_before_output(tmp_path, prepared):
    source, recipe = prepared
    recipe["input_at"] = "2027-06-30T23:59:00Z"
    plan = dict(
        format=linked.FORMAT,
        inputs={
            "identity": {
                "root": str(source / "company"),
                "manifest_sha256": hashlib.sha256(
                    (source / "MANIFEST.json").read_bytes()
                ).hexdigest(),
            }
        },
        jobs=[
            dict(
                id="removal",
                kind="access-remediation",
                depends_on=[],
                recipe=recipe,
                sources={"source": "identity"},
            )
        ],
    )
    with pytest.raises(CompanyStoreError):
        linked.run(write(tmp_path / "plan.json", plan), tmp_path / "result", repository=ROOT)
    assert not (tmp_path / "result").exists()
