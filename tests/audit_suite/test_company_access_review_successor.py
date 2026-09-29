import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import company_access_review_continuation as prior
from enterprise.audit_suite import company_access_review_successor as successor
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded
from tests.audit_suite.test_company_access_review_continuation import group, inputs, rows

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prepared(tmp_path):
    roots, recipe = inputs.__wrapped__(tmp_path)
    parent = tmp_path / "q3"
    prior.generate(parent, repository=ROOT, source_roots=roots, recipe=recipe)
    recipe = successor.AccessReviewSuccessorRecipe(
        recipe,
        group("prior_review", "q3-original", parent, rows(parent)),
        recipe.company_id,
        "q4-successor",
        "REVIEW-Q4",
        "2027-10-01T00:00:00Z",
        "2028-01-01T00:00:00Z",
        "2028-01-01T09:00:00Z",
        "2028-01-01T09:01:00Z",
        "2028-01-01T09:02:00Z",
        "Declared-subject Q4 carry-forward; no intervening activity supplied.",
    )
    return {**roots, "prior_review": parent}, recipe


def test_q4_replays_full_original_chain_and_keeps_scope(prepared, tmp_path):
    roots, recipe = prepared
    before = {str(p): (p / "company.sqlite3").read_bytes() for p in set(roots.values())}
    result = successor.generate(tmp_path / "q4", repository=ROOT, source_roots=roots, recipe=recipe)
    assert len(result["records"]) == 3
    by_system = {r["system"]: json.loads(r["content"]) for r in rows(tmp_path / "q4")}
    assert by_system["review_decisions"]["decisions"][0]["decision"] == "RETAIN_AUTHORIZED"
    assert by_system["review_population"]["members"][0]["rights"] == ["inventory-admin"]
    assert by_system["review_reconciliation"]["unresolved_person_ids"] == ["P014"]
    assert by_system["review_reconciliation"]["whole_review_closed"] is False
    for body in by_system.values():
        assert len(body["predecessor_review"]["source_refs"]) == 3
        assert sum(len(g["source_refs"]) for g in body["source_groups"]) == 16
        assert body["whole_quarter_operation"] == "NOT_ESTABLISHED"
    assert len(list((tmp_path / "q4" / "upstream").iterdir())) == 19
    assert before == {str(p): (p / "company.sqlite3").read_bytes() for p in set(roots.values())}


@pytest.mark.parametrize(
    "changes",
    [
        {"period_start": "2028-01-01T00:00:00Z", "period_end_exclusive": "2028-04-01T00:00:00Z"},
        {"period_end_exclusive": "2028-02-01T00:00:00Z"},
        {"decision_at": "2028-01-01T08:00:00Z"},
        {"branch_id": "review-q3-continuation"},
    ],
)
def test_rejects_nonadjacent_or_relabelled_review(prepared, tmp_path, changes):
    roots, recipe = prepared
    with pytest.raises(CompanyStoreError):
        successor.generate(
            tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=replace(recipe, **changes)
        )
    assert not (tmp_path / "bad").exists()


def changed_prior(roots, recipe, tmp_path, mutate):
    destination = tmp_path / "changed-prior"
    destination.mkdir(mode=0o700)
    store = CompanyStore(destination)
    for row in rows(roots["prior_review"]):
        body = json.loads(row["content"])
        mutate(row["system"], body)
        store.register_system(row["company"], row["branch"], row["system"], "P001")
        store.append_version(
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            expected_version=0,
            command_id=row["command_id"],
            event_at=row["event_at"],
            available_at=row["available_at"],
            content=encoded(body),
            provenance=json.loads(row["provenance"]),
        )
    return {**roots, "prior_review": destination}, replace(
        recipe, prior_review=group("prior_review", "q3-original", destination, rows(destination))
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("whole_review_closed", True),
        ("whole_review_closed", 0),
        ("unresolved_person_ids", []),
    ],
)
def test_repinned_prior_scope_forgery_fails(prepared, tmp_path, field, value):
    roots, recipe = prepared

    def mutate(system, body):
        if system == "review_reconciliation":
            body[field] = value

    roots, recipe = changed_prior(roots, recipe, tmp_path, mutate)
    with pytest.raises(CompanyStoreError, match="recomputed"):
        successor.generate(tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "bad").exists()


def test_repinned_extra_right_fails(prepared, tmp_path):
    roots, recipe = prepared

    def mutate(system, body):
        if system == "review_population":
            body["members"][0]["rights"].append("invented-admin")

    roots, recipe = changed_prior(roots, recipe, tmp_path, mutate)
    with pytest.raises(CompanyStoreError, match="recomputed"):
        successor.generate(tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=recipe)


def test_changed_original_metadata_rejects(prepared, tmp_path):
    roots, recipe = prepared
    changed = replace(recipe.prior_recipe.source_groups[0], source_versions_sha256="0" * 64)
    recipe = replace(
        recipe,
        prior_recipe=replace(
            recipe.prior_recipe, source_groups=(changed, *recipe.prior_recipe.source_groups[1:])
        ),
    )
    with pytest.raises(CompanyStoreError, match="metadata differs"):
        successor.generate(tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=recipe)


def test_final_source_race_rejects_publication(prepared, tmp_path, monkeypatch):
    roots, recipe = prepared
    read = successor.read_inputs
    count = 0

    def racing(root, refs):
        nonlocal count
        result = read(root, refs)
        count += 1
        return (result[0], "0" * 64) if count == 5 else result

    monkeypatch.setattr(successor, "read_inputs", racing)
    with pytest.raises(CompanyStoreError, match="changed before publication"):
        successor.generate(tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "bad").exists()


def test_final_code_race_rejects_publication(prepared, tmp_path, monkeypatch):
    roots, recipe = prepared
    real = Path.read_bytes
    target = ROOT / "enterprise/audit_suite/company_access_review_successor.py"
    count = 0

    def changing(path):
        nonlocal count
        data = real(path)
        if path == target:
            count += 1
            if count > 1:
                return data + b"\n# changed\n"
        return data

    monkeypatch.setattr(Path, "read_bytes", changing)
    with pytest.raises(CompanyStoreError, match="Implementation or scoped sources changed"):
        successor.generate(tmp_path / "bad", repository=ROOT, source_roots=roots, recipe=recipe)
    assert not (tmp_path / "bad").exists()
