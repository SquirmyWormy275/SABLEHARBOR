import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import company_access_review_continuation as review
from enterprise.audit_suite.company_access_remediation_activity import generate_pair
from enterprise.audit_suite.company_lifecycle_activity import (
    FIELDS,
    LifecycleSourceRef,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded
from tests.audit_suite.test_company_access_remediation_activity import typed
from tests.audit_suite.test_company_access_remediation_operator import prepared

ROOT = Path(__file__).resolve().parents[2]


def rows(root):
    with CompanyStore(root)._db() as db:
        return [
            dict(r)
            for r in db.execute("SELECT * FROM versions ORDER BY event_at,system,record,version")
        ]


def group(name, label, root, selected):
    refs = tuple(LifecycleSourceRef(**{k: r[k] for k in FIELDS}) for r in selected)
    return review.ReviewContinuationSourceGroup(name, label, refs, read_inputs(root, refs)[1])


@pytest.fixture
def inputs(tmp_path):
    capsule, raw = prepared.__wrapped__(tmp_path)
    source = capsule / "company"
    remediation = tmp_path / "remediation"
    generate_pair(remediation, repository=ROOT, source_root=source, recipe=typed(raw))
    native = rows(remediation)
    selected = {
        (r["system"], r["record"], r["version"]): r for r in native if r["branch"] == "removal-b"
    }
    roots = {
        "identity": source,
        "remediation_initial": remediation,
        "remediation_final": remediation,
    }
    groups = (
        review.ReviewContinuationSourceGroup(
            "identity",
            raw["source_store_id"],
            typed(raw).source_refs,
            raw["source_versions_sha256"],
        ),
        group(
            "remediation_initial",
            "removal-original",
            remediation,
            [selected[k] for k in review.CHAIN[:6]],
        ),
        group(
            "remediation_final",
            "removal-original",
            remediation,
            [selected[k] for k in review.CHAIN[6:]],
        ),
    )
    recipe = review.AccessReviewContinuationRecipe(
        "SH",
        "review-q3-continuation",
        "REVIEW-Q3",
        groups,
        "2027-07-01T00:00:00Z",
        "2027-10-01T00:00:00Z",
        "2027-10-01T09:00:00Z",
        "2027-10-01T09:01:00Z",
        "2027-10-01T09:02:00Z",
        "Local declared subject carry-forward; no intervening activity evidence supplied.",
    )
    return roots, recipe


def test_completed_removal_drives_next_quarter_without_closing_parent_gap(inputs, tmp_path):
    roots, recipe = inputs
    before = {str(p): (p / "company.sqlite3").read_bytes() for p in set(roots.values())}
    out = tmp_path / "next-review"
    result = review.generate(out, repository=ROOT, source_roots=roots, recipe=recipe)
    assert len(result["records"]) == 3
    output = {r["system"]: json.loads(r["content"]) for r in rows(out)}
    assert output["review_population"]["members"][0]["rights"] == ["inventory-admin"]
    decision = output["review_decisions"]["decisions"][0]
    assert decision["decision"] == "RETAIN_AUTHORIZED" and decision["remove_rights"] == []
    assert decision["state_source"]["version"] == 3
    assert output["review_reconciliation"]["unresolved_person_ids"] == ["P014"]
    assert output["review_reconciliation"]["whole_review_closed"] is False
    for value in output.values():
        assert value["population_scope"] == "DECLARED_SUBJECT_ONLY_NOT_WORKFORCE_CENSUS"
        assert value["whole_quarter_operation"] == "NOT_ESTABLISHED"
    for p in set(roots.values()):
        assert (p / "company.sqlite3").read_bytes() == before[str(p)]
    with CompanyStore(out)._db() as db:
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    with pytest.raises(CompanyStoreError):
        review.generate(out, repository=ROOT, source_roots=roots, recipe=recipe)


@pytest.mark.parametrize("corruption", ["false_probe", "duplicate_key", "nonfinite"])
def test_exact_repinned_but_false_terminal_probe_is_rejected(inputs, tmp_path, corruption):
    roots, recipe = inputs
    altered = tmp_path / "false-probe"
    altered.mkdir(mode=0o700)
    store = CompanyStore(altered)
    for row in rows(roots["remediation_initial"]):
        with CompanyStore(roots["remediation_initial"])._db() as db:
            owner = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
                (row["company"], row["branch"], row["system"]),
            ).fetchone()[0]
        store.register_system(row["company"], row["branch"], row["system"], owner)
        body = json.loads(row["content"])
        if (
            row["branch"] == "removal-b"
            and row["system"] == "validation_probes"
            and row["version"] == 2
        ):
            body["removed_permission_probes"] = {"billing-admin": "ALLOW"}
        content = encoded(body)
        if (
            row["branch"] == "removal-b"
            and row["system"] == "validation_probes"
            and row["version"] == 2
        ):
            if corruption == "duplicate_key":
                content = content[:-1] + b',"extra":1,"extra":2}'
            elif corruption == "nonfinite":
                content = content[:-1] + b',"extra":1e999}'
        store.append_version(
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            expected_version=row["version"] - 1,
            command_id=row["command_id"],
            event_at=row["event_at"],
            available_at=row["available_at"],
            content=content,
            provenance=json.loads(row["provenance"]),
        )
    indexed = {
        (r["system"], r["record"], r["version"]): r
        for r in rows(altered)
        if r["branch"] == "removal-b"
    }
    groups = (
        recipe.source_groups[0],
        group(
            "remediation_initial",
            "removal-original",
            altered,
            [indexed[k] for k in review.CHAIN[:6]],
        ),
        group(
            "remediation_final", "removal-original", altered, [indexed[k] for k in review.CHAIN[6:]]
        ),
    )
    with pytest.raises(CompanyStoreError, match="verification|Strict finite"):
        review.generate(
            tmp_path / "bad",
            repository=ROOT,
            source_roots={**roots, "remediation_initial": altered, "remediation_final": altered},
            recipe=replace(recipe, source_groups=groups),
        )
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"period_start": "2027-04-01T00:00:00Z"},
        {"population_at": "2027-09-30T23:00:00Z"},
        {"branch_id": "removal-b"},
    ],
)
def test_wrong_period_future_cutoff_or_reused_branch_fails(inputs, tmp_path, change):
    roots, recipe = inputs
    with pytest.raises(CompanyStoreError):
        review.generate(
            tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=replace(recipe, **change)
        )
    assert not (tmp_path / "bad").exists()


def test_incomplete_chain_and_mismatched_producer_fail(inputs, tmp_path):
    roots, recipe = inputs
    final = recipe.source_groups[-1]
    fewer = final.source_refs[:-1]
    for name, bad in [
        (
            "missing",
            replace(
                final,
                source_refs=fewer,
                source_versions_sha256=read_inputs(roots[final.id], fewer)[1],
            ),
        ),
        ("label", replace(final, source_store_id="unrelated")),
    ]:
        with pytest.raises(CompanyStoreError):
            review.generate(
                tmp_path / name,
                repository=ROOT,
                source_roots=roots,
                recipe=replace(recipe, source_groups=(*recipe.source_groups[:-1], bad)),
            )
        assert not (tmp_path / name).exists()
