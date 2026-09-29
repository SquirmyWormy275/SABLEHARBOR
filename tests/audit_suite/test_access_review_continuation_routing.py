"""Maintained operator and pinned existing/producer routes for one review continuation."""

import copy
import hashlib
import json
import sqlite3
from dataclasses import asdict

import pytest

from enterprise.audit_suite import company_activity_linked_plan as linked
from enterprise.audit_suite import company_activity_producer_plan as producer
from enterprise.audit_suite.company_access_review_continuation import (
    CHAIN,
    AccessReviewContinuationRecipe,
)
from enterprise.audit_suite.company_activity_plan import PLAN_KINDS
from enterprise.audit_suite.company_runtime_activation import activate
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_access_remediation_operator import ROOT, write
from tests.audit_suite.test_company_access_remediation_operator import prepared as identity_prepared
from tests.audit_suite.test_company_access_review_continuation import group, rows
from tools.audit_suite import generate_company_activity as operator


def entry(capsule):
    return {
        "root": str(capsule / "company"),
        "manifest_sha256": hashlib.sha256((capsule / "MANIFEST.json").read_bytes()).hexdigest(),
    }


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path = tmp_path_factory.mktemp("review-routing")
    identity, removal_recipe = identity_prepared.__wrapped__(path)
    removal = path / "removal-operator"
    operator.run(
        "access-remediation",
        write(path / "removal.json", removal_recipe),
        removal,
        repository=ROOT,
        source_root=identity / "company",
    )
    native = rows(removal / "company")
    selected = {
        (r["system"], r["record"], r["version"]): r for r in native if r["branch"] == "removal-b"
    }
    parent = rows(identity / "company")
    parent_selected = [
        r
        for r in parent
        if any(all(r[k] == ref[k] for k in ref) for ref in removal_recipe["source_refs"])
    ]
    groups = (
        group("identity", removal_recipe["source_store_id"], identity / "company", parent_selected),
        group(
            "remediation_initial",
            "removal-original",
            removal / "company",
            [selected[k] for k in CHAIN[:6]],
        ),
        group(
            "remediation_final",
            "removal-original",
            removal / "company",
            [selected[k] for k in CHAIN[6:]],
        ),
    )
    recipe = asdict(
        AccessReviewContinuationRecipe(
            "SH",
            "review-q3-continuation",
            "REVIEW-Q3",
            groups,
            "2027-07-01T00:00:00Z",
            "2027-10-01T00:00:00Z",
            "2027-10-01T09:00:00Z",
            "2027-10-01T09:01:00Z",
            "2027-10-01T09:02:00Z",
            "Local declared-subject continuation; no whole-quarter operation asserted.",
        )
    )
    return identity, removal, json.loads(json.dumps(recipe)), removal_recipe


def plan_for(prepared, version):
    identity, removal, recipe, removal_recipe = prepared
    job = {
        "id": "review",
        "kind": "access-review-continuation",
        "depends_on": [],
        "recipe": copy.deepcopy(recipe),
        "sources": {
            "identity": "identity",
            "remediation_initial": "removal",
            "remediation_final": "removal",
        },
    }
    if version == 2:
        return {
            "format": linked.FORMAT,
            "inputs": {"identity": entry(identity), "removal": entry(removal)},
            "jobs": [job],
        }
    for g in job["recipe"]["source_groups"]:
        if g["id"] != "identity":
            del g["source_versions_sha256"]
    job["depends_on"] = ["removal"]
    job["sources"] = {
        "identity": {"input_id": "identity"},
        **{
            k: {"source_job": "removal", "metadata_mode": producer.CAPTURE}
            for k in ["remediation_initial", "remediation_final"]
        },
    }
    parent = {
        "id": "removal",
        "kind": "access-remediation",
        "depends_on": [],
        "recipe": copy.deepcopy(removal_recipe),
        "sources": {"source": {"input_id": "identity"}},
    }
    return {
        "format": producer.FORMAT,
        "inputs": {"identity": entry(identity)},
        "jobs": [parent, job],
    }


@pytest.mark.parametrize("route", ["operator", "v2", "v3"])
def test_actual_operator_routes_three_originals_and_fresh_runtime(prepared, tmp_path, route):
    identity, removal, recipe, _ = prepared
    before = {p: (p / "company/company.sqlite3").read_bytes() for p in [identity, removal]}
    if route == "operator":
        capsule = tmp_path / "capsule"
        operator.run(
            "access-review-continuation",
            write(tmp_path / "recipe.json", recipe),
            capsule,
            repository=ROOT,
            source_roots={
                "identity": identity / "company",
                "remediation_initial": removal / "company",
                "remediation_final": removal / "company",
            },
        )
    else:
        runner = linked if route == "v2" else producer
        runner.run(
            write(tmp_path / "plan.json", plan_for(prepared, 2 if route == "v2" else 3)),
            tmp_path / "run",
            repository=ROOT,
        )
        capsule = tmp_path / "run/jobs/review"
    manifest = json.loads((capsule / "MANIFEST.json").read_bytes())
    assert manifest["counts"]["versions"] == manifest["counts"]["systems"] == 3
    for name, pin in manifest["members"].items():
        assert hashlib.sha256((capsule / name).read_bytes()).hexdigest() == pin
    activate(
        capsule,
        tmp_path / "runtime",
        expected_manifest_sha256=hashlib.sha256(
            (capsule / "MANIFEST.json").read_bytes()
        ).hexdigest(),
    )
    native = rows(tmp_path / "runtime")
    assert len(native) == 3
    decoded = {r["system"]: json.loads(r["content"]) for r in native}
    assert decoded["review_population"]["members"][0]["rights"] == ["inventory-admin"]
    assert decoded["review_reconciliation"]["unresolved_person_ids"] == ["P014"]
    assert decoded["review_reconciliation"]["whole_review_closed"] is False
    with sqlite3.connect(
        (tmp_path / "runtime/company.sqlite3").as_uri() + "?mode=ro", uri=True
    ) as db:
        for table in ["grants", "collections", "access_events"]:
            assert db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    for p in before:
        assert (p / "company/company.sqlite3").read_bytes() == before[p]


@pytest.mark.parametrize("version", [2, 3])
def test_bad_route_topology_rejected_before_output(prepared, tmp_path, version):
    plan = plan_for(prepared, version)
    job = plan["jobs"][-1]
    job["sources"]["remediation_final"] = copy.deepcopy(job["sources"]["identity"])
    runner = linked if version == 2 else producer
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "bad.json", plan), tmp_path / "rejected", repository=ROOT)
    assert not (tmp_path / "rejected").exists()


def test_operator_rejects_missing_group_root_and_v1_remains_nine(prepared, tmp_path):
    identity, _, recipe, _ = prepared
    with pytest.raises(CompanyStoreError):
        operator.run(
            "access-review-continuation",
            write(tmp_path / "recipe.json", recipe),
            tmp_path / "rejected",
            repository=ROOT,
            source_roots={"identity": identity / "company"},
        )
    assert not (tmp_path / "rejected").exists()
    assert len(PLAN_KINDS) == 9 and "access-review-continuation" not in PLAN_KINDS
